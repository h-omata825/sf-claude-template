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

BATCH_PATTERNS       = re.compile(r"\bDatabase\.Batchable\b", re.IGNORECASE)
SCHED_PATTERNS       = re.compile(r"\bSchedulable\b", re.IGNORECASE)
TEST_PATTERNS        = re.compile(r"@IsTest|@isTest|isTest", re.IGNORECASE)
INTEGRATION_PATTERNS = re.compile(
    r"\bHttp\b|\bHttpRequest\b|\bHttpResponse\b"
    r"|\bHttpCalloutMock\b"
    r"|\bWebServiceCallout\b",
    re.IGNORECASE,
)

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


def extract_trigger_overview(trigger_path: Path) -> str:
    """Triggerファイルから「{Object} の {events} トリガー」形式で概要を生成する。

    ファイル冒頭のコメントがあればそれを優先。無ければ trigger 宣言から自動生成。
    例: `trigger FeedCommentTrigger on FeedComment (after insert) { ... }`
         → "FeedComment の after insert トリガー"
    """
    try:
        text = trigger_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    # 先頭の /** ... */ javadoc を優先
    m = re.match(r'\s*/\*\*(.*?)\*/', text, re.DOTALL)
    if m:
        lines = [l.strip().lstrip('*').strip() for l in m.group(1).split('\n')
                 if l.strip().strip('*').strip() and not l.strip().lstrip('*').strip().startswith('@')]
        if lines:
            return lines[0]
    # trigger 宣言から抽出
    m = re.search(r'trigger\s+\w+\s+on\s+(\w+)\s*\(([^)]+)\)', text)
    if m:
        obj = m.group(1)
        events = ", ".join(e.strip() for e in m.group(2).split(",") if e.strip())
        return f"{obj} の {events} トリガー"
    return ""


def extract_lwc_overview(lwc_dir: Path) -> str:
    """LWC コンポーネントバンドルから概要を抽出する。

    優先順: .js-meta.xml の <description> → <masterLabel> → JS の JSDoc 冒頭行
    """
    name = lwc_dir.name
    meta = lwc_dir / f"{name}.js-meta.xml"
    if meta.exists():
        try:
            content = meta.read_text(encoding="utf-8", errors="ignore")
            # namespace を意識せず Regex で抜く（XML 名前空間差異を許容）
            for tag in ("description", "masterLabel"):
                m = re.search(rf'<{tag}>(.*?)</{tag}>', content, re.DOTALL)
                if m:
                    val = m.group(1).strip()
                    if val:
                        return val
        except Exception:
            pass
    # Fallback: .js の先頭 JSDoc
    js = lwc_dir / f"{name}.js"
    if js.exists():
        try:
            text = js.read_text(encoding="utf-8", errors="ignore")
            m = re.match(r'\s*/\*\*(.*?)\*/', text, re.DOTALL)
            if m:
                lines = [l.strip().lstrip('*').strip() for l in m.group(1).split('\n')
                         if l.strip().strip('*').strip() and not l.strip().lstrip('*').strip().startswith('@')]
                if lines:
                    return lines[0]
        except Exception:
            pass
    return ""


def extract_vf_overview(page_meta_path: Path) -> str:
    """Visualforce ページから概要を抽出する。

    優先順: .page-meta.xml の <description> → <label> → .page の <title> タグ
    """
    try:
        content = page_meta_path.read_text(encoding="utf-8", errors="ignore")
        for tag in ("description", "label"):
            m = re.search(rf'<{tag}>(.*?)</{tag}>', content, re.DOTALL)
            if m:
                val = m.group(1).strip()
                if val:
                    return val
    except Exception:
        pass
    # .page ファイルの <title> を fallback
    page_path = page_meta_path.with_name(page_meta_path.name.replace(".page-meta.xml", ".page"))
    if page_path.exists():
        try:
            text = page_path.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'<title>\s*(.*?)\s*</title>', text, re.DOTALL)
            if m:
                val = m.group(1).strip()
                if val:
                    return val
        except Exception:
            pass
    return ""


def extract_aura_overview(aura_dir: Path) -> str:
    """Aura コンポーネントバンドルから概要を抽出する。

    優先順: .cmp-meta.xml の <description> → .cmp の冒頭コメント
    ただし "A Lightning Component Bundle" のデフォルト値は空扱いにする。
    """
    name = aura_dir.name
    meta = aura_dir / f"{name}.cmp-meta.xml"
    DEFAULT_DESCS = {"A Lightning Component Bundle"}
    if meta.exists():
        try:
            content = meta.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'<description>(.*?)</description>', content, re.DOTALL)
            if m:
                val = m.group(1).strip()
                if val and val not in DEFAULT_DESCS:
                    return val
        except Exception:
            pass
    # .cmp の冒頭の HTML コメント
    cmp = aura_dir / f"{name}.cmp"
    if cmp.exists():
        try:
            text = cmp.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'<!--\s*(.*?)\s*-->', text, re.DOTALL)
            if m:
                val = m.group(1).strip()
                # "attribute" など雑なコメントは除外
                if val and len(val) > 5 and "attribute" not in val.lower():
                    return val.split('\n')[0]
        except Exception:
            pass
    return ""


def extract_trigger_handler(trigger_path: Path) -> str | None:
    """トリガーファイルからハンドラークラス名を抽出する。
    見つからない場合は {TriggerStem}Handler を推測して返す。
    推測したクラスファイルが classes/ に存在しない場合は None を返す。
    """
    classes_dir = trigger_path.parent.parent / "classes"
    try:
        text = trigger_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'\b(\w+Handler)\b', text)
        if m:
            handler_name = m.group(1)
            if not (classes_dir / f"{handler_name}.cls").exists():
                print(f"[警告] {trigger_path.name}: ハンドラー {handler_name}.cls が classes/ に存在しません → absorb_into=None", file=sys.stderr)
                return None
            return handler_name
    except Exception:
        pass
    # フォールバック: OpportunityTrigger → OpportunityTriggerHandler
    stem = trigger_path.stem
    guessed = f"{stem}Handler"
    if not (classes_dir / f"{guessed}.cls").exists():
        print(f"[警告] {trigger_path.name}: ハンドラークラス名を推測 → {guessed} だが classes/ に存在しません → absorb_into=None", file=sys.stderr)
        return None
    print(f"[警告] {trigger_path.name}: ハンドラークラス名を推測 → {guessed}", file=sys.stderr)
    return guessed


def classify_apex(path: Path) -> str:
    """Apexクラスの種別を判定する (Batch / Integration / Apex)

    Schedulable のみを実装するクラス（バッチの起動設定だけ）は
    独立した機能として扱わず None を返してスキャン対象から除外する。
    スケジュール情報（cron式）は対応する Batch の設計書の trigger に記載する。

    Http / HttpRequest / HttpResponse を使う外部連携クラスは Integration に分類する。
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
    if INTEGRATION_PATTERNS.search(text):
        return "Integration"
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
    ledger_path = project_dir / "docs" / ".sf" / "feature_ids.yml"
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

    # --- Apex / Batch ---
    base = force_app / "classes"
    if base.exists():
        for cls_file in sorted(base.glob("*.cls")):
            classified = classify_apex(cls_file)
            if classified is None:
                continue
            _add(classified, cls_file.stem, {
                "name":        cls_file.stem,
                "overview":    extract_javadoc(cls_file),
                "source_file": cls_file.as_posix(),
                "design_doc":  get_design_doc(docs_design, cls_file.stem),
            })

    # --- Trigger（ハンドラークラスに吸収）---
    base = force_app / "triggers"
    if base.exists():
        for trig_file in sorted(base.glob("*.trigger")):
            handler = extract_trigger_handler(trig_file)
            _add("Trigger", trig_file.stem, {
                "name":        trig_file.stem,
                "overview":    extract_trigger_overview(trig_file),
                "source_file": trig_file.as_posix(),
                "design_doc":  None,
                "absorb_into": handler,   # ハンドラークラスの steps/prerequisites に吸収
            })

    # --- Flow ---
    base = force_app / "flows"
    if base.exists():
        for flow_file in sorted(base.glob("*.flow-meta.xml")):
            label, ptype, desc = get_flow_info(flow_file)
            flow_type = "画面フロー" if ptype == "Flow" and b"<screens>" in flow_file.read_bytes() else "Flow"
            api_name = flow_file.name.replace(".flow-meta.xml", "")
            # description が空なら label を overview に fallback（api_name と被らない場合のみ）
            overview = desc.strip()
            if not overview and label and label != api_name:
                overview = label
            _add(flow_type, api_name, {
                "name":        label,
                "overview":    overview,
                "source_file": flow_file.as_posix(),
                "design_doc":  get_design_doc(docs_design, flow_file.stem),
            })

    # --- LWC（モーダルコンポーネントは親に吸収）---
    base = force_app / "lwc"
    if base.exists():
        lwc_names = {p.name for p in base.iterdir() if p.is_dir()}
        for comp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            name = comp_dir.name
            # モーダル検出: 名前が "modal"（大文字小文字不問）で終わる
            parent_name = None
            if name.lower().endswith("modal"):
                candidate = name[:-5]   # "Modal" / "modal" = 5文字
                if candidate and candidate in lwc_names:
                    parent_name = candidate
            _add("LWC", name, {
                "name":        name,
                "overview":    extract_lwc_overview(comp_dir),
                "source_file": comp_dir.as_posix(),
                "design_doc":  get_design_doc(docs_design, name),
                "absorb_into": parent_name,   # None = 独立設計書を作る
            })

    # --- Aura ---
    base = force_app / "aura"
    if base.exists():
        for comp_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            _add("Aura", comp_dir.name, {
                "name":        comp_dir.name,
                "overview":    extract_aura_overview(comp_dir),
                "source_file": comp_dir.as_posix(),
                "design_doc":  get_design_doc(docs_design, comp_dir.name),
            })

    # --- Visualforce ---
    base = force_app / "pages"
    if base.exists():
        for page_file in sorted(base.glob("*.page-meta.xml")):
            api_name = page_file.name.replace(".page-meta.xml", "")
            _add("Visualforce", api_name, {
                "name":        api_name,
                "overview":    extract_vf_overview(page_file),
                "source_file": page_file.as_posix(),
                "design_doc":  get_design_doc(docs_design, api_name),
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
