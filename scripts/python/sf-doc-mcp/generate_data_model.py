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
}

# カテゴリ分類ルール（キーワード → バケット）
# _index.md の見出し文字列にキーワードが含まれていれば、対応する分類を適用する。
# これにより、プロジェクトごとに異なるカテゴリ見出しでも自動で正しく分類される。
_CATEGORY_RULES = [
    # (正規表現, 分類 tx/mst/std/sup, スタイルキー)
    (r"(トランザクション|Transaction|取引|業務)", "tx",  "primary"),
    (r"(マスタ|マスター|Master)",                 "mst", "accent"),
    (r"(標準|Standard)",                          "std", "secondary"),
    (r"(補助|制御|ログ|Support|Log|Helper)",      "sup", "light"),
]


def classify_category(cat_name: str) -> tuple:
    """カテゴリ名 → (bucket, style)。該当なしは (sup, light)。"""
    for pat, bucket, style in _CATEGORY_RULES:
        if re.search(pat, cat_name, re.IGNORECASE):
            return bucket, style
    return "sup", "light"

HDR_H      = 0.52
FIELD_H    = 0.215
MIN_BODY_H = 0.18
MAX_FIELDS = 5


# ── パース: _index.md ──────────────────────────────────────────────────────────

def parse_index(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    categories = {}
    current_h3 = None
    for line in text.splitlines():
        if re.match(r'^##\s+', line):
            current_h3 = None
            continue
        m3 = re.match(r'^###\s+(.+)', line)
        if m3:
            current_h3 = m3.group(1).strip()
            categories.setdefault(current_h3, [])
            continue
        if not current_h3 or not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        label, api_name = cols[0], cols[1]
        if (not label or label.startswith("---") or label == "オブジェクト"
                or api_name.startswith("---")
                or re.match(r'\[.+\]\(.+\)', api_name)):
            continue
        categories[current_h3].append({"label": label, "api_name": api_name})
    return categories


# ── パース: _data-model.md ────────────────────────────────────────────────────

def parse_relations(path: Path) -> list:
    """リレーション一覧テーブル + Mermaid erDiagram からリレーションを返す。
    各リレーションに fk_field（FKフィールドAPI名）を付与する。
    Returns: [{parent, child, label, type, fk_field}]
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")

    # 主従テーブルから親子ペア取得
    md_pairs = set()
    for m in re.finditer(r'\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*\*\*主従', text):
        md_pairs.add((m.group(1), m.group(2)))

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
        # ヘッダー・セパレーターをスキップ
        if not re.match(r'\w', parent_raw) or parent_raw == "親オブジェクト":
            continue
        # **主従...** のマークダウンを除去
        parent = re.sub(r'\*+', '', parent_raw).strip()
        child  = re.sub(r'\*+', '', child_raw).strip()
        fk     = re.sub(r'\*+', '', fk_field).strip()
        # FKフィールドが複数ある場合は最初だけ（括弧内の説明を除く）
        fk = re.split(r'[（(、,]', fk)[0].strip()
        if parent and child and fk and re.match(r'\w', fk):
            fk_map[(parent, child)] = fk

    # Mermaid erDiagram をパース
    mermaid_m = re.search(r'```mermaid\nerDiagram\n(.*?)```', text, re.DOTALL)
    if not mermaid_m:
        return []

    relations = []
    seen = set()
    for line in mermaid_m.group(1).splitlines():
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
        fk_field = fk_map.get(key, fk_map.get((raw_parent, raw_child), ""))
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
    block_m = re.search(r'\w+\s*\{([^}]+)\}', mermaid_m.group(1), re.DOTALL)
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
    """## 主要カスタム項目 テーブルからフィールドを抽出（標準オブジェクト用）"""
    fields = []
    # セクションを見つける
    section_m = re.search(r'##\s+主要カスタム項目\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    if not section_m:
        return fields
    for line in section_m.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 3:
            continue
        label, api_name, dtype = cols[0], cols[1], cols[2]
        if not api_name or api_name.startswith("---") or api_name == "API名":
            continue
        if api_name in _SKIP_FIELDS:
            continue
        # マークダウン装飾を除去
        label = re.sub(r'\*+', '', label).strip()
        dtype_clean = dtype.split("(")[0].strip().lower()
        is_fk = dtype_clean in ("reference",)
        fields.append({"api_name": api_name, "type": dtype_clean, "label": label, "is_fk": is_fk})
    return fields


def parse_object_fields(md_path: Path) -> dict:
    """個別オブジェクト MD から説明・キー項目リストを返す。"""
    if not md_path.exists():
        return {"description": "", "fields": []}
    text = md_path.read_text(encoding="utf-8")
    desc = ""
    m = re.search(r'\|\s*説明\s*\|\s*(.+?)\s*\|', text)
    if m:
        desc = m.group(1).strip()

    # カスタムオブジェクト: Mermaid ブロック優先
    fields = _parse_fields_from_mermaid(text)
    # 標準/Mermaidなし: 主要カスタム項目テーブルから
    if not fields:
        fields = _parse_fields_from_table(text)
    # それでもない場合: リレーション表から FK のみ
    if not fields:
        for m2 in re.finditer(r'\|\s*([^|]+?)\s*\|\s*参照（親）\s*\|\s*(\w+)\s*\|', text):
            api = m2.group(2).strip()
            if api not in _SKIP_FIELDS:
                fields.append({"api_name": api, "type": "reference",
                                "label": m2.group(1).strip(), "is_fk": True})

    fk_fields    = [f for f in fields if f["is_fk"]]
    other_fields = [f for f in fields if not f["is_fk"] and f["type"] not in ("string", "textarea")]
    selected = (fk_fields + other_fields)[:MAX_FIELDS]
    return {"description": desc, "fields": selected}


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
                         x0, y0, x1, y1, box_w=2.2):
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
    actual_box_w = min(box_w, col_step - 0.25, 2.4)

    positions = {}
    for l in sorted(by_layer.keys()):
        nodes_in_layer = by_layer[l]
        col_cx = x0 + l * col_step + col_step / 2
        heights = [box_heights.get(n, HDR_H + MIN_BODY_H) for n in nodes_in_layer]
        total_h = sum(heights) + ROW_GAP * (len(nodes_in_layer) - 1)
        start_y = max((y0 + y1) / 2 - total_h / 2, y0)
        cur_y = start_y
        for i, nid in enumerate(nodes_in_layer):
            h = heights[i]
            x = col_cx - actual_box_w / 2
            y = min(cur_y, y1 - h)
            positions[nid] = (x, y, actual_box_w, h)
            cur_y += h + ROW_GAP

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
            desc = object_fields.get(api, {}).get("description", "")[:50] or "—"
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
                    object_fields, relations, style_by_api, box_w=2.2):
    box_heights = {
        nid: compute_box_h(len(object_fields.get(nid, {}).get("fields", [])))
        for nid in node_ids
    }
    positions = layout_hierarchical(
        node_ids, relations, box_heights,
        x0=0.3, y0=1.3, x1=13.0, y1=7.1, box_w=box_w,
    )
    boxes = []
    for nid, (x, y, w, h) in positions.items():
        label = label_map.get(nid, nid)
        oinfo = object_fields.get(nid, {"fields": []})
        boxes.append({
            "id": nid, "label": label, "api_name": nid,
            "fields": oinfo.get("fields", []),
            "x": x, "y": y, "w": w, "h": h,
            "style": style_by_api.get(nid, "light"),
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
        desc = object_fields.get(api, {}).get("description", "")[:50] or "—"
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

    cat_map = {}
    label_map = {}
    for cat, objs in categories.items():
        for obj in objs:
            cat_map[obj["api_name"]]   = cat
            label_map[obj["api_name"]] = obj["label"]

    # TX ER: TX + 直接接続する標準オブジェクト
    tx_api = {o["api_name"] for o in tx_objs}
    connected_std = set()
    for r in relations:
        if r["parent"] in tx_api and r["child"] not in tx_api:
            connected_std.add(r["child"])
        if r["child"] in tx_api and r["parent"] not in tx_api:
            connected_std.add(r["parent"])
    std_in_er = [o for o in std_objs if o["api_name"] in connected_std]
    tx_er_nodes = [o["api_name"] for o in std_in_er + tx_objs]

    # マスタ系内部リレーション
    mst_api = {o["api_name"] for o in mst_objs}
    mst_relations = [r for r in relations
                     if r["parent"] in mst_api and r["child"] in mst_api]

    toc_items = [
        {"label": "1. オブジェクト一覧",         "target": "オブジェクト一覧"},
        {"label": "2. トランザクション系ER図",   "target": "トランザクション系ER図"},
        {"label": "3. マスタ系オブジェクト",     "target": "マスタ系オブジェクト"},
        {"label": "4. 補助・制御 / ログ系",      "target": "補助・制御 / ログ系オブジェクト"},
        {"label": "5. リレーション一覧",         "target": "リレーション一覧"},
    ]

    slides = [{"layout": "toc", "title": "目次", "items": toc_items}]

    slides.append({"layout": "section", "title": "オブジェクト一覧"})
    slides.append(_build_object_list_table(categories, object_fields))

    slides.append({"layout": "section", "title": "トランザクション系ER図"})
    if tx_er_nodes:
        slides.append(_build_er_slide(
            "トランザクション系ER図",
            tx_er_nodes, cat_map, label_map, object_fields, relations,
            style_by_api, box_w=2.2,
        ))

    slides.append({"layout": "section", "title": "マスタ系オブジェクト"})
    if mst_objs:
        if mst_relations:
            slides.append(_build_er_slide(
                "マスタ系リレーション図",
                list(mst_api), cat_map, label_map, object_fields, mst_relations,
                style_by_api, box_w=2.4,
            ))
        slides.append(_build_master_table(mst_objs, object_fields, relations))

    slides.append({"layout": "section", "title": "補助・制御 / ログ系"})
    if sup_objs:
        slides.append(_build_support_table(sup_objs, object_fields))

    slides.append({"layout": "section", "title": "リレーション一覧"})
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
