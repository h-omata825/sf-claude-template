# scripts/python/sf-doc-mcp/generate_detail_design.py
# -*- coding: utf-8 -*-
"""
詳細設計書.xlsx を1機能分生成する（テンプレート読込方式・新JSONスキーマ対応）。

  詳細設計書テンプレート.xlsx（build_detail_design_template.py で生成した「器」）を
  コピーしてセル値 + 図形PNGを流し込む。

7シート構成:
  1. 改版履歴           : メタ + 履歴テーブル
  2. 概要               : 機能名 / 機能概要 / 目的 / 利用者 / 起点画面 / 操作トリガー
  3. 業務フロー         : スイムレーン図PNG + フロー表(No/アクター/処理内容/分岐条件)
  4. 対象オブジェクト   : ER図PNG + 項目表(オブジェクト名/項目API名/項目ラベル/読み書き区分/備考)
  5. 処理概要           : フローチャートPNG + 処理表(ステップNo/処理内容/条件分岐/SOQL概要/DML操作)
  6. 関連コンポーネント : コンポーネント図PNG + 一覧表(コンポーネント名/種別/役割/依存方向)
  7. 影響範囲           : 5セクション(更新/参照オブジェクト、関連Apex等、外部連携、他機能依存)

Usage:
  python generate_detail_design.py \\
    --input  detail_design.json \\
    --template "C:/.../詳細設計書テンプレート.xlsx" \\
    --output-dir "C:/.../出力先" \\
    [--version-increment minor]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import date as _date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

import design_revision as dr
from meta_store import read_meta, write_meta
from version_manager import increment_version

# ── 色定数 ─────────────────────────────────────────────────────────
C_HDR_BLUE  = "2E75B6"
C_BAND_BLUE = "0070C0"
C_LABEL_BG  = "D9E1F2"
C_FONT_D    = "000000"
C_FONT_W    = "FFFFFF"

THIN = Side(style="thin", color="8B9DC3")

# ── テンプレート行番号定数 ─────────────────────────────────────────
# build_detail_design_template.py の構造から算出
# 改版履歴
REV_META_ROW       = 3
REV_META_PROJECT_V = (6, 18)
REV_META_DATE_V    = (23, 31)
REV_DATA_ROW_START = 6
REV_COLS = {
    "項番":     (2,  3),
    "版数":     (4,  5),
    "変更箇所": (6,  11),
    "変更内容": (12, 17),
    "変更理由": (18, 23),
    "変更日":   (24, 26),
    "変更者":   (27, 29),
    "備考":     (30, 31),
}

# 概要（row3〜row8: 機能名/機能概要/目的/利用者/起点画面/操作トリガー）
OV_LABEL_VAL_CS = 7
OV_LABEL_VAL_CE = 31
OV_ROWS = {
    "name_ja":        3,
    "summary":        4,
    "purpose":        5,
    "users":          6,
    "trigger_screen": 7,
    "trigger":        8,
}

# 業務フロー: 表上・図下レイアウト
# テーブル: row3=バンド, row4=ヘッダ, row5〜24=データ(20行)
# 図エリア: row26=バンド, row27〜56=図エリア(30行)
BF_IMG_ANCHOR      = "B27"
BF_DATA_ROW_START  = 5
BF_STEP_CS,  BF_STEP_CE  = 2,  3
BF_ACTOR_CS, BF_ACTOR_CE = 4,  8
BF_ACT_CS,   BF_ACT_CE   = 9,  22
BF_COND_CS,  BF_COND_CE  = 23, 31

# 対象オブジェクト: 表上・図下レイアウト
# テーブル: row3=バンド, row4=ヘッダ, row5〜34=データ(30行)
# 図エリア: row36=バンド, row37〜66=図エリア(30行)
OBJ_IMG_ANCHOR     = "B37"
OBJ_DATA_ROW_START = 5
OBJ_NAME_CS,  OBJ_NAME_CE  = 2,  7
OBJ_FAPI_CS,  OBJ_FAPI_CE  = 8,  14
OBJ_FLBL_CS,  OBJ_FLBL_CE  = 15, 20
OBJ_ACC_CS,   OBJ_ACC_CE   = 21, 23
OBJ_NOTE_CS,  OBJ_NOTE_CE  = 24, 31

# 処理概要: 表上・図下レイアウト
# テーブル: row3=バンド, row4=ヘッダ, row5〜24=データ(20行)
# 図エリア: row26=バンド, row27〜56=図エリア(30行)
PROC_IMG_ANCHOR     = "B27"
PROC_DATA_ROW_START = 5
PROC_STEP_CS, PROC_STEP_CE = 2,  3
PROC_DESC_CS, PROC_DESC_CE = 4,  13
PROC_COND_CS, PROC_COND_CE = 14, 19
PROC_SOQL_CS, PROC_SOQL_CE = 20, 25
PROC_DML_CS,  PROC_DML_CE  = 26, 31

# 関連コンポーネント: 表上・図下レイアウト
# テーブル: row3=バンド, row4=ヘッダ, row5〜19=データ(15行)
# 図エリア: row21=バンド, row22〜51=図エリア(30行)
COMP_IMG_ANCHOR     = "B22"
COMP_DATA_ROW_START = 5
COMP_NAME_CS, COMP_NAME_CE = 2,  9
COMP_TYPE_CS, COMP_TYPE_CE = 10, 13
COMP_ROLE_CS, COMP_ROLE_CE = 14, 24
COMP_DEP_CS,  COMP_DEP_CE  = 25, 31

# 影響範囲: row3 から積み上がる
# 更新オブジェクト: row3=バンド, row4=ヘッダ, row5-12=データ(8行), row13=spacer
# 参照オブジェクト: row14=バンド, row15=ヘッダ, row16-23=データ(8行), row24=spacer
# 関連Apex/Flow/LWC: row25=バンド, row26=ヘッダ, row27-34=データ(8行), row35=spacer
# 外部連携影響: row36=バンド, row37=ヘッダ, row38-42=データ(5行), row43=spacer
# 他機能依存: row44=バンド, row45=ヘッダ, row46-50=データ(5行), row51=spacer
IMPACT_UPDATE_OBJ_START = 5
IMPACT_REF_OBJ_START    = 16
IMPACT_APEX_START       = 27
IMPACT_EXT_START        = 38
IMPACT_DEP_START        = 46

GRID_RIGHT = 31

SCALAR_FIELDS  = ["summary", "purpose", "users", "trigger_screen", "trigger"]
SECTION_SHEETS = {
    "business_flow":    "業務フロー",
    "related_objects":  "対象オブジェクト",
    "process_steps":    "処理概要",
    "components":       "関連コンポーネント",
}


# ── スタイルヘルパー ────────────────────────────────────────────────
def _fill(c): return PatternFill("solid", fgColor=c)
def _fnt(bold=False, color=C_FONT_D, size=10):
    return Font(name="游ゴシック", bold=bold, color=color, size=size)
def _aln(h="left", v="center", wrap=True):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def B_all():
    return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def W(ws, row, col, value="", bold=False, fg=C_FONT_D, bg=None,
      h="left", v="center", wrap=True, border=None, size=10):
    c = ws.cell(row=row, column=col, value=value)
    c.font = _fnt(bold=bold, color=fg, size=size)
    c.alignment = _aln(h=h, v=v, wrap=wrap)
    if bg: c.fill = _fill(bg)
    if border: c.border = border
    return c

def MW(ws, row, cs, ce, value="", border=None, bg=None, **kwargs):
    if border:
        for c in range(cs, ce + 1):
            ws.cell(row=row, column=c).border = border
    if bg:
        for c in range(cs, ce + 1):
            ws.cell(row=row, column=c).fill = _fill(bg)
    ws.merge_cells(start_row=row, start_column=cs, end_row=row, end_column=ce)
    return W(ws, row, cs, value, border=border, bg=bg, **kwargs)

def set_h(ws, row, h):
    ws.row_dimensions[row].height = h


# ── PNG埋め込み ────────────────────────────────────────────────────
def _embed_image(ws, png_path: str, anchor: str,
                 img_w: int = 840, img_h: int | None = None):
    """PNGをExcelシートに埋め込む。img_h=Noneなら縦横比維持。"""
    try:
        if not Path(png_path).exists():
            return
        img = XLImage(png_path)
        img.anchor = anchor
        if img_h is None:
            ratio = img.height / img.width if img.width else 1.0
            img.width = img_w
            img.height = int(img_w * ratio)
        else:
            img.width = img_w
            img.height = img_h
        ws.add_image(img)
    except Exception as e:
        print(f"  [WARN] 画像埋め込み失敗({anchor}): {e}")


# ── シート埋め込み ─────────────────────────────────────────────────
def fill_revision(ws, data: dict, history: list[dict]):
    vs, _ = REV_META_PROJECT_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("project_name", ""))
    vs, _ = REV_META_DATE_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("date", ""))
    dr.fill_revision_table(ws, history, REV_COLS, REV_DATA_ROW_START)


def fill_overview(ws, data: dict, changed_fields: set):
    """概要シートに値を書き込む。"""
    for key, row in OV_ROWS.items():
        val = data.get(key, "")
        if val:
            cell = ws.cell(row=row, column=OV_LABEL_VAL_CS, value=val)
            if key in changed_fields:
                dr.apply_red(cell, size=10)


def fill_business_flow(ws, data: dict, changed_step_nos: set,
                       png_path: str | None):
    """業務フローシート: スイムレーン図 + テーブル。"""
    if png_path:
        _embed_image(ws, png_path, BF_IMG_ANCHOR, img_w=880)

    flows = data.get("business_flow", [])
    r = BF_DATA_ROW_START
    for i, flow in enumerate(flows):
        step_no = flow.get("step", i + 1)
        is_changed = step_no in changed_step_nos
        set_h(ws, r, 24)

        # 分岐条件テキスト: nextのconditionを集約
        nexts = flow.get("next", [])
        conditions = [n.get("condition", "") for n in nexts if n.get("condition")]
        cond_text = " / ".join(conditions)

        c1 = MW(ws, r, BF_STEP_CS,  BF_STEP_CE,  step_no,
                border=B_all(), h="center")
        c2 = MW(ws, r, BF_ACTOR_CS, BF_ACTOR_CE, flow.get("actor", ""),
                border=B_all(), h="center")
        c3 = MW(ws, r, BF_ACT_CS,   BF_ACT_CE,   flow.get("action", ""),
                border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, BF_COND_CS,  BF_COND_CE,  cond_text,
                border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4):
                dr.apply_red(c)
        r += 1


def fill_target_objects(ws, data: dict, changed_obj_keys: set,
                        png_path: str | None):
    """対象オブジェクトシート: ER図 + 項目テーブル。"""
    if png_path:
        _embed_image(ws, png_path, OBJ_IMG_ANCHOR, img_w=880)

    objects = data.get("related_objects", [])
    r = OBJ_DATA_ROW_START
    for obj in objects:
        obj_name = f"{obj.get('label', '')} ({obj.get('api_name', '')})"
        is_changed = obj.get("api_name", "") in changed_obj_keys
        for field in obj.get("fields", []):
            set_h(ws, r, 22)
            c1 = MW(ws, r, OBJ_NAME_CS,  OBJ_NAME_CE,  obj_name,
                    border=B_all())
            c2 = MW(ws, r, OBJ_FAPI_CS,  OBJ_FAPI_CE,  field.get("api_name", ""),
                    border=B_all())
            c3 = MW(ws, r, OBJ_FLBL_CS,  OBJ_FLBL_CE,  field.get("label", ""),
                    border=B_all())
            c4 = MW(ws, r, OBJ_ACC_CS,   OBJ_ACC_CE,   field.get("access", ""),
                    border=B_all(), h="center")
            c5 = MW(ws, r, OBJ_NOTE_CS,  OBJ_NOTE_CE,  field.get("note", ""),
                    border=B_all(), wrap=True)
            if is_changed:
                for c in (c1, c2, c3, c4, c5):
                    dr.apply_red(c)
            r += 1


def fill_process_overview(ws, data: dict, changed_step_nos: set,
                          png_path: str | None):
    """処理概要シート: フローチャート + テーブル。"""
    if png_path:
        _embed_image(ws, png_path, PROC_IMG_ANCHOR, img_w=880)

    steps = data.get("process_steps", [])
    r = PROC_DATA_ROW_START
    for i, ps in enumerate(steps):
        step_no = ps.get("step", i + 1)
        is_changed = step_no in changed_step_nos
        set_h(ws, r, 30)

        desc_text = f"{ps.get('title', '')}\n{ps.get('description', '')}".strip()
        branch = ps.get("branch") or ""

        c1 = MW(ws, r, PROC_STEP_CS, PROC_STEP_CE, step_no,
                border=B_all(), h="center")
        c2 = MW(ws, r, PROC_DESC_CS, PROC_DESC_CE, desc_text,
                border=B_all(), wrap=True, v="top")
        c3 = MW(ws, r, PROC_COND_CS, PROC_COND_CE, branch,
                border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, PROC_SOQL_CS, PROC_SOQL_CE, ps.get("soql") or "",
                border=B_all(), wrap=True, v="top")
        c5 = MW(ws, r, PROC_DML_CS,  PROC_DML_CE,  ps.get("dml") or "",
                border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4, c5):
                dr.apply_red(c)
        r += 1


def fill_related_components(ws, data: dict, changed_comp_keys: set,
                            png_path: str | None):
    """関連コンポーネントシート: コンポーネント図 + 一覧テーブル。"""
    if png_path:
        _embed_image(ws, png_path, COMP_IMG_ANCHOR, img_w=880)

    components = data.get("components", [])
    r = COMP_DATA_ROW_START
    for comp in components:
        api_name = comp.get("api_name", "")
        is_changed = api_name in changed_comp_keys
        set_h(ws, r, 24)

        # 依存方向: callees のリストを文字列化
        callees = comp.get("callees", [])
        dep_text = " → ".join(callees) if callees else ""

        c1 = MW(ws, r, COMP_NAME_CS, COMP_NAME_CE, api_name,
                border=B_all())
        c2 = MW(ws, r, COMP_TYPE_CS, COMP_TYPE_CE, comp.get("type", ""),
                border=B_all(), h="center")
        c3 = MW(ws, r, COMP_ROLE_CS, COMP_ROLE_CE, comp.get("role", ""),
                border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, COMP_DEP_CS,  COMP_DEP_CE,  dep_text,
                border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4):
                dr.apply_red(c)
        r += 1


def fill_impact_scope(ws, data: dict):
    """影響範囲シート: 5セクションに値を書き込む。"""
    impact = data.get("impact", {})

    def _fill_simple_list(items: list, start_row: int, name_cs: int, name_ce: int):
        """1列だけのシンプルなリスト書き込み。"""
        r = start_row
        for item in items:
            set_h(ws, r, 22)
            MW(ws, r, name_cs, name_ce, item, border=B_all())
            r += 1

    # 更新オブジェクト: col 2-9=名前, 10-20=更新項目, 21-31=更新条件
    r = IMPACT_UPDATE_OBJ_START
    for obj_name in impact.get("update_objects", []):
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  obj_name, border=B_all())
        MW(ws, r, 10, 20, "",       border=B_all())
        MW(ws, r, 21, 31, "",       border=B_all())
        r += 1

    # 参照オブジェクト: col 2-9=名前, 10-20=参照項目, 21-31=参照目的
    r = IMPACT_REF_OBJ_START
    for obj_name in impact.get("reference_objects", []):
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  obj_name, border=B_all())
        MW(ws, r, 10, 20, "",       border=B_all())
        MW(ws, r, 21, 31, "",       border=B_all())
        r += 1

    # 関連Apex/Flow/LWC: col 2-9=名称, 10-13=種別, 14-31=関連内容
    r = IMPACT_APEX_START
    apex_items = impact.get("related_apex", [])
    flow_items = impact.get("related_flow", [])
    lwc_items  = impact.get("related_lwc", [])
    for name in apex_items:
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  name,   border=B_all())
        MW(ws, r, 10, 13, "Apex", border=B_all(), h="center")
        MW(ws, r, 14, 31, "",     border=B_all())
        r += 1
    for name in flow_items:
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  name,   border=B_all())
        MW(ws, r, 10, 13, "Flow", border=B_all(), h="center")
        MW(ws, r, 14, 31, "",     border=B_all())
        r += 1
    for name in lwc_items:
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  name,  border=B_all())
        MW(ws, r, 10, 13, "LWC", border=B_all(), h="center")
        MW(ws, r, 14, 31, "",    border=B_all())
        r += 1

    # 外部連携影響: col 2-9=連携先, 10-31=影響内容
    r = IMPACT_EXT_START
    for name in impact.get("external_integrations", []):
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  name, border=B_all())
        MW(ws, r, 10, 31, "",   border=B_all())
        r += 1

    # 他機能依存: col 2-9=機能名, 10-31=依存内容
    r = IMPACT_DEP_START
    for name in impact.get("feature_dependencies", []):
        set_h(ws, r, 22)
        MW(ws, r, 2,  9,  name, border=B_all())
        MW(ws, r, 10, 31, "",   border=B_all())
        r += 1


# ── 差分計算 ────────────────────────────────────────────────────────
def _compute_diffs(prev_data: dict | None, new_data: dict) -> dict:
    if prev_data is None:
        return {"scalars": [], "lists": {}}
    return {
        "scalars": dr.diff_scalars(prev_data, new_data, SCALAR_FIELDS),
        "lists": {
            "business_flow": dr.diff_list(
                prev_data.get("business_flow", []),
                new_data.get("business_flow", []), "step"),
            "related_objects": dr.diff_list(
                prev_data.get("related_objects", []),
                new_data.get("related_objects", []), "api_name"),
            "process_steps": dr.diff_list(
                prev_data.get("process_steps", []),
                new_data.get("process_steps", []), "step"),
            "components": dr.diff_list(
                prev_data.get("components", []),
                new_data.get("components", []), "api_name"),
        },
    }


# ── PNG生成 ────────────────────────────────────────────────────────
def _generate_diagrams(data: dict, tmp_dir: str) -> dict[str, str | None]:
    """4種の図形PNGを生成し、パスを返す。失敗したらNone。"""
    import diagram_gen as dg

    paths: dict[str, str | None] = {
        "swimlane":  None,
        "er":        None,
        "flowchart": None,
        "component": None,
    }

    # 1. スイムレーン図（業務フロー）
    flows = data.get("business_flow", [])
    if flows:
        try:
            sl_path = str(Path(tmp_dir) / "swimlane.png")
            dg.render_swimlane(_business_flow_to_swimlane(flows), sl_path)
            paths["swimlane"] = sl_path
            print("  [OK] スイムレーン図")
        except Exception as e:
            print(f"  [WARN] スイムレーン図: {e}")

    # 2. ER図（対象オブジェクト）
    objects = data.get("related_objects", [])
    if objects:
        try:
            er_path = str(Path(tmp_dir) / "er.png")
            obj_list, rels = _related_objects_to_er(objects)
            dg.render_er_diagram(obj_list, rels, er_path)
            paths["er"] = er_path
            print("  [OK] ER図")
        except Exception as e:
            print(f"  [WARN] ER図: {e}")

    # 3. フローチャート（処理概要）
    steps = data.get("process_steps", [])
    if steps:
        try:
            fc_path = str(Path(tmp_dir) / "flowchart.png")
            dg.render_flowchart(steps, fc_path)
            paths["flowchart"] = fc_path
            print("  [OK] フローチャート")
        except Exception as e:
            print(f"  [WARN] フローチャート: {e}")

    # 4. コンポーネント図（関連コンポーネント）
    components = data.get("components", [])
    if components:
        try:
            cm_path = str(Path(tmp_dir) / "component.png")
            dg.render_component_diagram(components, cm_path)
            paths["component"] = cm_path
            print("  [OK] コンポーネント図")
        except Exception as e:
            print(f"  [WARN] コンポーネント図: {e}")

    return paths


def _business_flow_to_swimlane(flows: list[dict]) -> dict:
    """business_flow リストを render_swimlane 用のフロー dict に変換する。"""
    lane_names = list(dict.fromkeys(f.get("actor", "不明") for f in flows))
    steps = [
        {"id": str(f.get("step", i + 1)), "lane": f.get("actor", "不明"),
         "label": f.get("action", "")}
        for i, f in enumerate(flows)
    ]
    transitions = []
    for i, f in enumerate(flows):
        nexts = f.get("next", [])
        src = str(f.get("step", i + 1))
        if nexts:
            for n in nexts:
                dst_step = n.get("step") or (flows[i + 1].get("step", i + 2) if i + 1 < len(flows) else None)
                if dst_step:
                    transitions.append({"from": src, "to": str(dst_step),
                                        "condition": n.get("condition", "")})
        elif i + 1 < len(flows):
            transitions.append({"from": src, "to": str(flows[i + 1].get("step", i + 2))})
    return {
        "title": "業務フロー",
        "lanes": [{"name": n} for n in lane_names],
        "steps": steps,
        "transitions": transitions,
    }


def _related_objects_to_er(objects: list[dict]) -> tuple[list, list]:
    """related_objects を render_er_diagram 用の (objects, relations) に変換する。"""
    obj_list = [
        {"api": o.get("api_name", ""), "label": o.get("label", ""),
         "type": "カスタム" if "__c" in o.get("api_name", "") else "標準"}
        for o in objects
    ]
    rels = []
    for o in objects:
        for r in o.get("relations", []):
            rels.append({
                "parent": o.get("api_name", ""),
                "rel":    r.get("type", "lookup"),
                "child":  r.get("to", ""),
                "field":  r.get("field", ""),
            })
    return obj_list, rels




# ── メイン ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="詳細設計書 Excel 生成（新スキーマ対応）")
    parser.add_argument("--input",      required=True, help="詳細設計 JSON ファイルパス")
    parser.add_argument("--template",   required=True, help="詳細設計書テンプレート.xlsx パス")
    parser.add_argument("--output-dir", required=True, help="出力先ディレクトリ")
    parser.add_argument("--version-increment", default="minor",
                        choices=["minor", "major"])
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    today  = _date.today().strftime("%Y-%m-%d")
    author = data.get("author", "")

    feature_id = data.get("feature_id", "")
    name_ja    = data.get("name_ja", "機能")
    safe_name  = re.sub(r'[\\/:*?"<>|]', "_", name_ja)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_name}_詳細設計.xlsx"

    # ── バージョン判定 ────────────────────────────────────────────
    source_file = ""
    existing = sorted(out_dir.glob(f"*{safe_name}*詳細設計*.xlsx"),
                      key=lambda f: f.stat().st_mtime, reverse=True)
    if existing:
        source_file = str(existing[0])
        print(f"  [AUTO] 既存ファイルを検出: {existing[0].name}")

    prev_meta   = read_meta(source_file) if source_file else None
    prev_data   = prev_meta.get("data") if prev_meta else None

    if prev_meta:
        current_version = increment_version(
            prev_meta.get("version", "1.0"), args.version_increment)
        history    = prev_meta.get("history", [])
        is_initial = False
        print(f"更新モード: {prev_meta.get('version', '?')} -> {current_version}")
    else:
        current_version = data.get("version") or "1.0"
        history    = []
        is_initial = True
        print(f"新規作成モード: v{current_version}")

    data["version"] = current_version
    if not data.get("date"):
        data["date"] = today

    diffs = _compute_diffs(prev_data, data)
    if prev_meta and args.version_increment == "minor" and not dr.has_any_diff(diffs):
        print("差分なし: 既存ファイルと一致しているため更新をスキップしました")
        sys.exit(0)

    last_no = max((h["項番"] for h in history
                   if isinstance(h.get("項番"), int)), default=0)
    new_entries = dr.build_entries(
        current_version, diffs, author, today,
        start_no=last_no + 1,
        is_major=(args.version_increment == "major"),
        is_initial=is_initial,
        section_sheet_map=SECTION_SHEETS,
        scalar_sheet="概要",
    )
    history = history + new_entries

    changed_scalars    = dr.changed_scalar_fields(diffs)
    changed_flows      = dr.changed_ids(diffs, "business_flow")
    changed_objs       = dr.changed_ids(diffs, "related_objects")
    changed_proc_steps = dr.changed_ids(diffs, "process_steps")
    changed_comps      = dr.changed_ids(diffs, "components")
    is_major           = (args.version_increment == "major")

    # ── 図形PNG生成 ──────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp_dir:
        png_paths = _generate_diagrams(data, tmp_dir)

        # ── テンプレ読込 -> セル流し込み ──────────────────────────
        wb = load_workbook(args.template)

        fill_revision(wb["改版履歴"], data, history)

        fill_overview(
            wb["概要"], data,
            changed_fields=set() if is_major else changed_scalars)

        fill_business_flow(
            wb["業務フロー"], data,
            changed_step_nos=set() if is_major else changed_flows,
            png_path=png_paths.get("swimlane"))

        fill_target_objects(
            wb["対象オブジェクト"], data,
            changed_obj_keys=set() if is_major else changed_objs,
            png_path=png_paths.get("er"))

        fill_process_overview(
            wb["処理概要"], data,
            changed_step_nos=set() if is_major else changed_proc_steps,
            png_path=png_paths.get("flowchart"))

        fill_related_components(
            wb["関連コンポーネント"], data,
            changed_comp_keys=set() if is_major else changed_comps,
            png_path=png_paths.get("component"))

        fill_impact_scope(wb["影響範囲"], data)

        meta_payload = {
            "version": current_version,
            "date":    today,
            "author":  author,
            "data":    data,
            "history": history,
        }
        write_meta(wb, meta_payload)

        wb.save(str(out_path))

    sys.stdout.buffer.write(
        f"[OK] 詳細設計書を生成しました: v{current_version} -> {out_path}\n".encode("utf-8"))

    # 同名パターンの旧ファイルを削除
    for old_f in out_dir.glob(f"*{safe_name}*詳細設計*.xlsx"):
        if old_f.resolve() != out_path.resolve():
            old_f.unlink()
            sys.stdout.buffer.write(
                f"  [CLEANUP] 旧ファイルを削除: {old_f.name}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
