# scripts/python/sf-doc-mcp/generate_detail_design.py
# -*- coding: utf-8 -*-
"""
詳細設計書.xlsx を1機能分生成する（テンプレート読込方式・新JSONスキーマ対応）。

  詳細設計書テンプレート.xlsx（build_detail_design_template.py で生成した「器」）を
  コピーしてセル値 + 図形PNGを流し込む。

6シート構成:
  1. 改版履歴           : メタ + 履歴テーブル
  2. 概要               : 機能名 / 機能概要 / 目的 / 利用者 / 起点画面 / 操作トリガー
  3. 業務フロー         : スイムレーン図PNG + フロー表(No/アクター/処理内容/分岐条件)
  4. 対象オブジェクト   : ER図PNG + 項目表(オブジェクト名/項目API名/項目ラベル/読み書き区分/備考)
  5. 処理概要           : フローチャートPNG + 処理表(No/処理内容/コンポーネント/分岐条件)
  6. 関連コンポーネント : コンポーネント図PNG + 一覧表(コンポーネント名/種別/役割/依存方向)

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
from openpyxl.utils import get_column_letter

import design_revision as dr
from build_detail_design_template import (
    section_band, diagram_area, data_rows, setup_grid, set_h,
    GRID_LEFT, GRID_RIGHT,
    C_BAND_BLUE, C_TITLE_DARK,
)
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

# 業務フロー: テーブルヘッダは row4、データは row5 から動的追加
BF_DATA_ROW_START  = 5
BF_STEP_CS,  BF_STEP_CE  = 2,  3
BF_ACTOR_CS, BF_ACTOR_CE = 4,  8
BF_ACT_CS,   BF_ACT_CE   = 9,  22
BF_COND_CS,  BF_COND_CE  = 23, 31
# BF_COL_GROUPS: データ行のマージセル定義
BF_COL_GROUPS = [
    (BF_STEP_CS, BF_STEP_CE),
    (BF_ACTOR_CS, BF_ACTOR_CE),
    (BF_ACT_CS, BF_ACT_CE),
    (BF_COND_CS, BF_COND_CE),
]

# 対象オブジェクト: 表上・図下レイアウト（動的行）
# ※ 項目ラベルが左（8-14）、API名が右（15-20）の順
OBJ_DATA_ROW_START = 5
OBJ_NAME_CS,  OBJ_NAME_CE  = 2,  7
OBJ_FLBL_CS,  OBJ_FLBL_CE  = 8,  14   # 項目ラベル（左）
OBJ_FAPI_CS,  OBJ_FAPI_CE  = 15, 20   # 項目API名（右）
OBJ_ACC_CS,   OBJ_ACC_CE   = 21, 23
OBJ_NOTE_CS,  OBJ_NOTE_CE  = 24, 31
OBJ_COL_GROUPS = [
    (OBJ_NAME_CS, OBJ_NAME_CE),
    (OBJ_FLBL_CS, OBJ_FLBL_CE),
    (OBJ_FAPI_CS, OBJ_FAPI_CE),
    (OBJ_ACC_CS,  OBJ_ACC_CE),
    (OBJ_NOTE_CS, OBJ_NOTE_CE),
]

# 処理概要: テーブルヘッダは row4、データは row5 から動的追加
PROC_DATA_ROW_START = 5
PROC_STEP_CS, PROC_STEP_CE = 2,  3
PROC_DESC_CS, PROC_DESC_CE = 4,  15
PROC_COMP_CS, PROC_COMP_CE = 16, 22
PROC_COND_CS, PROC_COND_CE = 23, 31
PROC_COL_GROUPS = [
    (PROC_STEP_CS, PROC_STEP_CE),
    (PROC_DESC_CS, PROC_DESC_CE),
    (PROC_COMP_CS, PROC_COMP_CE),
    (PROC_COND_CS, PROC_COND_CE),
]

# 関連コンポーネント: テーブルヘッダは row4、データは row5 から動的追加
COMP_DATA_ROW_START = 5
COMP_NAME_CS, COMP_NAME_CE = 2,  9
COMP_TYPE_CS, COMP_TYPE_CE = 10, 13
COMP_ROLE_CS, COMP_ROLE_CE = 14, 31  # 依存方向列廃止のため役割を31まで拡張
COMP_COL_GROUPS = [
    (COMP_NAME_CS, COMP_NAME_CE),
    (COMP_TYPE_CS, COMP_TYPE_CE),
    (COMP_ROLE_CS, COMP_ROLE_CE),
]

GRID_RIGHT_C = 31

SCALAR_FIELDS  = ["summary", "purpose", "users", "trigger_screen", "trigger"]
SECTION_SHEETS = {
    "business_flow":    "業務フロー",
    "process_steps":    "処理概要",
    "related_objects":  "対象オブジェクト",
    "components":       "関連コンポーネント",
}

# 動的シートの図エリア高さ（行数）
DIAGRAM_AREA_ROWS = 30
# 動的シートの空行追加数（手動入力用）— 0=データ行のみ
DYNAMIC_EMPTY_ROWS = 0


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

# set_h is imported from build_detail_design_template


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
    """業務フローシート: テーブル(動的行) + スイムレーン図。"""
    flows = data.get("business_flow", [])
    n_data = len(flows)
    total_rows = n_data + DYNAMIC_EMPTY_ROWS

    # データ行 + 空行の枠を作成
    r = BF_DATA_ROW_START
    data_rows(ws, r, r + total_rows - 1, BF_COL_GROUPS, row_h=24)

    # データ書き込み
    for i, flow in enumerate(flows):
        step_no = flow.get("step", i + 1)
        is_changed = step_no in changed_step_nos
        set_h(ws, r, 24)

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

    # スペーサー + 図エリア
    spacer_row = BF_DATA_ROW_START + total_rows
    set_h(ws, spacer_row, 8)
    diagram_start = spacer_row + 1
    diagram_area(ws, diagram_start, "業務フロー図（自動生成）", section_no=2)

    # 図埋め込み
    img_anchor = f"B{diagram_start + 1}"
    if png_path:
        _embed_image(ws, png_path, img_anchor, img_w=880)


def _compute_obj_note(obj_api: str, field_access: str, data: dict) -> str:
    """object_access + process_steps から項目ごとの備考テキストを生成する。

    フィールドの読み書き区分に応じて関連するアクセスのみ抽出する。
    例（読み取り専用項目）: 「プリチェック判定時に参照。」
    例（書き込み項目）: 「コンサルテーション依頼時に更新・登録。見積作成時に新規作成。」
    """
    _OP_JA = {"R": "参照", "W": "更新・登録", "RW": "参照・更新", "INSERT": "新規作成"}
    _WRITE_OPS = {"W", "RW", "INSERT"}
    _READ_OPS  = {"R", "RW"}

    object_access = data.get("object_access", [])
    process_steps = data.get("process_steps", [])

    comp_to_step: dict[str, str] = {}
    for ps in process_steps:
        comp = ps.get("component", "")
        if comp and comp not in comp_to_step:
            comp_to_step[comp] = ps.get("title", "")

    accesses = [a for a in object_access if a.get("object") == obj_api]
    if not accesses:
        if field_access in ("W", "RW", "INSERT"):
            return "更新・登録対象。"
        if field_access == "R":
            return "参照のみ。"
        return ""

    # フィールドの読み書き区分に応じて関連するアクセスのみ抽出
    relevant = [
        a for a in accesses
        if (field_access == "R" and a.get("operation", "") in _READ_OPS)
        or (field_access in ("W", "INSERT") and a.get("operation", "") in _WRITE_OPS)
        or field_access == "RW"
    ]
    if not relevant:
        relevant = accesses  # フォールバック

    parts = []
    for acc in relevant:
        op_ja = _OP_JA.get(acc.get("operation", ""), acc.get("operation", ""))
        step_title = comp_to_step.get(acc.get("component", ""), "")
        if step_title:
            parts.append(f"{step_title}時に{op_ja}")
        else:
            parts.append(op_ja)
    return "。".join(parts) + "。" if parts else ""


def fill_target_objects(ws, data: dict, changed_obj_keys: set,
                        png_path: str | None):
    """対象オブジェクトシート: 項目テーブル(動的行・縦結合) + 図。

    列順: オブジェクト名(縦結合) | 項目ラベル | 項目API名 | 読み書き区分(日本語) | 備考
    """
    _ACCESS_JA = {
        "R": "参照", "W": "更新", "RW": "参照・更新", "INSERT": "新規作成",
    }
    objects = data.get("related_objects", [])

    r = OBJ_DATA_ROW_START

    for obj in objects:
        obj_api   = obj.get("api_name", "")
        obj_label = f"{obj.get('label', '')} ({obj_api})"
        is_changed = obj_api in changed_obj_keys
        fields = obj.get("fields", [])
        if not fields:
            continue
        n_fields      = len(fields)
        obj_start_row = r

        for fi, field in enumerate(fields):
            set_h(ws, r, 22)
            access    = field.get("access", "")
            access_ja = _ACCESS_JA.get(access, access)
            note      = field.get("note", "")
            if not note:
                note = _compute_obj_note(obj_api, access, data)

            # オブジェクト名列: 全行書くが後で縦結合する
            MW(ws, r, OBJ_NAME_CS, OBJ_NAME_CE,
               obj_label if fi == 0 else "", border=B_all())

            c2 = MW(ws, r, OBJ_FLBL_CS, OBJ_FLBL_CE, field.get("label", ""),
                    border=B_all())
            c3 = MW(ws, r, OBJ_FAPI_CS, OBJ_FAPI_CE, field.get("api_name", ""),
                    border=B_all())
            c4 = MW(ws, r, OBJ_ACC_CS,  OBJ_ACC_CE,  access_ja,
                    border=B_all(), h="center")
            c5 = MW(ws, r, OBJ_NOTE_CS, OBJ_NOTE_CE, note,
                    border=B_all(), wrap=True, v="top")
            if is_changed:
                for c in (c2, c3, c4, c5):
                    dr.apply_red(c)
            r += 1

        # オブジェクト名列を縦結合（フィールドが複数ある場合）
        if n_fields > 1:
            # 個別行の横結合を解除してから縦結合
            for ri in range(obj_start_row, r):
                try:
                    ws.unmerge_cells(start_row=ri, start_column=OBJ_NAME_CS,
                                     end_row=ri, end_column=OBJ_NAME_CE)
                except Exception:
                    pass
            ws.merge_cells(start_row=obj_start_row, start_column=OBJ_NAME_CS,
                           end_row=r - 1, end_column=OBJ_NAME_CE)
            mc = ws.cell(row=obj_start_row, column=OBJ_NAME_CS)
            mc.value     = obj_label
            mc.font      = _fnt()
            mc.alignment = _aln(v="center", wrap=True)
            mc.border    = B_all()
            if is_changed:
                dr.apply_red(mc)

    # スペーサー + 図エリア（動的位置）
    spacer_row = r
    set_h(ws, spacer_row, 8)
    diagram_start = spacer_row + 1
    diagram_area(ws, diagram_start, "オブジェクト関連図（自動生成）", section_no=2)

    img_anchor = f"B{diagram_start + 1}"
    if png_path:
        _embed_image(ws, png_path, img_anchor, img_w=880)


def fill_process_overview(ws, data: dict, changed_step_nos: set,
                          png_path: str | None):
    """処理概要シート: テーブル(動的行) + フローチャート。"""
    steps = data.get("process_steps", [])
    n_data = len(steps)
    total_rows = n_data + DYNAMIC_EMPTY_ROWS

    # データ行 + 空行の枠を作成
    r = PROC_DATA_ROW_START
    data_rows(ws, r, r + total_rows - 1, PROC_COL_GROUPS, row_h=30)

    for i, ps in enumerate(steps):
        step_no = ps.get("step", i + 1)
        is_changed = step_no in changed_step_nos
        set_h(ws, r, 30)

        desc_text = f"{ps.get('title', '')}\n{ps.get('description', '')}".strip()
        component = ps.get("component") or ""
        branch = ps.get("branch") or ""

        c1 = MW(ws, r, PROC_STEP_CS, PROC_STEP_CE, step_no,
                border=B_all(), h="center")
        c2 = MW(ws, r, PROC_DESC_CS, PROC_DESC_CE, desc_text,
                border=B_all(), wrap=True, v="top")
        c3 = MW(ws, r, PROC_COMP_CS, PROC_COMP_CE, component,
                border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, PROC_COND_CS, PROC_COND_CE, branch,
                border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4):
                dr.apply_red(c)
        r += 1

    # スペーサー + 図エリア
    spacer_row = PROC_DATA_ROW_START + total_rows
    set_h(ws, spacer_row, 8)
    diagram_start = spacer_row + 1
    diagram_area(ws, diagram_start, "処理フロー図（自動生成）", section_no=2)

    img_anchor = f"B{diagram_start + 1}"
    if png_path:
        _embed_image(ws, png_path, img_anchor, img_w=880)


def fill_related_components(ws, data: dict, changed_comp_keys: set,
                            png_path: str | None):
    """関連コンポーネントシート: テーブル(動的行) + コンポーネント図。"""
    components = data.get("components", [])
    n_data = len(components)
    total_rows = n_data + DYNAMIC_EMPTY_ROWS

    r = COMP_DATA_ROW_START
    data_rows(ws, r, r + total_rows - 1, COMP_COL_GROUPS, row_h=24)

    for comp in components:
        api_name = comp.get("api_name", "")
        is_changed = api_name in changed_comp_keys
        set_h(ws, r, 24)

        c1 = MW(ws, r, COMP_NAME_CS, COMP_NAME_CE, api_name,
                border=B_all())
        c2 = MW(ws, r, COMP_TYPE_CS, COMP_TYPE_CE, comp.get("type", ""),
                border=B_all(), h="center")
        c3 = MW(ws, r, COMP_ROLE_CS, COMP_ROLE_CE, comp.get("role", ""),
                border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3):
                dr.apply_red(c)
        r += 1

    # スペーサー + 図エリア
    spacer_row = COMP_DATA_ROW_START + total_rows
    set_h(ws, spacer_row, 8)
    diagram_start = spacer_row + 1
    diagram_area(ws, diagram_start, "コンポーネント関連図（自動生成）", section_no=2)

    img_anchor = f"B{diagram_start + 1}"
    if png_path:
        _embed_image(ws, png_path, img_anchor, img_w=880)




# ── GFスキーマ正規化 ────────────────────────────────────────────────
import re as _re

# Salesforce 標準オブジェクトの日本語ラベルマップ
_STD_OBJ_LABELS = {
    "Lead": "リード", "Contact": "取引先責任者", "Account": "取引先",
    "Opportunity": "商談", "Case": "ケース", "Task": "ToDo", "Event": "行動",
    "User": "ユーザー", "ContentVersion": "コンテンツバージョン",
    "ContentDocument": "コンテンツドキュメント",
    "ContentDocumentLink": "コンテンツドキュメントリンク",
    "EmailMessage": "メール", "Attachment": "添付ファイル",
}

# 技術用語→日本語変換ルール（正規表現, 置換文字列）
_TECH_REPL = [
    (_re.compile(r'@InvocableMethod[としてで\s]*'), 'Flowのアクションとして呼び出され、'),
    (_re.compile(r'@AuraEnabled[としてで\s]*'), 'LWCから呼び出し可能で、'),
    (_re.compile(r'@RemoteAction[としてで\s]*'), '非同期で呼び出され、'),
    (_re.compile(r'@\w+'), ''),
    # ClassName.methodName() → 除去（前後の助詞が残る）
    (_re.compile(r'[A-Z][A-Za-z0-9]+\.[A-Za-z]\w+\([^)]*\)'), ''),
    # ClassName.methodName → 除去
    (_re.compile(r'[A-Z][A-Za-z0-9]+\.[A-Za-z]\w+'), ''),
    # 連続する句読点・空白を整理
    (_re.compile(r'[ \t]{2,}'), ' '),
    (_re.compile(r'(、){2,}'), '、'),
    (_re.compile(r'(。){2,}'), '。'),
]


def _clean_tech(text: str) -> str:
    """Apexアノテーション・クラス名.メソッド名パターンを除去して日本語説明にする。"""
    for pattern, repl in _TECH_REPL:
        text = pattern.sub(repl, text)
    return text.strip()


def _short_title(responsibility: str, max_len: int = 35) -> str:
    """responsibilityの先頭文からAPIを除去した短いタイトルを作る。"""
    clean = _clean_tech(responsibility)
    m = _re.match(r'^(.+?)[。．\n]', clean)
    title = m.group(1) if m else clean
    return title[:max_len].strip()


def _extract_actor(token: str) -> str:
    """フロートークンから日本語アクター名を推定する。"""
    t = _re.sub(r'（[^）]*）|\([^)]*\)', '', token).strip()
    if _re.search(r'お客様|顧客|申請者|依頼者', t):
        return "お客様"
    if _re.search(r'管理者|事務|担当者|スタッフ|GF社', t):
        return "GF社担当者"
    if _re.search(r'Flow|フロー|承認', t):
        return "自動フロー"
    if _re.search(r'[A-Z][a-zA-Z]', t):
        return "システム"
    return t[:20] if t else "システム"


def _infer_callees(data: dict) -> None:
    """data_flow_overview の「→」連鎖からコンポーネント間呼び出し関係を推論して callees に設定する。"""
    flow_text = data.get("data_flow_overview", "")
    if not flow_text:
        return
    comp_names = {c.get("api_name", "") for c in data.get("components", [])}
    if not comp_names:
        return

    # 最初の段落（。まで）だけ使う
    main_flow = flow_text.split("。")[0]
    tokens = _re.split(r'→', main_flow)

    def find_comp(token: str) -> str | None:
        for name in comp_names:
            if name and name in token:
                return name
        return None

    callees_map: dict[str, list[str]] = {n: [] for n in comp_names}
    prev = None
    for token in tokens:
        curr = find_comp(token)
        if curr and prev and prev != curr and curr not in callees_map[prev]:
            callees_map[prev].append(curr)
        if curr:
            prev = curr

    for comp in data.get("components", []):
        name = comp.get("api_name", "")
        if callees_map.get(name):
            comp["callees"] = callees_map[name]


def _build_business_flow(data: dict) -> list[dict]:
    """data_flow_overview の「→」トークンから業務フロー steps を生成する。"""
    flow_text = data.get("data_flow_overview", "")
    if not flow_text:
        return []

    comp_map = {c.get("api_name", ""): c for c in data.get("components", [])}
    # 最初の文（。まで）
    main_flow = flow_text.split("。")[0]
    tokens = [t.strip() for t in _re.split(r'→', main_flow) if t.strip()]

    steps = []
    for i, token in enumerate(tokens):
        # コンポーネント名が含まれる場合は対応するresponsibilityの先頭文を使う
        matched_comp = next((c for name, c in comp_map.items() if name and name in token), None)
        if matched_comp:
            responsibility = matched_comp.get("responsibility", "")
            action = _short_title(responsibility) if responsibility else _clean_tech(token)
            actor = "システム"
        else:
            clean = _re.sub(r'（[^）]*）|\([^)]*\)', '', token).strip()
            clean = _clean_tech(clean)
            if i == 0:
                actor = _extract_actor(token)
                action = f"{clean}から処理を依頼・起動する" if clean else "処理を開始する"
            else:
                actor = "システム"
                action = clean if clean else token.strip()

        steps.append({
            "step": i + 1,
            "actor": actor,
            "action": action,
            "system": matched_comp.get("api_name", "Salesforce") if matched_comp else "外部",
            "next": [{"to": i + 2}] if i < len(tokens) - 1 else [],
        })

    return steps


def _build_process_steps(data: dict) -> list[dict]:
    """components の responsibility から日本語の処理概要 steps を生成する。"""
    steps = []
    for i, comp in enumerate(data.get("components", []), 1):
        responsibility = comp.get("responsibility", "")
        comp_type = comp.get("type", "Apex")

        # 入出力情報を補足に追加
        desc_parts = [_clean_tech(responsibility)]
        if comp.get("inputs"):
            desc_parts.append(f"■ 受け取るデータ: {comp['inputs']}")
        if comp.get("outputs"):
            desc_parts.append(f"■ 出力・更新内容: {comp['outputs']}")
        if comp.get("error_handling"):
            desc_parts.append(f"■ エラー処理: {comp['error_handling']}")

        title = _short_title(responsibility) if responsibility else comp.get("api_name", "")

        # Flowは分岐処理が多いためbranchに "条件分岐あり" を設定
        branch = "条件分岐あり" if comp_type == "Flow" else None

        steps.append({
            "step": i,
            "title": title,
            "description": "\n".join(p for p in desc_parts if p),
            "component": comp.get("api_name", ""),
            "branch": branch,
            "next": [{"to": i + 1}] if i < len(data.get("components", [])) else [],
        })

    return steps


def _build_related_objects(data: dict) -> list[dict]:
    """component の inputs/outputs/responsibility から __c オブジェクトと標準オブジェクトを抽出する。"""
    seen: set[str] = set()
    objects: list[dict] = []

    all_texts = []
    for comp in data.get("components", []):
        all_texts += [
            comp.get("responsibility", ""),
            comp.get("inputs", ""),
            comp.get("outputs", ""),
        ]
    all_texts += [
        data.get("data_flow_overview", ""),
        data.get("processing_purpose", ""),
    ]
    combined = " ".join(all_texts)

    # __c オブジェクト
    for m in _re.finditer(r'([A-Z][A-Za-z0-9]*__c)\b', combined):
        api = m.group(1)
        if api not in seen:
            seen.add(api)
            # ラベル推定: CamelCase → スペース区切り（大文字前にスペース）
            raw = api.replace("__c", "")
            label = _re.sub(r'([A-Z])', r' \1', raw).strip()
            objects.append({
                "api_name": api, "label": label,
                "fields": [{"api_name": "-", "label": "（詳細は個票参照）",
                             "access": "", "note": ""}],
                "relations": [],
            })

    # 標準オブジェクト（一致する場合のみ）
    for std_api, std_label in _STD_OBJ_LABELS.items():
        # 単語境界で出現するものだけ
        if std_api not in seen and _re.search(rf'\b{std_api}\b', combined):
            seen.add(std_api)
            objects.append({
                "api_name": std_api, "label": std_label,
                "fields": [{"api_name": "-", "label": "（詳細は個票参照）",
                             "access": "", "note": ""}],
                "relations": [],
            })

    return objects


def _infer_users(data: dict) -> str:
    """processing_purpose / data_flow_overview からユーザー/利用部門を推定する。"""
    combined = " ".join([
        data.get("processing_purpose", ""),
        data.get("data_flow_overview", ""),
    ])
    parts = []
    if _re.search(r'お客様|顧客|申請者|Experience Cloud', combined):
        parts.append("お客様（Experience Cloudユーザー）")
    if _re.search(r'管理者|GF社|担当者|事務', combined):
        parts.append("GF社担当者")
    if _re.search(r'コンサル', combined):
        parts.append("GF社コンサル部")
    if _re.search(r'営業', combined):
        parts.append("GF社営業部")
    return "・".join(parts) if parts else ""


def _normalize_schema(data: dict) -> dict:
    """GFプロジェクト固有スキーマを generate_detail_design.py の標準スキーマに変換する。

    GFスキーマ → 標準スキーマ の主なマッピング:
      group_id           → feature_id
      processing_purpose → summary
      data_flow_overview → purpose / business_flow
      components[]       → process_steps（日本語化）・callees推論
      interfaces[]       → (補助情報のみ)
    """
    # feature_id
    if not data.get("feature_id") and data.get("group_id"):
        data["feature_id"] = data["group_id"]

    # 概要フィールド
    if not data.get("summary"):
        parts = [data.get("processing_purpose", "")]
        if data.get("notes"):
            parts.append(f"【前提・補足】{data['notes']}")
        data["summary"] = "\n".join(p for p in parts if p)

    if not data.get("purpose") and data.get("data_flow_overview"):
        data["purpose"] = data["data_flow_overview"]

    # 利用者推定
    if not data.get("users"):
        data["users"] = _infer_users(data)

    # 起点画面: LWC コンポーネントがあれば列挙、なければ空
    if not data.get("trigger_screen"):
        lwcs = [c.get("api_name", "") for c in data.get("components", [])
                if c.get("type") == "LWC"]
        if lwcs:
            data["trigger_screen"] = " / ".join(lwcs)

    # prerequisites → trigger
    if not data.get("trigger") and data.get("prerequisites"):
        data["trigger"] = data["prerequisites"]

    # components: responsibility → role（日本語化）& callees 初期化
    for comp in data.get("components", []):
        if not comp.get("role"):
            comp["role"] = _clean_tech(comp.get("responsibility", ""))
        if "callees" not in comp:
            comp["callees"] = []

    # callees を data_flow_overview から推論（まだ未設定の場合）
    if not any(comp.get("callees") for comp in data.get("components", [])):
        _infer_callees(data)

    # process_steps: components から日本語説明で生成
    if not data.get("process_steps"):
        data["process_steps"] = _build_process_steps(data)

    # business_flow: data_flow_overview から生成
    if not data.get("business_flow"):
        data["business_flow"] = _build_business_flow(data)

    # related_objects: outputs/inputs から __c・標準オブジェクトを抽出
    if not data.get("related_objects"):
        data["related_objects"] = _build_related_objects(data)

    return data


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

    # 2. オブジェクト参照マトリクス（対象オブジェクト）
    objects = data.get("related_objects", [])
    object_access = data.get("object_access", [])
    components = data.get("components", [])
    if objects:
        try:
            er_path = str(Path(tmp_dir) / "er.png")
            if object_access:
                from diagram_utils import generate_object_component_matrix
                generate_object_component_matrix(
                    object_access, components, objects, er_path)
            else:
                # object_access がない場合は従来のER図にフォールバック
                from er_utils import generate_er_image
                boxes, arrows = _related_objects_to_er_boxes(objects)
                n_obj = len(boxes)
                er_w = min(14, max(8, n_obj * 3.0))
                er_h = min(10, max(6, n_obj * 2.0))
                generate_er_image(boxes, arrows, er_path,
                                  title="オブジェクト関連図",
                                  slide_w=er_w, slide_h=er_h)
            paths["er"] = er_path
            print("  [OK] オブジェクト参照マトリクス")
        except Exception as e:
            print(f"  [WARN] オブジェクト参照マトリクス: {e}")

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
                dst_step = n.get("to") or (flows[i + 1].get("step", i + 2) if i + 1 < len(flows) else None)
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


def _related_objects_to_er_boxes(objects: list[dict]) -> tuple[list, list]:
    """related_objects を er_utils.generate_er_image 用の (boxes, arrows) に変換する。

    自動グリッドレイアウト: オブジェクトを横に並べ、収まらなければ折り返す。
    """
    import math

    n = len(objects)
    cols = min(n, 3)
    rows = math.ceil(n / cols)

    # レイアウト定数
    box_w = 3.0
    box_h_base = 1.2
    field_h = 0.32
    x_gap = 1.0
    y_gap = 1.0
    x_start = 1.0
    y_start = 1.5  # タイトルバー分

    boxes = []
    obj_id_map: dict[str, str] = {}  # api_name -> box id

    for i, obj in enumerate(objects):
        api = obj.get("api_name", "")
        label = obj.get("label", "")
        fk_fields = [f for f in obj.get("fields", []) if f.get("access") in ("RW", "W")]
        n_fields = min(len(fk_fields), 4)  # 表示上限4フィールド
        h = box_h_base + n_fields * field_h

        col_idx = i % cols
        row_idx = i // cols
        x = x_start + col_idx * (box_w + x_gap)
        y = y_start + row_idx * (box_h_base + 4 * field_h + y_gap)

        style = "primary" if "__c" in api else "secondary"
        box_id = api.replace("__c", "_c").replace("__", "_")
        obj_id_map[api] = box_id

        box_fields = []
        for fi, f in enumerate(fk_fields[:4]):
            box_fields.append({
                "name": f.get("api_name", ""),
                "label": f.get("label", ""),
                "is_fk": any(
                    r.get("to") == f.get("api_name", "")
                    or r.get("field", "") == f.get("api_name", "")
                    for r in obj.get("relations", [])
                ),
            })

        boxes.append({
            "id": box_id,
            "api": api,
            "label": label,
            "x": x, "y": y, "w": box_w, "h": h,
            "style": style,
            "fields": box_fields,
        })

    arrows = []
    for obj in objects:
        src_api = obj.get("api_name", "")
        src_id = obj_id_map.get(src_api, "")
        for rel in obj.get("relations", []):
            to_api = rel.get("to", "")
            dst_id = obj_id_map.get(to_api, "")
            if not dst_id:
                continue
            rel_type = rel.get("type", "lookup").lower()
            arrows.append({
                "from": src_id,
                "to": dst_id,
                "rel": rel_type,
                "field": rel.get("field", rel.get("label", "")),
            })

    return boxes, arrows


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
    data = _normalize_schema(data)   # GFスキーマ → 標準スキーマ変換
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

        fill_process_overview(
            wb["処理概要"], data,
            changed_step_nos=set() if is_major else changed_proc_steps,
            png_path=png_paths.get("flowchart"))

        fill_target_objects(
            wb["対象オブジェクト"], data,
            changed_obj_keys=set() if is_major else changed_objs,
            png_path=png_paths.get("er"))

        fill_related_components(
            wb["関連コンポーネント"], data,
            changed_comp_keys=set() if is_major else changed_comps,
            png_path=png_paths.get("component"))

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
