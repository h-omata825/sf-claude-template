# -*- coding: utf-8 -*-
"""
詳細設計書.xlsx を1機能グループ分生成する（テンプレート読込方式）。

  詳細設計書テンプレート.xlsx（build_detail_design_template.py で生成した「器」）を
  コピーしてセル値を流し込む。

5シート構成:
  1. 改版履歴                   : メタ + 履歴テーブル
  2. グループ詳細               : 処理目的 / データ連携概要 / 前提条件
  3. コンポーネント仕様         : 担当処理 / 入力 / 出力 / エラー処理
  4. インターフェース定義       : メソッド/API名 / パラメータ / 返却値 / 例外
  5. 画面仕様                   : 画面項目 / UI種別 / 型 / 必須 / バリデーション

Usage:
  python generate_detail_design.py \\
    --input  detail_design.json \\
    --template "C:/.../詳細設計書テンプレート.xlsx" \\
    --output-dir "C:/.../出力ルート"

出力先: {output-dir}/detail/【GRP-001】機能グループ名.xlsx

JSON スキーマ:
{
  "group_id": "GRP-001",
  "name_ja": "見積依頼",
  "name_en": "QuotationRequest",
  "project_name": "...",
  "author": "...",
  "date": "YYYY-MM-DD",
  "processing_purpose": "エンジニア向けの処理目的説明",
  "data_flow_overview": "コンポーネント間のデータ連携の概要",
  "prerequisites": "前提条件",
  "notes": "備考",
  "components": [
    {
      "api_name": "QuotationRequestController",
      "type": "Apex",
      "responsibility": "担当処理（1〜2文）",
      "inputs": "入力データの概要",
      "outputs": "返却データの概要",
      "error_handling": "エラー処理の方針"
    }
  ],
  "interfaces": [
    {
      "component": "QuotationRequestController",
      "method": "saveQuotation",
      "description": "処理内容",
      "input_params": "String quotationName, Id accountId",
      "return_value": "Id（作成されたレコードID）",
      "exceptions": "AuraHandledException"
    }
  ],
  "screens": [
    {
      "component": "QuotationRequestPage",
      "screen_name": "見積依頼入力画面",
      "items": [
        {
          "label": "見積件名",
          "api_name": "Name",
          "ui_type": "テキスト",
          "data_type": "String",
          "required": true,
          "default_value": "",
          "validation": "必須入力"
        }
      ]
    }
  ]
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as _date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import design_revision as dr
from meta_store import read_meta, write_meta
from version_manager import increment_version

# ── 色定数 ─────────────────────────────────────────────────────────
C_HDR_BLUE  = "2E75B6"
C_BAND_BLUE = "0070C0"
C_LABEL_BG  = "D9E1F2"
C_FONT_D    = "000000"
C_FONT_W    = "FFFFFF"
C_FONT_GRAY = "595959"

THIN = Side(style="thin",   color="8B9DC3")
MED  = Side(style="medium", color="1F3864")

# ── テンプレートと一致させる定数 ────────────────────────────────────
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

# グループ詳細
GRP_META_ROW_1 = 3
GRP_META_ROW_2 = 4
GRP_META_1_V = {
    "project_name": (6,  16),
    "group_id":     (21, 24),
    "author":       (28, 29),
    "version":      (31, 31),
}
GRP_META_2_V = {
    "name_ja": (6,  24),
    "date":    (28, 31),
}
GRP_LABEL_VAL_CS = 7
GRP_LABEL_VAL_CE = 31
GRP_SECTION_ROW = {
    "processing_purpose":  7,
    "data_flow_overview":  10,
    "prerequisites":       13,
    "notes":               14,
}

# コンポーネント仕様（テンプレート定数と同一）
CM_DATA_ROW_START = 5
CM_API_CS,  CM_API_CE  = 2,  8
CM_TYPE_CS, CM_TYPE_CE = 9,  11
CM_RSP_CS,  CM_RSP_CE  = 12, 20
CM_IN_CS,   CM_IN_CE   = 21, 24
CM_OUT_CS,  CM_OUT_CE  = 25, 28
CM_ERR_CS,  CM_ERR_CE  = 29, 31

# インターフェース定義（テンプレート定数と同一）
IF_DATA_ROW_START = 5
IF_CMP_CS,  IF_CMP_CE  = 2,  6
IF_MTD_CS,  IF_MTD_CE  = 7,  12
IF_DSC_CS,  IF_DSC_CE  = 13, 19
IF_PRM_CS,  IF_PRM_CE  = 20, 25
IF_RET_CS,  IF_RET_CE  = 26, 29
IF_EXC_CS,  IF_EXC_CE  = 30, 31

# 画面仕様（テンプレート定数と同一）
SC_SEC_ROW        = 3   # 最初の画面セクション行（テンプレート上の雛形）
SC_HEAD_ROW       = 4
SC_DATA_ROW_START = 5
SC_NO_CS,   SC_NO_CE   = 2,  3
SC_LBL_CS,  SC_LBL_CE  = 4,  8
SC_API_CS,  SC_API_CE  = 9,  14
SC_UI_CS,   SC_UI_CE   = 15, 17
SC_TYP_CS,  SC_TYP_CE  = 18, 19
SC_REQ_CS,  SC_REQ_CE  = 20, 21
SC_DEF_CS,  SC_DEF_CE  = 22, 24
SC_VAL_CS,  SC_VAL_CE  = 25, 31

GRID_RIGHT = 31
SC_COL_GROUPS = [(SC_NO_CS, SC_NO_CE), (SC_LBL_CS, SC_LBL_CE),
                 (SC_API_CS, SC_API_CE), (SC_UI_CS, SC_UI_CE),
                 (SC_TYP_CS, SC_TYP_CE), (SC_REQ_CS, SC_REQ_CE),
                 (SC_DEF_CS, SC_DEF_CE), (SC_VAL_CS, SC_VAL_CE)]

SCALAR_FIELDS  = ["processing_purpose", "data_flow_overview", "prerequisites", "notes"]
SECTION_SHEETS = {
    "components":  "コンポーネント仕様",
    "interfaces":  "インターフェース定義",
    "screens":     "画面仕様",
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


# ── シート埋め込み ─────────────────────────────────────────────────
def fill_revision(ws, data: dict, history: list[dict]):
    vs, _ = REV_META_PROJECT_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("project_name", ""))
    vs, _ = REV_META_DATE_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("date", ""))
    dr.fill_revision_table(ws, history, REV_COLS, REV_DATA_ROW_START)


def fill_group_detail(ws, data: dict, changed_fields: set):
    for key, (cs, _) in GRP_META_1_V.items():
        ws.cell(row=GRP_META_ROW_1, column=cs, value=data.get(key, ""))
    for key, (cs, _) in GRP_META_2_V.items():
        ws.cell(row=GRP_META_ROW_2, column=cs, value=data.get(key, ""))
    for key, row in GRP_SECTION_ROW.items():
        val = data.get(key, "")
        if val:
            cell = ws.cell(row=row, column=GRP_LABEL_VAL_CS, value=val)
            if key in changed_fields:
                dr.apply_red(cell, size=10)


def fill_component_spec(ws, data: dict, changed_keys: set):
    components = data.get("components", [])
    r = CM_DATA_ROW_START
    for comp in components:
        key = comp.get("api_name", "")
        is_changed = key in changed_keys
        set_h(ws, r, 36)
        c1 = MW(ws, r, CM_API_CS,  CM_API_CE,  key,                          border=B_all(), v="top")
        c2 = MW(ws, r, CM_TYPE_CS, CM_TYPE_CE, comp.get("type", ""),         border=B_all(), h="center")
        c3 = MW(ws, r, CM_RSP_CS,  CM_RSP_CE,  comp.get("responsibility", ""), border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, CM_IN_CS,   CM_IN_CE,   comp.get("inputs", ""),       border=B_all(), wrap=True, v="top")
        c5 = MW(ws, r, CM_OUT_CS,  CM_OUT_CE,  comp.get("outputs", ""),      border=B_all(), wrap=True, v="top")
        c6 = MW(ws, r, CM_ERR_CS,  CM_ERR_CE,  comp.get("error_handling", ""), border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4, c5, c6):
                dr.apply_red(c)
        r += 1


def fill_interface_def(ws, data: dict, changed_keys: set):
    interfaces = data.get("interfaces", [])
    r = IF_DATA_ROW_START
    for iface in interfaces:
        key = iface.get("method", "")
        is_changed = key in changed_keys
        set_h(ws, r, 36)
        c1 = MW(ws, r, IF_CMP_CS, IF_CMP_CE, iface.get("component", ""),    border=B_all(), v="top")
        c2 = MW(ws, r, IF_MTD_CS, IF_MTD_CE, key,                            border=B_all(), v="top")
        c3 = MW(ws, r, IF_DSC_CS, IF_DSC_CE, iface.get("description", ""),  border=B_all(), wrap=True, v="top")
        c4 = MW(ws, r, IF_PRM_CS, IF_PRM_CE, iface.get("input_params", ""), border=B_all(), wrap=True, v="top")
        c5 = MW(ws, r, IF_RET_CS, IF_RET_CE, iface.get("return_value", ""), border=B_all(), wrap=True, v="top")
        c6 = MW(ws, r, IF_EXC_CS, IF_EXC_CE, iface.get("exceptions", ""),   border=B_all(), wrap=True, v="top")
        if is_changed:
            for c in (c1, c2, c3, c4, c5, c6):
                dr.apply_red(c)
        r += 1


def fill_screen_spec(ws, data: dict):
    """画面ごとにセクション帯+ヘッダ+データ行を積み上げる。"""
    screens = data.get("screens", [])
    if not screens:
        return

    r = SC_SEC_ROW  # テンプレートの雛形行から上書き開始

    for screen in screens:
        screen_name = screen.get("screen_name", screen.get("component", "画面"))

        # セクション帯（画面名）
        set_h(ws, r, 26)
        MW(ws, r, 2, GRID_RIGHT, f"■ {screen_name}",
           bold=True, fg=C_FONT_W, bg=C_BAND_BLUE, size=11, border=B_all())
        r += 1

        # テーブルヘッダー
        set_h(ws, r, 26)
        hdr_cols = [
            (SC_NO_CS,  SC_NO_CE,  "No"),
            (SC_LBL_CS, SC_LBL_CE, "項目名"),
            (SC_API_CS, SC_API_CE, "API名/プロパティ"),
            (SC_UI_CS,  SC_UI_CE,  "UI種別"),
            (SC_TYP_CS, SC_TYP_CE, "型"),
            (SC_REQ_CS, SC_REQ_CE, "必須"),
            (SC_DEF_CS, SC_DEF_CE, "初期値"),
            (SC_VAL_CS, SC_VAL_CE, "バリデーション"),
        ]
        for cs, ce, label in hdr_cols:
            MW(ws, r, cs, ce, label,
               bold=True, fg=C_FONT_W, bg=C_HDR_BLUE, h="center", border=B_all())
        r += 1

        # データ行
        items = screen.get("items", [])
        for i, item in enumerate(items):
            set_h(ws, r, 22)
            MW(ws, r, SC_NO_CS,  SC_NO_CE,  str(i + 1),                      border=B_all(), h="center")
            MW(ws, r, SC_LBL_CS, SC_LBL_CE, item.get("label", ""),           border=B_all())
            MW(ws, r, SC_API_CS, SC_API_CE, item.get("api_name", ""),         border=B_all())
            MW(ws, r, SC_UI_CS,  SC_UI_CE,  item.get("ui_type", ""),          border=B_all(), h="center")
            MW(ws, r, SC_TYP_CS, SC_TYP_CE, item.get("data_type", ""),        border=B_all(), h="center")
            MW(ws, r, SC_REQ_CS, SC_REQ_CE, "○" if item.get("required") else "", border=B_all(), h="center")
            MW(ws, r, SC_DEF_CS, SC_DEF_CE, item.get("default_value", ""),   border=B_all())
            MW(ws, r, SC_VAL_CS, SC_VAL_CE, item.get("validation", ""),       border=B_all(), wrap=True)
            r += 1

        # 画面間スペーサー
        set_h(ws, r, 10)
        r += 1


# ── 差分計算 ────────────────────────────────────────────────────────
def _compute_diffs(prev_data: dict | None, new_data: dict) -> dict:
    if prev_data is None:
        return {"scalars": [], "lists": {}}
    return {
        "scalars": dr.diff_scalars(prev_data, new_data, SCALAR_FIELDS),
        "lists": {
            "components": dr.diff_list(
                prev_data.get("components", []),
                new_data.get("components", []), "api_name"),
            "interfaces": dr.diff_list(
                prev_data.get("interfaces", []),
                new_data.get("interfaces", []), "method"),
            "screens": dr.diff_list(
                prev_data.get("screens", []),
                new_data.get("screens", []), "component"),
        },
    }


# ── メイン ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="詳細設計書 Excel 生成")
    parser.add_argument("--input",      required=True, help="詳細設計 JSON ファイルパス")
    parser.add_argument("--template",   required=True, help="詳細設計書テンプレート.xlsx パス")
    parser.add_argument("--output-dir", required=True, help="出力先ディレクトリ")
    parser.add_argument("--source-file", default="",
                        help="更新時: 既存の詳細設計書xlsxパス")
    parser.add_argument("--version-increment", default="minor",
                        choices=["minor", "major"])
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    today  = _date.today().strftime("%Y-%m-%d")
    author = data.get("author", "")

    group_id  = data.get("group_id", "GRP-000")
    name_ja   = data.get("name_ja", "機能グループ")
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", name_ja)

    out_dir = Path(args.output_dir) / "detail"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"【{group_id}】{safe_name}.xlsx"

    # ── バージョン判定 ────────────────────────────────────────────
    source_file = args.source_file.strip()
    if not source_file:
        existing = sorted(out_dir.glob(f"【{group_id}】*.xlsx"),
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
        print(f"更新モード: {prev_meta.get('version', '?')} → {current_version}")
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
        scalar_sheet="グループ詳細",
    )
    history = history + new_entries

    changed_scalars = dr.changed_scalar_fields(diffs)
    changed_comps   = dr.changed_ids(diffs, "components")
    changed_ifaces  = dr.changed_ids(diffs, "interfaces")
    is_major        = (args.version_increment == "major")

    # ── テンプレ読込 → セル流し込み ──────────────────────────────
    wb = load_workbook(args.template)
    fill_revision(
        wb["改版履歴"], data, history)
    fill_group_detail(
        wb["グループ詳細"], data,
        changed_fields=set() if is_major else changed_scalars)
    fill_component_spec(
        wb["コンポーネント仕様"], data,
        changed_keys=set() if is_major else changed_comps)
    fill_interface_def(
        wb["インターフェース定義"], data,
        changed_keys=set() if is_major else changed_ifaces)
    fill_screen_spec(
        wb["画面仕様"], data)

    write_meta(wb, {
        "version": current_version,
        "date":    today,
        "author":  author,
        "data":    data,
        "history": history,
    })

    wb.save(str(out_path))
    sys.stdout.buffer.write(
        f"[OK] 詳細設計書を生成しました: v{current_version} → {out_path}\n".encode("utf-8"))

    for old_f in out_dir.glob(f"【{group_id}】*.xlsx"):
        if old_f.resolve() != out_path.resolve():
            old_f.unlink()
            sys.stdout.buffer.write(
                f"  [CLEANUP] 旧ファイルを削除: {old_f.name}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
