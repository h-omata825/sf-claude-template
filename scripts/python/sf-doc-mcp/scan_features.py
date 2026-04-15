"""
force-app/ と docs/design/ を走査して機能一覧を JSON 出力する。

機能IDは docs/feature_ids.yml を唯一の台帳として管理する。
- 既存API名は台帳のIDを再利用
- 新規は末尾に追番
- 今回見つからなかったものは deprecated=true にしてID欠番を保持

Usage: python scan_features.py --project-dir <path>
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from feature_id_ledger import (
    load_ledger, save_ledger, resolve_id, mark_deprecated, _make_key,
)


FEATURE_TYPES = {
    "classes":   "Apex",
    "triggers":  "Trigger",
    "flows":     "Flow",
    "lwc":       "LWC",
    "aura":      "Aura",
}

BATCH_PATTERNS = re.compile(r"\bDatabase\.Batchable\b", re.IGNORECASE)
SCHED_PATTERNS = re.compile(r"\bSchedulable\b", re.IGNORECASE)
TEST_PATTERNS  = re.compile(r"@IsTest|@isTest|isTest", re.IGNORECASE)

FLOW_NS = "http://soap.sforce.com/2006/04/metadata"


def extract_javadoc(path: Path) -> str:
    """Apexクラスのjavadocコメント最初の意味ある行を取得する"""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'/\*\*(.*?)\*/', text, re.DOTALL)
        if m:
            lines = [l.strip().lstrip('*').strip() for l in m.group(1).split('\n')
                     if l.strip().strip('*').strip() and not l.strip().lstrip('*').strip().startswith('@')]
            return lines[0] if lines else ""
    except Exception:
        pass
    return ""


def classify_apex(path: Path) -> str:
    """Apexクラスの種別を判定する (Batch / Apex)

    Schedulable のみを実装するクラス（バッチの起動設定だけ）は
    独立した機能として扱わず None を返してスキャン対象から除外する。
    スケジュール情報（cron式）は対応する Batch の設計書の trigger に記載する。
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "Apex"
    if TEST_PATTERNS.search(text):
        return None          # テストクラスは除外
    if BATCH_PATTERNS.search(text):
        return "Batch"
    if SCHED_PATTERNS.search(text):
        return None          # Schedulable のみ → Batch の trigger に吸収
    return "Apex"


def get_flow_info(path: Path) -> tuple[str, str, str]:
    """フロー XML から label, processType, description を取得する"""
    try:
        content = path.read_bytes()
        tree = ET.fromstring(content)
        ns = {"sf": FLOW_NS}
        label = tree.findtext("sf:label", namespaces=ns) or path.stem
        ptype = tree.findtext("sf:processType", namespaces=ns) or "Flow"
        desc  = tree.findtext("sf:description", namespaces=ns) or ""
        return label, ptype, desc
    except Exception:
        return path.stem, "Flow", ""


def get_design_doc(docs_design_dir: Path, name: str) -> str | None:
    """docs/design/ 配下から機能名に対応するMDファイルのパスを返す"""
    for md in docs_design_dir.rglob("*.md"):
        if name.lower() in md.stem.lower():
            return md.as_posix()
    return None


def scan(project_dir: Path) -> list[dict]:
    force_app = project_dir / "force-app" / "main" / "default"
    docs_design = project_dir / "docs" / "design"
    ledger_path = project_dir / "docs" / "feature_ids.yml"
    ledger = load_ledger(ledger_path)

    features = []
    active_keys: set[str] = set()

    def _add(ftype: str, api_name: str, extra: dict):
        fid = resolve_id(ledger, ftype, api_name)
        active_keys.add(_make_key(ftype, api_name))
        entry = {
            "id":       fid,
            "type":     ftype,
            "api_name": api_name,
            **extra,
        }
        features.append(entry)

    # --- Apex / Trigger / Batch ---
    for folder, ftype in [("classes", "Apex"), ("triggers", "Trigger")]:
        base = force_app / folder
        if not base.exists():
            continue
        for cls_file in sorted(base.glob("*.cls")):
            if ftype == "Apex":
                classified = classify_apex(cls_file)
                if classified is None:
                    continue
                actual_type = classified
            else:
                actual_type = "Trigger"
            _add(actual_type, cls_file.stem, {
                "name":        cls_file.stem,
                "overview":    extract_javadoc(cls_file),
                "source_file": cls_file.as_posix(),
                "design_doc":  get_design_doc(docs_design, cls_file.stem),
            })

    # --- Flow ---
    base = force_app / "flows"
    if base.exists():
        for flow_file in sorted(base.glob("*.flow-meta.xml")):
            label, ptype, desc = get_flow_info(flow_file)
            flow_type = "画面フロー" if "Screen" in ptype else "Flow"
            api_name = flow_file.name.replace(".flow-meta.xml", "")
            _add(flow_type, api_name, {
                "name":        label,
                "overview":    desc,
                "source_file": flow_file.as_posix(),
                "design_doc":  get_design_doc(docs_design, flow_file.stem),
            })

    # --- LWC ---
    base = force_app / "lwc"
    if base.exists():
        for comp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            _add("LWC", comp_dir.name, {
                "name":        comp_dir.name,
                "source_file": comp_dir.as_posix(),
                "design_doc":  get_design_doc(docs_design, comp_dir.name),
            })

    # --- Aura ---
    base = force_app / "aura"
    if base.exists():
        for comp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            _add("Aura", comp_dir.name, {
                "name":        comp_dir.name,
                "source_file": comp_dir.as_posix(),
                "design_doc":  get_design_doc(docs_design, comp_dir.name),
            })

    # 今回見つからなかった機能は deprecated にする
    newly_deprecated = mark_deprecated(ledger, active_keys)
    if newly_deprecated:
        print(f"[情報] 削除検知: {len(newly_deprecated)}件 → 台帳で deprecated=true に更新",
              file=sys.stderr)
        for e in newly_deprecated:
            print(f"  - {e['id']} ({e['type']}) {e['api_name']}", file=sys.stderr)

    # 台帳保存（常に）
    save_ledger(ledger_path, ledger)

    return features


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default=".", help="プロジェクトルート")
    parser.add_argument("--output",      default=None, help="出力JSONファイルパス（省略時はstdout）")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    features = scan(project_dir)
    out = json.dumps(features, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"スキャン完了: {len(features)}件 → {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(out.encode("utf-8"))
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
