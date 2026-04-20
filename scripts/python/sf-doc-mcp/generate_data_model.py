#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データモデル定義書 PPTX 生成スクリプト

入力:
  docs/catalog/_index.md       — オブジェクト一覧・カテゴリ分類
  docs/catalog/_data-model.md  — ER図・リレーション定義
  docs/catalog/custom/*.md     — カスタムオブジェクト定義
  docs/catalog/standard/*.md   — 標準オブジェクト定義

出力:
  データモデル定義書.pptx

Usage:
  python generate_data_model.py \\
    --docs-dir <path/to/project/docs> \\
    --output-dir <output dir> \\
    --author "作成者名"
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

_SKIP_FIELDS = {
    "Id", "OwnerId", "CreatedById", "LastModifiedById",
    "CreatedDate", "LastModifiedDate", "SystemModstamp",
    "IsDeleted", "CurrencyIsoCode",
    "RecordTypeId",
}

# カテゴリ分類ルール（キーワード → バケット）
# _index.md の見出し文字列にキーワードが含まれていれば、対応する分類を適用する。
# これにより、プロジェクトごとに異なるカテゴリ見出しでも自動で正しく分類される。
_CATEGORY_RULES = [
    # (正規表現, 分類 tx/mst/std/sup, スタイルキー)
    (r"(トランザクション|Transaction|取引|業務)",     "tx",  "primary"),
    (r"(マスタ|マスター|Master)",                      "mst", "accent"),
    (r"(標準|Standard|標準オブジェクト)",              "std", "secondary"),
    (r"(補助|制御|ログ|Support|Log|Helper|一時|Tmp)", "sup", "light"),
]


def classify_category(cat_name: str) -> tuple:
    """カテゴリ名 → (bucket, style)。該当なしは (sup, light)。"""
    for pat, bucket, style in _CATEGORY_RULES:
        if re.search(pat, cat_name, re.IGNORECASE):
            return bucket, style
    return "sup", "light"

HDR_H      = 0.62   # er_utils.py と同期 (0.52→0.62)
FIELD_H    = 0.32   # er_utils.py と同期 (0.28→0.32)
MIN_BODY_H = 0.36
MAX_FIELDS = 8


# ── パース: _index.md ──────────────────────────────────────────────────────────

def parse_index(path: Path) -> dict:
    """_index.md から カテゴリ → オブジェクトリスト を返す。

    ## レベル見出し（例: ## 標準オブジェクト）も ### サブカテゴリなしで
    直接テーブルを持つ場合はそのまま 1 カテゴリとして取り込む。
    ### レベル見出しがあれば優先してサブカテゴリ名を使用する。
    オブジェクト一覧でない見出し（サマリ・全体図・注記等）はスキップする。
    """
    # オブジェクト定義として扱わない ## セクション見出しのパターン
    _SKIP_H2_PATTERNS = re.compile(
        r'(サマリ|全体図|所見|注意|データモデル全体|カスタム項目数|主な所見)',
        re.IGNORECASE,
    )

    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    categories = {}
    current_h2 = None   # ## レベル見出し（カテゴリ候補）
    current_h3 = None   # ### レベル見出し（具体カテゴリ名）
    skip_section = False  # 現在のセクションをスキップするフラグ

    def _active_cat():
        # ### があればそちらを優先、なければ ## を使う
        if skip_section:
            return None
        return current_h3 or current_h2

    for line in text.splitlines():
        # ## 見出し: h2 更新、h3 リセット
        m2 = re.match(r'^##\s+(.+)', line)
        if m2:
            current_h2 = m2.group(1).strip()
            current_h3 = None
            skip_section = bool(_SKIP_H2_PATTERNS.search(current_h2))
            if not skip_section:
                # ## レベル自体もカテゴリ候補として登録しておく
                categories.setdefault(current_h2, [])
            continue
        # ### 見出し: h3 更新
        m3 = re.match(r'^###\s+(.+)', line)
        if m3:
            current_h3 = m3.group(1).strip()
            if not skip_section:
                categories.setdefault(current_h3, [])
            continue
        # テーブル行
        cat = _active_cat()
        if not cat or not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        label, api_name = cols[0], cols[1].strip('`')
        if (not label or label.startswith("---") or label == "オブジェクト"
                or api_name.startswith("---")
                or re.match(r'\[.+\]\(.+\)', api_name)):
            continue
        # API名が英数字・アンダースコアのみで構成されている（正規 API 名）か検証
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', api_name):
            continue
        # 同じオブジェクトが重複登録されないよう確認
        existing_apis = {o["api_name"] for o in categories[cat]}
        if api_name not in existing_apis:
            categories[cat].append({"label": label, "api_name": api_name})
    # 空カテゴリを除去
    return {k: v for k, v in categories.items() if v}


# ── パース: _data-model.md ────────────────────────────────────────────────────

def _derive_fk_from_fields(parent: str, child_lookup_fields: list[str]) -> str:
    """親オブジェクト名と子のlookupフィールドリストからFKフィールドを推定する。

    例: parent="Account", fields=["Account__c","Opportunity__c"] → "Account__c"
        parent="BusinessTravelerHeader__c", fields=["BusinessTravelerHeader__c"] → "BusinessTravelerHeader__c"
        parent="Opportunity", fields=["OpportunityId__c","Opportunity__c"] → "Opportunity__c"
    """
    parent_base = re.sub(r'__[cm]$', '', parent, flags=re.IGNORECASE).lower()
    # 完全一致（ベース名）を優先
    for fld in child_lookup_fields:
        fld_base = re.sub(r'__[cm]$', '', fld, flags=re.IGNORECASE).lower()
        if fld_base == parent_base:
            return fld
    # 前方一致（OpportunityId__c → Opportunity）
    for fld in child_lookup_fields:
        fld_base = re.sub(r'__[cm]$', '', fld, flags=re.IGNORECASE).lower()
        if fld_base.startswith(parent_base) or parent_base.startswith(fld_base):
            return fld
    return ""


def parse_relations(path: Path) -> list:
    """リレーション一覧テーブル + Mermaid erDiagram からリレーションを返す。
    各リレーションに fk_field（FKフィールドAPI名）を付与する。
    Returns: [{parent, child, label, type, fk_field}]
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    # 主従テーブルから親子ペア取得（**主従 形式と MasterDetail 両対応）
    md_pairs = set()
    for m in re.finditer(r'\|\s*(`?)(\w+)\1\s*\|\s*(`?)(\w+)\3\s*\|\s*(MasterDetail|\*\*?主従)', text, re.IGNORECASE):
        md_pairs.add((m.group(2), m.group(4)))

    # リレーション一覧テーブルから FK フィールド名を取得
    # 形式: | 親オブジェクト | 子オブジェクト | 関係種別 | 項目 |
    fk_map = {}  # (parent, child) -> fk_field
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 4:
            continue
        parent_raw, child_raw, rel_kind, fk_field = cols[0], cols[1], cols[2], cols[3]
        # バッククォート・マークダウンを除去してから判定
        parent = re.sub(r'[\*`]', '', parent_raw).strip()
        child  = re.sub(r'[\*`]', '', child_raw).strip()
        fk     = re.sub(r'[\*`]', '', fk_field).strip()
        # ヘッダー・セパレーターをスキップ
        if not re.match(r'\w', parent) or parent == "親オブジェクト":
            continue
        # FKフィールドが複数ある場合は最初だけ（括弧内の説明を除く）
        fk = re.split(r'[（(、,/ ]', fk)[0].strip()
        # API名らしいもの（英数字アンダースコアのみ）だけ採用
        if parent and child and fk and re.match(r'^\w+$', fk) and not re.search(r'[\u3040-\u9fff]', fk):
            fk_map[(parent, child)] = fk

    # Mermaid erDiagram をパース
    mermaid_m = re.search(r'```mermaid\nerDiagram\n(.*?)```', text, re.DOTALL)
    if not mermaid_m:
        return []

    mermaid_body = mermaid_m.group(1)

    # エンティティのフィールドブロックからlookup/masterdetailフィールドを収集
    # entity_lookup_fields: {entity_api_name: [field_api_name, ...]}
    entity_lookup_fields: dict[str, list] = {}
    for ent_m in re.finditer(r'(\w+)\s*\{([^}]*)\}', mermaid_body, re.DOTALL):
        ent_name = ent_m.group(1)
        fields = []
        for fline in ent_m.group(2).splitlines():
            fline = fline.strip()
            fm = re.match(r'(lookup|masterdetail)\s+(\w+)', fline, re.IGNORECASE)
            if fm:
                fields.append(fm.group(2))
        if fields:
            entity_lookup_fields[ent_name] = fields

    relations = []
    seen = set()
    for line in mermaid_body.splitlines():
        line = line.strip()
        if not line or line.startswith('%'):
            continue
        m = re.match(r'(\w+)\s+(\S+)\s+(\w+)\s*:\s*"(.+)"', line)
        if not m:
            continue
        a, marker, b, label = m.group(1), m.group(2), m.group(3), m.group(4)
        if a == b:
            continue
        raw_parent, raw_child = (b, a) if marker.startswith("}") else (a, b)
        if (raw_parent, raw_child) in md_pairs:
            parent, child, rel_type = raw_parent, raw_child, "master_detail"
        elif (raw_child, raw_parent) in md_pairs:
            parent, child, rel_type = raw_child, raw_parent, "master_detail"
        else:
            parent, child, rel_type = raw_parent, raw_child, "lookup"
        key = (parent, child)
        if key in seen:
            continue
        seen.add(key)
        # テーブル由来のFKを優先、なければエンティティフィールドから自動導出
        fk_field = fk_map.get(key, fk_map.get((raw_parent, raw_child), ""))
        if not fk_field:
            child_fields = entity_lookup_fields.get(child, [])
            fk_field = _derive_fk_from_fields(parent, child_fields)
        # 標準オブジェクト同士の標準FK規則: Account→Opportunity = AccountId
        if not fk_field and not parent.endswith(("__c", "__mdt")) and not child.endswith(("__c", "__mdt")):
            fk_field = parent + "Id"
        relations.append({
            "parent":   parent,
            "child":    child,
            "label":    label,
            "type":     rel_type,
            "fk_field": fk_field,
        })
    return relations


# ── パース: 個別オブジェクト MD ───────────────────────────────────────────────

def _parse_fields_from_mermaid(text: str) -> list:
    """Mermaid erDiagram { } ブロックからフィールドを抽出（カスタムオブジェクト用）"""
    fields = []
    mermaid_m = re.search(r'```mermaid\n.*?erDiagram\n(.*?)```', text, re.DOTALL)
    if not mermaid_m:
        return fields
    # (?m) で行頭アンカー: "ObjectName {" の形式のブロックのみマッチ
    # （"||--o{" など関係行中の "{" にはマッチしない）
    block_m = re.search(r'(?m)^\s*\w[\w_]+\s*\{([^}]+)\}', mermaid_m.group(1), re.DOTALL)
    if not block_m:
        return fields
    for fline in block_m.group(1).splitlines():
        fline = fline.strip()
        if not fline:
            continue
        fm = re.match(r'(\w+)\s+(\w+)(?:\s+"([^"]+)")?', fline)
        if not fm:
            continue
        api, ftype, flabel = fm.group(1), fm.group(2), fm.group(3) or fm.group(1)
        if api in _SKIP_FIELDS or (api == "Id" and ftype.lower() in ("id", "pk")):
            continue
        is_fk = (ftype.lower() in ("id", "reference")
                 and (api.endswith("__c") or (api.endswith("Id") and api not in _SKIP_FIELDS)))
        fields.append({"api_name": api, "type": ftype.lower(), "label": flabel, "is_fk": is_fk})
    return fields


def _parse_fields_from_table(text: str) -> list:
    """フィールドテーブルから抽出。以下の2形式に対応:
    1. ## 主要カスタム項目 （標準オブジェクト用）
    2. ## 項目一覧 > ### カスタム項目 / ### 標準項目（カタログ生成形式）
    """
    fields = []

    def _parse_table_block(block: str) -> list:
        result = []
        # 列インデックス: ヘッダー行から自動検出（デフォルトは旧形式: label=0, api=1, type=2）
        api_col, label_col, dtype_col = 1, 0, 2
        detected = False
        for line in block.splitlines():
            if not line.strip().startswith("|"):
                continue
            cols = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cols) < 3:
                continue
            # 区切り行スキップ
            if all(c.startswith("---") or not c for c in cols):
                continue
            # ヘッダー行検出: "API名" または "項目名" が含まれる行
            if not detected and any(c in ("API名", "項目名") for c in cols):
                detected = True
                for ci, ch in enumerate(cols):
                    if ch in ("API名", "項目名"):
                        api_col = ci
                    elif ch in ("表示ラベル", "ラベル"):
                        label_col = ci
                    elif ch == "型":
                        dtype_col = ci
                continue
            if len(cols) <= max(api_col, label_col, dtype_col):
                continue
            api_name = cols[api_col].strip("`").strip()
            label    = re.sub(r'\*+', '', cols[label_col]).strip()
            dtype    = cols[dtype_col] if dtype_col < len(cols) else ""
            if not api_name or api_name.startswith("---") or api_name in ("API名", "項目名"):
                continue
            if api_name in _SKIP_FIELDS:
                continue
            if not re.match(r'^[A-Za-z_]\w*$', api_name):
                continue
            dtype_clean = dtype.split("(")[0].strip().lower()
            is_fk = dtype_clean in ("reference", "lookup", "master_detail", "masterdetail")
            result.append({"api_name": api_name, "type": dtype_clean,
                           "label": label, "is_fk": is_fk})
        return result

    # 形式1: ## 主要カスタム項目
    m1 = re.search(r'##\s+主要カスタム項目\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if m1:
        return _parse_table_block(m1.group(1))

    # 形式2: ## 項目一覧 配下を走査（### サブセクションあり・なし両対応）
    m2 = re.search(r'##\s+項目一覧\n(.*?)(?=\n##\s|\Z)', text, re.DOTALL)
    if m2:
        block = m2.group(1)
        seen_apis: set = set()
        sub_sections = list(re.finditer(r'###\s+.+?\n(.*?)(?=\n###|\Z)', block, re.DOTALL))
        if sub_sections:
            # ### サブセクションあり: 全サブセクションからFK抽出
            for sub_m in sub_sections:
                for f in _parse_table_block(sub_m.group(1)):
                    if f["api_name"] not in seen_apis:
                        seen_apis.add(f["api_name"])
                        if f["is_fk"]:
                            fields.append(f)
        else:
            # ### サブセクションなし: 直接テーブルを解析
            for f in _parse_table_block(block):
                if f["api_name"] not in seen_apis:
                    seen_apis.add(f["api_name"])
                    if f["is_fk"]:
                        fields.append(f)
    return fields


def parse_object_fields(md_path: Path) -> dict:
    """個別オブジェクト MD から説明・キー項目リスト・OWD・レコード数を返す。"""
    if not md_path.exists():
        return {"description": "", "fields": [], "owd": "", "record_count": ""}
    text = md_path.read_text(encoding="utf-8")
    desc = ""
    m = re.search(r'\|\s*説明\s*\|\s*(.+?)\s*\|', text)
    if m:
        desc = m.group(1).strip()

    # OWD（共有モデル）
    owd_m = re.search(r'\|\s*共有モデル\s*\|\s*(.+?)\s*\|', text)
    owd = owd_m.group(1).strip() if owd_m else ""
    # マークダウン装飾を除去
    owd = re.sub(r'\*+', '', owd).strip()

    # レコード数
    rc_m = re.search(r'\|\s*レコード数\s*\|\s*(.+?)\s*\|', text)
    record_count = rc_m.group(1).strip() if rc_m else ""
    record_count = re.sub(r'\*+', '', record_count).strip()

    # ── FK フィールド: ## リレーション テーブルを正とする（常に実行） ──
    # 「参照（子）」「主従（子）」は相手側に FK があるのでスキップ。
    # 項目名セルは "ContactName__c（委託担当者1〜5）" のような注釈付きを除去して API 名を取得。
    fk_from_relation: dict = {}  # api_name → {"api_name", "label"(=参照先), "type", "is_fk"}
    rel_section = re.search(r'##\s+リレーション\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if rel_section:
        for row in rel_section.group(1).splitlines():
            if not row.strip().startswith("|"):
                continue
            cols = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cols) < 3:
                continue
            target_obj, rel_type, item_name = cols[0], cols[1], cols[2]
            if "子" in rel_type or target_obj in ("関連先オブジェクト", "---"):
                continue  # 子側リレーション・ヘッダ・区切りはスキップ
            # 項目名から API 名を抽出（「（コメント）」を除去、先頭の API 名だけ取る）
            api_raw = re.split(r'[（(]', item_name)[0].strip()
            api_raw = re.sub(r'[\s、,]+.*', '', api_raw).strip()  # 複数列挙の2件目以降削除
            if not api_raw or not re.match(r'^[A-Za-z_]\w*$', api_raw):
                continue
            if api_raw in _SKIP_FIELDS:
                continue
            rel_kind = "master_detail" if "主従" in rel_type else "reference"
            fk_from_relation[api_raw] = {
                "api_name": api_raw,
                "label":    re.sub(r'\*+', '', target_obj).strip(),  # 参照先オブジェクト名
                "type":     rel_kind,
                "is_fk":    True,
            }

    # ── 非 FK フィールド: Mermaid → テーブル の順で補完 ──
    all_parsed = _parse_fields_from_mermaid(text)
    if not all_parsed:
        all_parsed = _parse_fields_from_table(text)

    # relation テーブルの FK を正とし、テーブル/Mermaid で見つかった FK を補完
    non_fk = [f for f in all_parsed if not f.get("is_fk") and f["api_name"] not in _SKIP_FIELDS]
    fk_fields = list(fk_from_relation.values())
    existing_fk_apis = {f["api_name"] for f in fk_fields}
    for f in all_parsed:
        if f.get("is_fk") and f["api_name"] not in existing_fk_apis:
            fk_fields.append(f)
            existing_fk_apis.add(f["api_name"])
    other_fields = non_fk
    selected = (fk_fields + other_fields)[:MAX_FIELDS]
    return {"description": desc, "fields": selected,
            "owd": owd, "record_count": record_count}


def load_all_object_fields(catalog_dir: Path, api_names: list,
                           label_map: dict = None) -> dict:
    result = {}
    for api_name in api_names:
        if api_name.endswith("__c") or api_name.endswith("__kav"):
            md_path = catalog_dir / "custom" / f"{api_name}.md"
        else:
            md_path = catalog_dir / "standard" / f"{api_name}.md"
        info = parse_object_fields(md_path)
        if label_map:
            for fld in info.get("fields", []):
                if fld.get("is_fk"):
                    target_api = fld["api_name"]
                    target_obj = re.sub(r'__c$', '', target_api)
                    if target_obj in label_map:
                        fld["ref_label"] = label_map[target_obj]
        result[api_name] = info
    return result


# ── レイアウト計算 ─────────────────────────────────────────────────────────────

def compute_box_h(n_fields: int) -> float:
    body = max(MIN_BODY_H, n_fields * FIELD_H)
    return round(HDR_H + body, 3)


def layout_hierarchical(node_ids, relations, box_heights,
                         x0, y0, x1, y1, box_w=2.8):
    """階層配置（親→子 を左→右）。
    同レイヤーに収まらない場合は隣レイヤーに溢れさせて縦オーバーフローを防ぐ。
    最終的に全ボックスの重なりを検出して補正する。
    """
    node_set = set(node_ids)
    children = defaultdict(list)
    parents  = defaultdict(list)
    for r in relations:
        p, c = r["parent"], r["child"]
        if p in node_set and c in node_set and p != c:
            children[p].append(c)
            parents[c].append(p)
    roots = sorted(n for n in node_ids if not parents[n])
    if not roots:
        roots = node_ids[:1]
    layer = {}
    q = deque()
    for r in roots:
        layer[r] = 0
        q.append(r)
    while q:
        node = q.popleft()
        for child in children[node]:
            new_l = layer[node] + 1
            if child not in layer or layer[child] < new_l:
                layer[child] = new_l
                q.append(child)
    max_l = max(layer.values(), default=0)
    for n in node_ids:
        if n not in layer:
            layer[n] = max_l + 1

    by_layer = defaultdict(list)
    for n, l in layer.items():
        by_layer[l].append(n)
    for l in by_layer:
        by_layer[l].sort(key=lambda n: -len(children[n]))

    # ── 縦オーバーフロー対策: 各レイヤーの高さが利用可能高を超える場合、
    #    超過分を隣レイヤー（親側優先 → 末尾レイヤー）に移す
    ROW_GAP = 0.18
    avail_h = y1 - y0
    def layer_needed_h(nodes):
        return sum(box_heights.get(n, HDR_H + MIN_BODY_H) for n in nodes) + \
               ROW_GAP * (len(nodes) - 1)

    for _ in range(3):  # 複数回試行
        changed = False
        for l in sorted(by_layer.keys()):
            while layer_needed_h(by_layer[l]) > avail_h and len(by_layer[l]) > 1:
                # 末尾（=子が少ない）を 1 つ取り出し、子レイヤーに寄せる
                moved = by_layer[l].pop()
                target_l = l + 1 if (l + 1) in by_layer else l - 1
                if target_l < 0:
                    target_l = l + 1
                by_layer.setdefault(target_l, []).append(moved)
                changed = True
        if not changed:
            break

    n_layers = max(by_layer.keys()) + 1
    col_step = (x1 - x0) / max(n_layers, 1)
    actual_box_w = min(box_w, col_step - 0.25, 3.2)

    positions = {}
    for l in sorted(by_layer.keys()):
        nodes_in_layer = by_layer[l]
        col_cx = x0 + l * col_step + col_step / 2
        heights = [box_heights.get(n, HDR_H + MIN_BODY_H) for n in nodes_in_layer]
        n = len(nodes_in_layer)
        x = col_cx - actual_box_w / 2
        if n == 1:
            # 単独オブジェクトは中央に配置
            nid = nodes_in_layer[0]
            h = heights[0]
            y = (y0 + y1) / 2 - h / 2
            y = max(y0, min(y, y1 - h))
            positions[nid] = (x, y, actual_box_w, h)
        else:
            # 等間隔配置: y0〜y1 の範囲を n 分割し、各スロット中央に配置
            slot_h = (y1 - y0) / n
            for i, nid in enumerate(nodes_in_layer):
                h = heights[i]
                cy = y0 + slot_h * i + slot_h / 2
                y = max(y0, min(cy - h / 2, y1 - h))
                positions[nid] = (x, y, actual_box_w, h)

    # ── 重なり補正（ペア単位）: 同じ矩形範囲に入ってしまうボックスを縦方向にずらす
    def _overlap(a, b, mx=0.05, my=0.05):
        ax, ay, aw, ah = a
        bx, by_, bw, bh = b
        return (ax < bx + bw - mx and ax + aw > bx + mx and
                ay < by_ + bh - my and ay + ah > by_ + my)

    ids = list(positions.keys())
    for _ in range(5):
        moved = False
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = positions[ids[i]], positions[ids[j]]
                if _overlap(a, b):
                    # 下側の b を a の直下へ移動
                    if a[1] <= b[1]:
                        shift = (a[1] + a[3] + ROW_GAP) - b[1]
                        positions[ids[j]] = (b[0], min(b[1] + shift, y1 - b[3]),
                                              b[2], b[3])
                    else:
                        shift = (b[1] + b[3] + ROW_GAP) - a[1]
                        positions[ids[i]] = (a[0], min(a[1] + shift, y1 - a[3]),
                                              a[2], a[3])
                    moved = True
        if not moved:
            break

    return {nid: (round(x, 3), round(y, 3), round(w, 3), round(h, 3))
            for nid, (x, y, w, h) in positions.items()}


# ── スライド JSON 組み立て ──────────────────────────────────────────────────────

def _build_object_list_table(categories: dict, object_fields: dict) -> dict:
    rows = []
    for cat, objs in categories.items():
        for obj in objs:
            api  = obj["api_name"]
            desc = object_fields.get(api, {}).get("description", "")[:120] or "—"
            rows.append([cat, obj["label"], api, desc])
    return {
        "layout": "table",
        "title":  "オブジェクト一覧",
        "table": {
            "headers":    ["カテゴリ", "オブジェクト名", "API名", "説明"],
            "col_widths": [2.2, 2.5, 3.5, 3.5],
            "rows":       rows[:28],
        },
    }


def _build_er_slide(title, node_ids, cat_map, label_map,
                    object_fields, relations, style_by_api, box_w=2.8,
                    ref_only_ids=None):
    """ER図スライドを組み立てる。

    ref_only_ids: メインレイアウトから外し、画面右端に小ボックスで配置するオブジェクト
    """
    ref_only_ids = list(ref_only_ids or [])
    ref_only_set = set(ref_only_ids)
    main_nodes = [nid for nid in node_ids if nid not in ref_only_set]

    def _er_fields(nid):
        """ER図用: 参照/主従 FK フィールドのみ返す"""
        return [f for f in object_fields.get(nid, {}).get("fields", []) if f.get("is_fk")]

    box_heights = {
        nid: compute_box_h(len(_er_fields(nid)))
        for nid in main_nodes
    }
    # メインレイアウト領域を右端 ref_only 用に少し狭める
    main_x1 = 10.6 if ref_only_ids else 13.18
    positions = layout_hierarchical(
        main_nodes, relations, box_heights,
        x0=0.15, y0=1.1, x1=main_x1, y1=7.38, box_w=box_w,
    )
    boxes = []
    for nid, (x, y, w, h) in positions.items():
        label = label_map.get(nid, nid)
        oinfo = object_fields.get(nid, {"fields": []})
        boxes.append({
            "id": nid, "label": label, "api_name": nid,
            "fields": _er_fields(nid),
            "x": x, "y": y, "w": w, "h": h,
            "style": style_by_api.get(nid, "light"),
            "owd":          oinfo.get("owd", ""),
            "record_count": oinfo.get("record_count", ""),
        })

    # ref_only ボックスを右端にスタック配置
    if ref_only_ids:
        rx0, rx1 = 10.8, 13.15
        ry0, ry1 = 1.1, 7.38
        rw = rx1 - rx0
        rh = 0.52  # ヘッダーのみ
        n = len(ref_only_ids)
        slot_h = (ry1 - ry0) / max(n, 1)
        for i, nid in enumerate(ref_only_ids):
            label = label_map.get(nid, nid)
            cy = ry0 + slot_h * i + slot_h / 2
            y = max(ry0, min(cy - rh / 2, ry1 - rh))
            oinfo = object_fields.get(nid, {"fields": []})
            boxes.append({
                "id": nid, "label": label, "api_name": nid,
                "fields": [],
                "x": round(rx0, 3), "y": round(y, 3),
                "w": round(rw, 3), "h": round(rh, 3),
                "style": "ref",
                "ref_only": True,
                "owd":          oinfo.get("owd", ""),
                "record_count": oinfo.get("record_count", ""),
            })

    node_set = set(node_ids)
    arrows = []
    seen = set()
    for r in relations:
        p, c = r["parent"], r["child"]
        if p not in node_set or c not in node_set or p == c:
            continue
        key = (p, c)
        if key in seen:
            continue
        seen.add(key)
        arr = {
            "from":  p,
            "to":    c,
            "label": r.get("fk_field") or r["label"],
        }
        if r["type"] == "master_detail":
            arr["arrow_style"] = "master_detail"
        arrows.append(arr)
    return {
        "layout":   "er",
        "title":    title,
        "elements": {"boxes": boxes, "arrows": arrows},
    }


def _build_tx_er_core(title, label_map, object_fields, relations, style_by_api):
    """TX コアフロー ER図 — 固定グリッドレイアウト（7オブジェクト専用）。
    ref_only ボックスなし・TX間リレーションのみ描画。
    """
    GRID_POS = {
        "BusinessTravelerHeader__c": (0, 0),
        "Quote__c":                   (1, 0),
        "Billing__c":                 (2, 0),
        "PaymentManagement__c":       (3, 0),
        "BusinessTraveler__c":        (0, 1),
        "QuoteDetail__c":             (1, 1),
        "BillingDetail__c":           (2, 1),
    }
    COL_W    = 3.3
    BOX_W    = 2.8   # COL_W - BOX_W = 0.5" ギャップ（矢印の余白）
    X0       = 0.1
    SLIDE_H  = 7.5
    TITLE_H  = 1.1   # タイトル行の占有高さ
    ROW_GAP  = 0.5   # 行間の最低ギャップ

    tx_apis = set(GRID_POS.keys())

    # 各ボックスの高さを先に計算（ER図: FK フィールドのみ表示）
    box_info = {}
    for api, (col, row) in GRID_POS.items():
        if api not in label_map:
            continue
        oinfo   = object_fields.get(api, {"fields": []})
        fk_only = [f for f in oinfo.get("fields", []) if f.get("is_fk")]
        box_info[api] = {"oinfo": oinfo, "fk_fields": fk_only,
                         "h": compute_box_h(len(fk_only)), "col": col, "row": row}

    # 行ごとの最大高さ
    row_max_h = {}
    for api, info in box_info.items():
        r = info["row"]
        row_max_h[r] = max(row_max_h.get(r, 0), info["h"])

    # Y_ROW を自動計算: 2行を上下均等配置してスライドを埋める
    BOTTOM   = SLIDE_H - 0.15
    row0_h   = row_max_h.get(0, 0)
    row1_h   = row_max_h.get(1, 0)
    total_h  = row0_h + row1_h
    avail    = BOTTOM - TITLE_H
    gap      = max(ROW_GAP, (avail - total_h) / max(1, len(row_max_h)))
    row0_top = TITLE_H
    row1_top = row0_top + row0_h + gap
    # はみ出し保護
    if row1_top + row1_h > BOTTOM:
        row1_top = BOTTOM - row1_h
    Y_ROW = [row0_top, row1_top]

    # 行の中心Y = Y_ROW[row] + max_h/2
    row_center_y = {r: Y_ROW[r] + row_max_h[r] / 2 for r in row_max_h}

    # ボックス配置: 中心Y を揃える
    boxes = []
    for api, info in box_info.items():
        col, row = info["col"], info["row"]
        h = info["h"]
        oinfo = info["oinfo"]
        x = round(X0 + col * COL_W, 3)
        y = round(row_center_y[row] - h / 2, 3)  # 中心Y から上端を逆算
        boxes.append({
            "id": api, "label": label_map.get(api, api), "api_name": api,
            "fields": info["fk_fields"],
            "x": x, "y": y, "w": BOX_W, "h": h,
            "style": style_by_api.get(api, "primary"),
            "owd":          oinfo.get("owd", ""),
            "record_count": oinfo.get("record_count", ""),
        })

    arrows = []
    seen = set()
    for r in relations:
        p, c = r["parent"], r["child"]
        if p not in tx_apis or c not in tx_apis or p == c:
            continue
        key = (p, c)
        if key in seen:
            continue
        seen.add(key)
        arr = {"from": p, "to": c, "label": r.get("fk_field") or r["label"]}
        if r["type"] == "master_detail":
            arr["arrow_style"] = "master_detail"
        # 接続辺を明示: 同列（縦MD）= bottom→top、同行（横Lookup）= right→left
        p_col, p_row = GRID_POS.get(p, (0, 0))
        c_col, c_row = GRID_POS.get(c, (0, 0))
        if p_col == c_col:  # 縦方向（MD）
            arr["side_from"] = "bottom" if p_row < c_row else "top"
            arr["side_to"]   = "top"    if p_row < c_row else "bottom"
        else:               # 横方向（Lookup）
            arr["side_from"] = "right" if p_col < c_col else "left"
            arr["side_to"]   = "left"  if p_col < c_col else "right"
        arrows.append(arr)

    return {
        "layout":   "er",
        "title":    title,
        "elements": {"boxes": boxes, "arrows": arrows},
    }


def _build_tx_er_grouped(title, std_ext_apis, mst_ext_apis,
                          label_map, object_fields, relations, style_by_api):
    """TX ER図拡張版 — TX（単列・左）＋ 外部オブジェクト個別ボックス（単列・右）。
    右列: 標準オブジェクト（上）→ マスタ系（下）の順で縦並び。
    TX を上から下へ1列に配置し、fraction で接続点を分散させて矢印の交差を排除。
    参照項目（FK）を各TXボックスに表示。
    """
    TX_ORDER = [
        "BusinessTravelerHeader__c",  # STD(Account, Opportunity)
        "BusinessTraveler__c",         # STD(Contact) + MST
        "Quote__c",                    # MST
        "QuoteDetail__c",              # MST
        "Billing__c",                  # MST
        "BillingDetail__c",            # MST
        "PaymentManagement__c",        # 外部参照なし
    ]
    TX_X            = 0.15
    TX_W            = 3.5
    TX_GAP          = 0.12
    TX_Y0           = 1.1
    COMPACT_FIELD_H = 0.32

    RGT_X       = 8.4
    RGT_W       = 4.8
    RGT_GAP     = 0.22   # 外部ボックス間隔
    RGT_Y0      = 1.1
    STD_MST_SEP = 0.50   # STD→MST 間の追加スペース

    tx_api_set = set(TX_ORDER)
    std_set    = set(std_ext_apis)
    mst_set    = set(mst_ext_apis)
    ext_apis   = std_set | mst_set

    # TX ↔ EXT の接続を事前収集
    ext_connections: dict = {}  # ext_api → [(tx_api, rel), ...]
    tx_connections:  dict = {}  # tx_api  → [(ext_api, rel), ...]
    for r in relations:
        p, c = r["parent"], r["child"]
        ext_api = tx_api = None
        if p in ext_apis and c in tx_api_set:
            ext_api, tx_api = p, c
        elif c in ext_apis and p in tx_api_set:
            ext_api, tx_api = c, p
        if ext_api and tx_api and tx_api in label_map:
            ext_connections.setdefault(ext_api, []).append((tx_api, r))
            tx_connections.setdefault(tx_api,   []).append((ext_api, r))

    # valid_tx: 外部参照のあるTXオブジェクトのみ
    valid_tx = [api for api in TX_ORDER if api in label_map and api in tx_connections]

    SLIDE_H    = 7.5
    BOTTOM     = SLIDE_H - 0.15
    MIN_GAP    = 0.12   # ボックス間の最小隙間
    FILL_RATIO = 0.70   # これを下回ったらボックスを引き伸ばす

    # ── TX ボックス（単列・左） ──
    boxes = []
    tx_items = []
    for api in valid_tx:
        oinfo     = object_fields.get(api, {"fields": []})
        all_fk    = [f for f in oinfo.get("fields", []) if f.get("is_fk")]
        fk_fields = all_fk[:2]   # 初期は2件
        h = round(HDR_H + max(len(fk_fields), 1) * COMPACT_FIELD_H, 3)
        tx_items.append((api, oinfo, all_fk, fk_fields, h))

    if tx_items:
        n         = len(tx_items)
        avail_tx  = BOTTOM - TX_Y0
        total_nat = sum(h for *_, h in tx_items)

        # スパース判定: 自然な高さが利用可能領域の FILL_RATIO 未満 → 引き伸ばす
        if total_nat < avail_tx * FILL_RATIO:
            total_gap = MIN_GAP * (n - 1)
            per_h     = (avail_tx - total_gap) / n
            new_items = []
            for api, oinfo, all_fk, _, _ in tx_items:
                # 引き伸ばした高さに収まるだけFKフィールドを表示
                n_fit = max(1, int((per_h - HDR_H) / COMPACT_FIELD_H))
                fk_show = all_fk[:n_fit]
                new_items.append((api, oinfo, all_fk, fk_show, per_h))
            tx_items = new_items
            tx_gap = MIN_GAP
        else:
            tx_gap = max(TX_GAP, (avail_tx - total_nat) / max(n - 1, 1))

        y = TX_Y0
        for api, oinfo, _, fk_fields, h in tx_items:
            boxes.append({
                "id": api, "label": label_map.get(api, api), "api_name": api,
                "fields": fk_fields,
                "x": TX_X, "y": round(y, 3), "w": TX_W, "h": round(h, 3),
                "style": style_by_api.get(api, "primary"),
                "owd":          oinfo.get("owd", ""),
                "record_count": "",
            })
            y += h + tx_gap

    # ── 右列ボックス: STD（上）→ MST（下）、均等分散 ──
    rgt_order_std = [api for api in std_ext_apis if api in ext_connections and api in label_map]
    rgt_order_mst = [api for api in mst_ext_apis if api in ext_connections and api in label_map]
    rgt_all = rgt_order_std + rgt_order_mst

    if rgt_all:
        n_rgt        = len(rgt_all)
        avail_rgt    = BOTTOM - RGT_Y0
        total_rgt_h  = HDR_H * n_rgt

        # スパース判定: 引き伸ばして均等配置
        if total_rgt_h < avail_rgt * FILL_RATIO:
            total_gap_rgt = MIN_GAP * (n_rgt - 1)
            rgt_box_h     = (avail_rgt - total_gap_rgt) / n_rgt
            rgt_gap       = MIN_GAP
        else:
            rgt_box_h = HDR_H
            rgt_gap   = max(RGT_GAP, (avail_rgt - total_rgt_h) / max(n_rgt - 1, 1))

        rgt_y = RGT_Y0
        for api in rgt_all:
            style = "secondary" if api in rgt_order_std else "accent"
            oinfo = object_fields.get(api, {"fields": []})
            boxes.append({
                "id": api, "label": label_map.get(api, api), "api_name": api,
                "fields": [],
                "x": RGT_X, "y": round(rgt_y, 3), "w": RGT_W, "h": round(rgt_box_h, 3),
                "style": style,
                "owd":          oinfo.get("owd", ""),
                "record_count": "",
            })
            rgt_y += rgt_box_h + rgt_gap

    # ── 矢印: TX → 個別外部オブジェクト ──
    def _fracs_range(n, lo=0.2, hi=0.8):
        if n <= 1: return [0.5]
        return [round(lo + (hi - lo) * i / (n - 1), 3) for i in range(n)]

    arrows = []
    for tx_api in valid_tx:
        if tx_api not in tx_connections:
            continue
        # STD接続を先、MST接続を後にソート → TX右側出口の上下と右列の上下が対応
        std_exts = [(ea, r) for ea, r in tx_connections[tx_api] if ea in std_set]
        mst_exts = [(ea, r) for ea, r in tx_connections[tx_api] if ea in mst_set]
        ordered  = std_exts + mst_exts
        n = len(ordered)
        if n == 0:
            continue
        tx_fracs = _fracs_range(n)

        for j, (ext_api, rel) in enumerate(ordered):
            sf_frac = tx_fracs[j]
            # EXT側 frac: このEXTに繋がるTXのうち valid_tx 順でのインデックス
            tx_list = [a for a, _ in ext_connections.get(ext_api, []) if a in valid_tx]
            tx_ordered_for_ext = [a for a in valid_tx if a in tx_list]
            idx     = tx_ordered_for_ext.index(tx_api) if tx_api in tx_ordered_for_ext else 0
            st_frac = _fracs_range(len(tx_ordered_for_ext))[idx]
            arrows.append({
                "from": tx_api, "to": ext_api, "label": "",
                "side_from": "right", "side_to": "left",
                "side_from_frac": sf_frac,
                "side_to_frac":   st_frac,
            })

    return {
        "layout":   "er",
        "title":    title,
        "elements": {"boxes": boxes, "arrows": arrows},
    }


def _build_tx_er_grouped_pages(
        base_title, std_ext_apis, mst_ext_apis,
        label_map, object_fields, relations, style_by_api,
) -> list:
    """_build_tx_er_grouped をページ分割対応でラップ。
    TX オブジェクト数が多くスライド高さ(7.5")を超える場合、TX を分割して複数スライドを返す。
    """
    SLIDE_H         = 7.5
    TX_Y0           = 1.1
    TX_GAP          = 0.12
    COMPACT_FIELD_H = 0.32
    MAX_FK          = 2

    # valid_tx の高さ合計を事前計算して 1 枚に収まる最大 TX 数を求める
    TX_ORDER = [
        "BusinessTravelerHeader__c", "BusinessTraveler__c",
        "Quote__c", "QuoteDetail__c", "Billing__c", "BillingDetail__c",
        "PaymentManagement__c",
    ]
    tx_api_set  = set(TX_ORDER)
    ext_apis    = set(std_ext_apis) | set(mst_ext_apis)
    tx_conn_set: set = set()
    for r in relations:
        p, c = r["parent"], r["child"]
        if p in ext_apis and c in tx_api_set and c in label_map:
            tx_conn_set.add(c)
        elif c in ext_apis and p in tx_api_set and p in label_map:
            tx_conn_set.add(p)
    valid_tx = [a for a in TX_ORDER if a in label_map and a in tx_conn_set]

    def _tx_h(api):
        oinfo = object_fields.get(api, {"fields": []})
        fk_n  = min(len([f for f in oinfo.get("fields", []) if f.get("is_fk")]), MAX_FK)
        return round(HDR_H + fk_n * COMPACT_FIELD_H, 3)

    # TX を高さでチャンク分割
    AVAIL_H = SLIDE_H - TX_Y0 - 0.2  # 余白込み
    chunks: list[list] = []
    cur_chunk: list    = []
    cur_h              = 0.0
    for api in valid_tx:
        h = _tx_h(api) + (TX_GAP if cur_chunk else 0)
        if cur_chunk and cur_h + h > AVAIL_H:
            chunks.append(cur_chunk)
            cur_chunk = [api]
            cur_h     = _tx_h(api)
        else:
            cur_chunk.append(api)
            cur_h += h
    if cur_chunk:
        chunks.append(cur_chunk)

    if not chunks:
        return [_build_tx_er_grouped(
            base_title, std_ext_apis, mst_ext_apis,
            label_map, object_fields, relations, style_by_api,
        )]

    # チャンクが 1 つだけなら通常通り
    if len(chunks) == 1:
        return [_build_tx_er_grouped(
            base_title, std_ext_apis, mst_ext_apis,
            label_map, object_fields, relations, style_by_api,
        )]

    # 複数チャンク: TX_ORDER を上書きした一時関数で各スライドを生成
    slides = []
    for idx, chunk in enumerate(chunks):
        suffix = f"（{idx+1}/{len(chunks)}）" if len(chunks) > 1 else ""

        # _build_tx_er_grouped 内の TX_ORDER を chunk に差し替えて呼ぶ
        # → 関数をモンキーパッチせず、relations と valid_tx を chunk に絞った
        #    サブセットを渡すことで制御する（同じ関数を chunk 単位で呼ぶ）
        # 実装上の簡便策: TX_ORDER グローバル変数ではなく引数で渡せないため、
        # ここでは chunk に含まれない TX が接続する relations だけを渡すことで
        # valid_tx が chunk に絞られる
        chunk_set = set(chunk)
        chunk_relations = [
            r for r in relations
            if not (
                (r["parent"] in tx_api_set and r["parent"] not in chunk_set) or
                (r["child"]  in tx_api_set and r["child"]  not in chunk_set)
            )
        ]
        slide = _build_tx_er_grouped(
            f"{base_title}{suffix}",
            std_ext_apis, mst_ext_apis,
            label_map, object_fields, chunk_relations, style_by_api,
        )
        slides.append(slide)
    return slides


def _build_relation_table(relations: list, label_map: dict) -> list:
    """リレーション一覧テーブル（複数スライドに分割）"""
    rows = []
    for r in sorted(relations, key=lambda x: (x["type"] != "master_detail", x["parent"])):
        pl = label_map.get(r["parent"], r["parent"])
        cl = label_map.get(r["child"],  r["child"])
        rel_type = "主従（MD）" if r["type"] == "master_detail" else "参照（Lookup）"
        fk = r.get("fk_field", "—") or "—"
        rows.append([
            f"{pl}\n({r['parent']})",
            f"{cl}\n({r['child']})",
            fk,
            rel_type,
        ])
    slides = []
    for i in range(0, max(1, len(rows)), 13):
        chunk = rows[i:i+13]
        suffix = f" ({i//13+1})" if len(rows) > 13 else ""
        slides.append({
            "layout": "table",
            "title":  f"リレーション一覧{suffix}",
            "table": {
                "headers":    ["親オブジェクト", "子オブジェクト", "FKフィールド", "種別"],
                "col_widths": [3.2, 3.2, 3.3, 1.8],
                "rows":       chunk,
            },
        })
    return slides


def _build_master_table(master_objs, object_fields, relations):
    master_api = {o["api_name"] for o in master_objs}
    ref_from = defaultdict(list)
    for r in relations:
        if r["child"] in master_api and r["parent"] not in master_api:
            ref_from[r["child"]].append(r["parent"])
    rows = []
    for obj in master_objs:
        api  = obj["api_name"]
        desc = object_fields.get(api, {}).get("description", "")[:120] or "—"
        refs = "、".join(ref_from.get(api, []))[:40] or "—"
        rows.append([obj["label"], api, desc, refs])
    return {
        "layout": "table",
        "title":  "マスタ系オブジェクト詳細",
        "table": {
            "headers":    ["オブジェクト名", "API名", "説明", "主な参照元"],
            "col_widths": [2.5, 3.5, 3.0, 2.7],
            "rows":       rows,
        },
    }


def _build_support_table(sup_objs, object_fields):
    rows = [[o["label"], o["api_name"],
             object_fields.get(o["api_name"], {}).get("description", "")[:60] or "—"]
            for o in sup_objs]
    return {
        "layout": "table",
        "title":  "補助・制御 / ログ系オブジェクト",
        "table": {
            "headers":    ["オブジェクト名", "API名", "説明"],
            "col_widths": [2.5, 3.5, 5.7],
            "rows":       rows,
        },
    }


def build_json(categories, relations, object_fields, author, company):
    tx_objs, mst_objs, std_objs, sup_objs = [], [], [], []
    style_by_api = {}
    for cat, objs in categories.items():
        bucket, style = classify_category(cat)
        for obj in objs:
            obj["description"] = object_fields.get(obj["api_name"], {}).get("description", "")
            style_by_api[obj["api_name"]] = style
        if bucket == "tx":
            tx_objs.extend(objs)
        elif bucket == "mst":
            mst_objs.extend(objs)
        elif bucket == "std":
            std_objs.extend(objs)
        else:
            sup_objs.extend(objs)

    # TX が一件もない場合: _index.md の見出しがカテゴリルールに一致しなかった可能性が高い。
    # カスタムオブジェクト（__c）を TX 扱いにしてER図が出るようにするフォールバック。
    if not tx_objs:
        custom_sup = [o for o in sup_objs if o["api_name"].endswith("__c")]
        if custom_sup:
            tx_objs = custom_sup
            sup_objs = [o for o in sup_objs if not o["api_name"].endswith("__c")]
            for o in tx_objs:
                style_by_api[o["api_name"]] = "primary"

    cat_map = {}
    label_map = {}
    for cat, objs in categories.items():
        for obj in objs:
            cat_map[obj["api_name"]]   = cat
            label_map[obj["api_name"]] = obj["label"]

    # TX ER: TX + 直接接続する非TXオブジェクトを分析
    tx_api = {o["api_name"] for o in tx_objs}
    mst_api_set = {o["api_name"] for o in mst_objs}

    # TX に直接リンクする外部オブジェクトを収集（TX同士除外）
    connected_non_tx = set()
    for r in relations:
        if r["parent"] in tx_api and r["child"] not in tx_api:
            connected_non_tx.add(r["child"])
        if r["child"] in tx_api and r["parent"] not in tx_api:
            connected_non_tx.add(r["parent"])

    # 外部参照オブジェクトリスト（優先順位付き）
    STD_PRIORITY = ["Account", "Contact", "Opportunity"]
    MST_PRIORITY = ["Product__c", "VisaApplicationTypeMaster__c", "ExternalAccount__c"]
    ext_api_list = []
    for api in STD_PRIORITY:
        if api in connected_non_tx:
            ext_api_list.append(api)
            if api not in label_map:
                std_obj = next((o for o in std_objs if o["api_name"] == api), None)
                label_map[api] = std_obj["label"] if std_obj else api
            style_by_api.setdefault(api, "secondary")
    for api in MST_PRIORITY:
        if api in connected_non_tx:
            ext_api_list.append(api)
            if api not in label_map:
                obj = next((o for o in mst_objs + sup_objs if o["api_name"] == api), None)
                label_map[api] = obj["label"] if obj else api
            style_by_api.setdefault(api, "accent" if api in mst_api_set else "light")
    # 上記リストにない残りの外部参照も補完
    for api in sorted(connected_non_tx):
        if api not in ext_api_list:
            ext_api_list.append(api)
            if api not in label_map:
                label_map[api] = api
            style_by_api.setdefault(api, "light")

    # マスタ系内部リレーション
    mst_api = {o["api_name"] for o in mst_objs}
    mst_relations = [r for r in relations
                     if r["parent"] in mst_api and r["child"] in mst_api]

    std_ext = [api for api in ext_api_list if api in STD_PRIORITY]
    mst_ext = [api for api in ext_api_list if api in MST_PRIORITY]

    # TX外部参照スライドは内容量に応じて分割
    ext_slides_meta = []  # (section_title, slide_title, std_list, mst_list)
    if std_ext and mst_ext:
        ext_slides_meta = [
            ("TX ER図（2/3）標準オブジェクト参照", "TX ER図（2/3）標準オブジェクト参照", std_ext, []),
            ("TX ER図（3/3）マスタ系オブジェクト参照", "TX ER図（3/3）マスタ系オブジェクト参照", [], mst_ext),
        ]
        toc_ext = [
            {"label": "4. TX ER図（2/3）標準オブジェクト参照", "target": "TX ER図（2/3）標準オブジェクト参照"},
            {"label": "5. TX ER図（3/3）マスタ系オブジェクト参照", "target": "TX ER図（3/3）マスタ系オブジェクト参照"},
        ]
        mst_no = 6; sup_no = 7; rel_no = 8
    elif std_ext or mst_ext:
        ext_slides_meta = [
            ("TX ER図（2/2）外部参照", "TX ER図（2/2）外部参照オブジェクト", std_ext, mst_ext),
        ]
        toc_ext = [
            {"label": "4. TX ER図（2/2）外部参照", "target": "TX ER図（2/2）外部参照"},
        ]
        mst_no = 5; sup_no = 6; rel_no = 7
    else:
        toc_ext = []
        mst_no = 4; sup_no = 5; rel_no = 6

    toc_items = [
        {"label": "1. オブジェクト一覧",          "target": "オブジェクト一覧"},
        {"label": "2. ER図 凡例",                  "target": "ER図 凡例"},
        {"label": "3. TX ER図（1/X）コアフロー",  "target": "TX ER図（1/2）コアフロー"},
        *toc_ext,
        {"label": f"{mst_no}. マスタ系オブジェクト",  "target": "マスタ系オブジェクト"},
        {"label": f"{sup_no}. 補助・制御 / ログ系",   "target": "補助・制御 / ログ系オブジェクト"},
        {"label": f"{rel_no}. リレーション一覧",       "target": "リレーション一覧"},
    ]

    slides = [{"layout": "toc", "title": "目次", "items": toc_items}]

    slides.append(_build_object_list_table(categories, object_fields))

    # ER図 凡例スライド（ER図の前に配置）
    slides.append({"layout": "er_legend", "title": "ER図 凡例"})

    # TX ER図 1/X: コアフロー（固定グリッド・TX間リレーションのみ）
    if tx_api:
        slides.append(_build_tx_er_core(
            "TX ER図（1/2）コアフロー",
            label_map, object_fields, relations, style_by_api,
        ))

    # TX ER図 外部参照（内容量に応じて1〜2枚に分割、TX数が多ければさらにページ追加）
    for sec_title, slide_title, std_list, mst_list in ext_slides_meta:
        for er_slide in _build_tx_er_grouped_pages(
            slide_title, std_list, mst_list,
            label_map, object_fields, relations, style_by_api,
        ):
            slides.append(er_slide)

    if mst_objs:
        if mst_relations:
            slides.append(_build_er_slide(
                "マスタ系リレーション図",
                list(mst_api), cat_map, label_map, object_fields, mst_relations,
                style_by_api, box_w=2.8,
            ))
        slides.append(_build_master_table(mst_objs, object_fields, relations))

    if sup_objs:
        slides.append(_build_support_table(sup_objs, object_fields))

    slides.extend(_build_relation_table(relations, label_map))

    return {
        "title":    "データモデル定義書",
        "subtitle": "Salesforce オブジェクト構成・リレーション定義",
        "company":  company,
        "version":  "1.0",
        "date":     datetime.date.today().strftime("%Y年%m月"),
        "author":   author,
        "slides":   slides,
    }


# ── エントリポイント ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="データモデル定義書 PPTX 生成")
    ap.add_argument("--docs-dir",   required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--author",     default="")
    args = ap.parse_args()

    docs_dir   = Path(args.docs_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    catalog_dir = docs_dir / "catalog"
    index_path  = catalog_dir / "_index.md"
    model_path  = catalog_dir / "_data-model.md"

    if not index_path.exists() and not model_path.exists():
        print(f"ERROR: docs/catalog/ が見つかりません\n  {index_path}\n  {model_path}",
              file=sys.stderr)
        sys.exit(1)

    categories = parse_index(index_path)
    relations  = parse_relations(model_path)

    all_api_names = [obj["api_name"] for objs in categories.values() for obj in objs]
    label_map_tmp = {obj["api_name"]: obj["label"]
                     for objs in categories.values() for obj in objs}
    object_fields = load_all_object_fields(catalog_dir, all_api_names, label_map_tmp)

    company = ""
    profile_path = docs_dir / "overview" / "org-profile.md"
    if profile_path.exists():
        text = profile_path.read_text(encoding="utf-8")
        m = re.search(r'\|\s*会社名\s*\|\s*(.+?)\s*\|', text)
        if m:
            company = m.group(1).strip()

    data = build_json(categories, relations, object_fields, args.author, company)
    output_path = output_dir / "データモデル定義書.pptx"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_json = f.name

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate_pptx.py"),
             "--json-file", tmp_json, "--output", str(output_path)],
            capture_output=True,
        )
        if result.returncode != 0:
            print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
            sys.exit(1)
        print(f"完了: {output_path}")
    finally:
        os.unlink(tmp_json)


if __name__ == "__main__":
    main()
