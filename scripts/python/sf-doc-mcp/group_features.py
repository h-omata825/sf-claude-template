# -*- coding: utf-8 -*-
"""機能グループ推論スクリプト。

scan_features.py が出力した機能一覧を入力として、
命名規則とコード内の依存関係からから業務機能グループを推論し、
docs/feature_groups.yml に出力する。

基本設計・詳細設計書の「機能グループ単位」の単位として使用する。

Usage:
  python group_features.py --project-dir <path> [--feature-list <json>] [--output <yaml>]

グルーピング戦略（優先順位順）:
  1. absorb_into（Trigger→Handler、Modal→親LWC）: 既存の吸収関係を尊重
  2. 命名プレフィックス（QuotationRequestController → QuotationRequest）
  3. コード内依存関係（import / new / actionCalls 等）
"""

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import yaml

FLOW_NS = "http://soap.sforce.com/2006/04/metadata"

# 命名プレフィックスから除去するサフィックス（長いものを先に評価）
_STRIP_SUFFIXES = [
    "TriggerHandler", "Controller", "Extension",
    "Service", "Handler", "Helper", "Selector",
    "Repository", "Util", "Utils", "Manager",
    "Factory", "Builder", "Batch", "Scheduler",
    "Integration", "Callout", "Client",
    "Form", "Modal", "List", "Detail",
    "Edit", "Create", "View", "Page",
    "Flow", "Process", "Action", "Screen",
    "Test", "Mock",
]

# 共有ユーティリティとみなすグループ参照数の閾値
_SHARED_THRESHOLD = 4


# ── 命名プレフィックス正規化 ───────────────────────────────────────

def normalize_prefix(api_name: str) -> str:
    """API名から業務的プレフィックスを抽出する。

    例:
      QuotationRequestController → QuotationRequest
      quotationRequestForm       → QuotationRequest
      Quotation_Request_Flow     → QuotationRequest
    """
    # camelCase → PascalCase
    name = api_name[0].upper() + api_name[1:] if api_name else api_name

    # アンダースコア区切り（Flow名 等）はキャメルケースに変換
    if "_" in name:
        name = "".join(p.capitalize() for p in name.split("_"))

    # サフィックスを長いものから順に除去
    for suffix in sorted(_STRIP_SUFFIXES, key=len, reverse=True):
        if name.endswith(suffix) and len(name) > len(suffix):
            name = name[:-len(suffix)]
            break  # 1回だけ除去

    return name


# ── ソースファイルからの依存関係抽出 ──────────────────────────────

def extract_apex_deps(cls_path: Path, all_api_names: set) -> set:
    """Apexクラスから参照している他クラス名を抽出する。"""
    deps = set()
    try:
        text = cls_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return deps

    # new ClassName() / new ClassName[
    for m in re.finditer(r"\bnew\s+([A-Z][A-Za-z0-9_]+)\s*[(\[]", text):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    # ClassName.staticMethod() または ClassName.field
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9_]+)\s*\.\s*[a-zA-Z]", text):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    # 型宣言: ClassName varName = / ClassName varName,
    for m in re.finditer(r"\b([A-Z][A-Za-z0-9_]+)\s+[a-z][A-Za-z0-9_]*\s*[=;,)]", text):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    return deps


def extract_lwc_deps(comp_dir: Path, all_api_names: set) -> set:
    """LWCのJSファイルからApexインポートを抽出する。"""
    deps = set()
    js_file = comp_dir / f"{comp_dir.name}.js"
    if not js_file.exists():
        return deps
    try:
        text = js_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return deps

    # import methodName from '@salesforce/apex/ClassName.methodName'
    for m in re.finditer(
        r"from\s+['\"]@salesforce/apex/([A-Za-z0-9_]+)\.[A-Za-z0-9_]+['\"]", text
    ):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    return deps


def extract_flow_deps(flow_path: Path, all_api_names: set) -> set:
    """FlowのXMLからApex呼び出し・サブフローを抽出する。"""
    deps = set()
    try:
        tree = ET.fromstring(flow_path.read_bytes())
        ns = {"sf": FLOW_NS}

        # <actionCalls><actionName> → Apex InvocableMethod クラス名
        for ac in tree.findall(".//sf:actionCalls", ns):
            name = ac.findtext("sf:actionName", namespaces=ns) or ""
            if name in all_api_names:
                deps.add(name)

        # <subflows><flowName> → サブフロー API名
        for sf_elem in tree.findall(".//sf:subflows", ns):
            name = sf_elem.findtext("sf:flowName", namespaces=ns) or ""
            if name in all_api_names:
                deps.add(name)
    except Exception:
        pass
    return deps


def extract_visualforce_deps(page_path: Path, all_api_names: set) -> set:
    """Visualforceページから参照しているApexクラス名を抽出する。

    page-meta.xml 内の controller="..." / extensions="..." 属性を読む。
    extensions は複数指定可（カンマ区切り）。
    """
    deps = set()
    try:
        text = page_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return deps

    # controller="ClassName"
    for m in re.finditer(r'\bcontroller\s*=\s*["\']([A-Za-z0-9_]+)["\']', text):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    # extensions="ClassA,ClassB"
    for m in re.finditer(r'\bextensions\s*=\s*["\']([^"\']+)["\']', text):
        for cls in m.group(1).split(","):
            cls = cls.strip()
            if cls in all_api_names:
                deps.add(cls)

    return deps


def extract_aura_deps(comp_dir: Path, all_api_names: set) -> set:
    """Auraコンポーネントから参照しているApexクラス名を抽出する。

    {name}.cmp の <aura:component controller="ClassName"> を読む。
    """
    deps = set()
    cmp_file = comp_dir / f"{comp_dir.name}.cmp"
    if not cmp_file.exists():
        return deps
    try:
        text = cmp_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return deps

    # <aura:component controller="ClassName">
    for m in re.finditer(r'\bcontroller\s*=\s*["\']([A-Za-z0-9_]+)["\']', text):
        if m.group(1) in all_api_names:
            deps.add(m.group(1))

    return deps


# ── Union-Find ────────────────────────────────────────────────────

class _UnionFind:
    def __init__(self, keys):
        self.parent = {k: k for k in keys}

    def find(self, k):
        while self.parent[k] != k:
            self.parent[k] = self.parent[self.parent[k]]
            k = self.parent[k]
        return k

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# ── メイン処理 ────────────────────────────────────────────────────

def build_groups(features: list, project_dir: Path) -> list:
    """命名規則 + コード内依存関係からグループを推論する。"""
    by_api = {f["api_name"]: f for f in features}
    all_api_names = set(by_api.keys())

    uf = _UnionFind(all_api_names)

    # Step 1: absorb_into 関係を結合（Trigger→Handler、Modal→親LWC）
    for f in features:
        absorb = f.get("absorb_into")
        if absorb and absorb in all_api_names:
            uf.union(f["api_name"], absorb)

    # Step 2: 命名プレフィックスで結合
    prefix_map = defaultdict(list)
    for api_name in all_api_names:
        prefix_map[normalize_prefix(api_name)].append(api_name)
    for members in prefix_map.values():
        for i in range(1, len(members)):
            uf.union(members[0], members[i])

    # Step 3: コード内依存関係で結合
    for f in features:
        api_name = f["api_name"]
        ftype = f.get("type", "")
        source = f.get("source_file", "")
        source_path = Path(source) if source else None

        deps: set = set()
        if ftype in ("Apex", "Batch", "Integration"):
            if source_path and source_path.exists():
                deps = extract_apex_deps(source_path, all_api_names)
        elif ftype == "LWC":
            if source_path and source_path.is_dir():
                deps = extract_lwc_deps(source_path, all_api_names)
        elif ftype in ("Flow", "画面フロー"):
            if source_path and source_path.exists():
                deps = extract_flow_deps(source_path, all_api_names)
        elif ftype == "Visualforce":
            if source_path and source_path.exists():
                deps = extract_visualforce_deps(source_path, all_api_names)
        elif ftype == "Aura":
            if source_path and source_path.is_dir():
                deps = extract_aura_deps(source_path, all_api_names)

        for dep in deps:
            if dep != api_name:
                uf.union(api_name, dep)

    # Step 4: グループ化
    group_map: dict = defaultdict(list)
    for api_name in all_api_names:
        group_map[uf.find(api_name)].append(by_api[api_name])

    # Step 5: 共有ユーティリティ検出（多数のグループから依存される）
    # 各 api_name が何グループから参照されているか集計
    group_roots = {api: uf.find(api) for api in all_api_names}
    ref_count: dict = defaultdict(set)  # api_name → 参照元グループ root の集合
    for f in features:
        api_name = f["api_name"]
        ftype = f.get("type", "")
        source = f.get("source_file", "")
        source_path = Path(source) if source else None
        deps: set = set()
        if ftype in ("Apex", "Batch", "Integration") and source_path and source_path.exists():
            deps = extract_apex_deps(source_path, all_api_names)
        elif ftype == "LWC" and source_path and source_path.is_dir():
            deps = extract_lwc_deps(source_path, all_api_names)
        elif ftype in ("Flow", "画面フロー") and source_path and source_path.exists():
            deps = extract_flow_deps(source_path, all_api_names)
        elif ftype == "Visualforce" and source_path and source_path.exists():
            deps = extract_visualforce_deps(source_path, all_api_names)
        elif ftype == "Aura" and source_path and source_path.is_dir():
            deps = extract_aura_deps(source_path, all_api_names)
        for dep in deps:
            ref_count[dep].add(group_roots[api_name])

    shared_apis = {
        api for api, roots in ref_count.items()
        if len(roots) >= _SHARED_THRESHOLD
    }

    # Step 6: グループオブジェクト生成
    groups = []
    gid = 1
    shared_group_features = []

    for root, members in sorted(group_map.items()):
        # 全員が shared なグループはまとめて shared グループへ
        shared_members = [m for m in members if m["api_name"] in shared_apis]
        normal_members = [m for m in members if m["api_name"] not in shared_apis]

        if normal_members:
            ja_name = _resolve_ja_name(normal_members + shared_members)
            prefix = normalize_prefix(root)
            groups.append({
                "group_id": f"GRP-{gid:03d}",
                "name_en": prefix,
                "name_ja": ja_name,
                "shared": False,
                "features": _format_members(normal_members + shared_members),
            })
            gid += 1

        # shared_members だけのグループはあとでまとめる
        for m in shared_members:
            if all(m["api_name"] in shared_apis for m in members):
                shared_group_features.append(m)

    if shared_group_features:
        # 重複除去
        seen = set()
        uniq = []
        for f in shared_group_features:
            if f["api_name"] not in seen:
                seen.add(f["api_name"])
                uniq.append(f)
        groups.append({
            "group_id": f"GRP-{gid:03d}",
            "name_en": "SharedUtilities",
            "name_ja": "共有ユーティリティ",
            "shared": True,
            "features": _format_members(uniq),
        })

    return groups


def _format_members(members: list) -> list:
    return sorted(
        [{"id": f["id"], "api_name": f["api_name"], "type": f["type"]}
         for f in members],
        key=lambda x: x.get("id", ""),
    )


def _resolve_ja_name(members: list) -> str:
    """メンバーの overview / name から日本語グループ名を推論する。"""
    for f in sorted(members, key=lambda x: len(x.get("overview", "")), reverse=True):
        overview = f.get("overview", "").strip()
        if overview and len(overview) > 3:
            # 最初の句読点・改行前を取る
            name = re.split(r"[。、\n（(]", overview)[0].strip()
            if name:
                return name[:30]
    # overview がなければ name をそのまま（英語になるがフォールバック）
    names = [f.get("name", f["api_name"]) for f in members]
    return max(names, key=len) if names else ""


# ── CLI ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="機能グループ推論スクリプト")
    parser.add_argument("--project-dir", required=True, help="プロジェクトルートパス")
    parser.add_argument("--feature-list", help="scan_features.py 出力 JSON（省略時は自動スキャン）")
    parser.add_argument("--output", help="出力 YAML パス（省略時は docs/feature_groups.yml）")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()

    # feature list 取得
    if args.feature_list:
        features = json.loads(Path(args.feature_list).read_text(encoding="utf-8"))
    else:
        scan_script = Path(__file__).parent / "scan_features.py"
        result = subprocess.run(
            [sys.executable, str(scan_script), "--project-dir", str(project_dir)],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(1)
        features = json.loads(result.stdout)

    # deprecated を除外
    features = [f for f in features if not f.get("deprecated")]
    if not features:
        print("機能が見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

    print(f"入力機能数: {len(features)}", file=sys.stderr)

    groups = build_groups(features, project_dir)

    output_path = (
        Path(args.output) if args.output
        else project_dir / "docs" / "feature_groups.yml"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "# 機能グループ定義（group_features.py 自動生成）\n"
        "# 命名規則とコード内依存関係から推論。必要に応じて手動調整可。\n"
    )
    body = yaml.dump(
        {"groups": groups},
        allow_unicode=True, sort_keys=False, default_flow_style=False,
    )
    output_path.write_text(header + body, encoding="utf-8")

    # サマリー出力
    shared_count = sum(1 for g in groups if g.get("shared"))
    normal_count = len(groups) - shared_count
    print(f"✅ グループ生成完了: {normal_count} 業務グループ + {shared_count} 共有グループ → {output_path}",
          file=sys.stderr)
    print("", file=sys.stderr)
    for g in groups:
        shared_label = " [共有]" if g.get("shared") else ""
        members = ", ".join(f["api_name"] for f in g["features"])
        print(f"  {g['group_id']}{shared_label} [{g['name_en']}] {g['name_ja']}")
        print(f"    {members}")


if __name__ == "__main__":
    main()
