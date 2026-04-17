# -*- coding: utf-8 -*-
"""
基本設計書.xlsx を1機能グループ分生成する（テンプレートなし・直接生成）。

2シート構成:
  1. 機能概要: グループ概要・業務の流れ・構成コンポーネント・関連オブジェクト・外部連携・前提条件
  2. 改版履歴: メタ + 履歴テーブル

Usage:
  python generate_basic_design.py \\
    --input  basic_design.json \\
    --output-dir "C:/.../出力ルート"

出力先: {output-dir}/basic/【GRP-001】機能グループ名.xlsx

JSON スキーマ:
{
  "group_id": "GRP-001",
  "name_ja": "見積依頼",
  "name_en": "QuotationRequest",
  "project_name": "...",
  "author": "...",
  "version": "1.0",
  "date": "YYYY-MM-DD",
  "purpose": "業務目的",
  "target_users": "対象ユーザー",
  "usage_scene": "利用シーン",
  "business_flow": [
    {"step": "1", "actor": "担当", "action": "操作・処理内容", "system": "コンポーネント名"}
  ],
  "components": [
    {"api_name": "...", "type": "Apex/LWC/...", "role": "役割概要"}
  ],
  "related_objects": [
    {"api_name": "...", "label": "ラベル", "usage": "用途"}
  ],
  "external_integrations": [
    {"target": "連携先", "direction": "送信/受信", "data": "データ内容", "timing": "タイミング"}
  ],
  "prerequisites": "前提条件",
  "notes": "備考"
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date as _date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ── 色定数 ─────────────────────────────────────────────────────────
C_TITLE_BG   = "1F3864"   # 表紙タイトル（濃紺）
C_HDR_BLUE   = "2E75B6"   # セクションヘッダー（青）
C_BAND_BLUE  = "4472C4"   # テーブルヘッダー（中青）
C_LABEL_BG   = "D9E1F2"   # ラベル背景（薄青）
C_META_BG    = "F2F2F2"   # メタ行背景（薄グレー）
C_STEP_BG    = "E2EFDA"   # 業務フロー行（薄緑）
C_ALT_BG     = "FAFAFA"   # 交互行背景（ほぼ白）
C_FONT_D     = "000000"
C_FONT_W     = "FFFFFF"
C_FONT_GRAY  = "595959"

THIN = Side(style="thin",   color="8B9DC3")
MED  = Side(style="medium", color="1F3864")

# ── 列レイアウト定数 ─────────────────────────────────────────────
# 全16列（col 2〜17）使用。col 1は左マージン用。
COL_START   = 2
COL_END     = 17
# ラベルエリア（2〜4列）
LABEL_CS, LABEL_CE = 2, 4
# コンテンツエリア（5〜17列）
CONT_CS,  CONT_CE  = 5, 17
# テーブル列定義（業務の流れ）
BF_STEP_CS,   BF_STEP_CE   = 2, 2
BF_ACTOR_CS,  BF_ACTOR_CE  = 3, 4
BF_ACTION_CS, BF_ACTION_CE = 5, 13
BF_SYS_CS,    BF_SYS_CE    = 14, 17
# テーブル列定義（構成コンポーネント）
CM_TYPE_CS,   CM_TYPE_CE   = 2, 3
CM_API_CS,    CM_API_CE    = 4, 7
CM_ROLE_CS,   CM_ROLE_CE   = 8, 17
# テーブル列定義（関連オブジェクト）
OB_API_CS,    OB_API_CE    = 2, 4
OB_LABEL_CS,  OB_LABEL_CE  = 5, 8
OB_USAGE_CS,  OB_USAGE_CE  = 9, 17
# テーブル列定義（外部連携）
EX_TARGET_CS, EX_TARGET_CE = 2, 4
EX_DIR_CS,    EX_DIR_CE    = 5, 6
EX_DATA_CS,   EX_DATA_CE   = 7, 12
EX_TIME_CS,   EX_TIME_CE   = 13, 17

META_ROW  = 3   # メタデータ行


# ── スタイルヘルパー ────────────────────────────────────────────────
def _fill(c): return PatternFill("solid", fgColor=c)

def _fnt(bold=False, color=C_FONT_D, size=10, italic=False):
    return Font(name="游ゴシック", bold=bold, color=color, size=size, italic=italic)

def _aln(h="left", v="center", wrap=True):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def _B(): return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
def _BM(): return Border(left=MED, right=MED, top=MED, bottom=MED)

def W(ws, row, col, value="", bold=False, fg=C_FONT_D, bg=None,
      h="left", v="center", wrap=True, border=None, size=10, italic=False):
    c = ws.cell(row=row, column=col, value=value)
    c.font = _fnt(bold=bold, color=fg, size=size, italic=italic)
    c.alignment = _aln(h=h, v=v, wrap=wrap)
    if bg:
        c.fill = _fill(bg)
    if border:
        c.border = border
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

def set_h(ws, row, pts):
    ws.row_dimensions[row].height = pts


# ── 列幅設定 ────────────────────────────────────────────────────────
def _set_col_widths(ws):
    widths = {
        1: 1.5,   # 左マージン
        2: 5,
        3: 8,
        4: 8,
        5: 12,
        6: 8, 7: 8, 8: 8, 9: 8, 10: 8,
        11: 8, 12: 8, 13: 8,
        14: 8, 15: 8, 16: 8, 17: 8,
    }
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w


# ── セクションヘッダー描画 ──────────────────────────────────────────
def _section_header(ws, row, text):
    set_h(ws, row, 22)
    MW(ws, row, COL_START, COL_END, f"■ {text}",
       bold=True, fg=C_FONT_W, bg=C_HDR_BLUE, size=11,
       border=_BM(), h="left", v="center")
    return row + 1


# ── ラベル+値の2列行 ───────────────────────────────────────────────
def _label_row(ws, row, label, value, min_h=20, value_rows=1):
    set_h(ws, row, max(min_h, value_rows * 15 + 5))
    MW(ws, row, LABEL_CS, LABEL_CE, label,
       bold=True, bg=C_LABEL_BG, border=_B(), v="center")
    MW(ws, row, CONT_CS, CONT_CE, value,
       border=_B(), wrap=True, v="top" if value_rows > 1 else "center")
    return row + 1


# ── テーブルヘッダー行 ──────────────────────────────────────────────
def _table_header(ws, row, cols: list[tuple]):
    """cols: [(cs, ce, label), ...]"""
    set_h(ws, row, 22)
    for cs, ce, label in cols:
        MW(ws, row, cs, ce, label,
           bold=True, fg=C_FONT_W, bg=C_BAND_BLUE,
           border=_B(), h="center")
    return row + 1


# ── 機能概要シート ──────────────────────────────────────────────────
def fill_overview(ws, data: dict):
    _set_col_widths(ws)

    # 行1: 空白（上マージン）
    ws.row_dimensions[1].height = 10

    # 行2: 大タイトル
    set_h(ws, 2, 36)
    MW(ws, 2, COL_START, COL_END, "基本設計書",
       bold=True, fg=C_FONT_W, bg=C_TITLE_BG, size=16,
       h="center", border=_BM())

    # 行3: メタ（プロジェクト名 / 機能グループ名 / 作成者 / 日付 / 版数）
    set_h(ws, 3, 20)
    meta_cols = [
        (2, 4,   "プロジェクト名"), (5, 8,   data.get("project_name", "")),
        (9, 10,  "グループ名"),     (11, 14, data.get("name_ja", "")),
        (15, 15, "作成者"),         (16, 16, data.get("author", "")),
        (17, 17, "版数"),
    ]
    for cs, ce, val in meta_cols:
        is_label = isinstance(val, str) and val in ("プロジェクト名", "グループ名", "作成者", "版数")
        MW(ws, 3, cs, ce, val,
           bold=is_label, bg=C_META_BG if is_label else None,
           border=_B(), h="center" if is_label else "left")
    W(ws, 3, 17, data.get("version", "1.0"), border=_B(), h="center")

    # 行4: 空白区切り
    ws.row_dimensions[4].height = 8

    r = 5

    # ── セクション1: グループ概要 ──
    r = _section_header(ws, r, "1. グループ概要")

    fields = [
        ("機能グループ名", data.get("name_ja", "")),
        ("業務目的",       data.get("purpose", "")),
        ("対象ユーザー",   data.get("target_users", "")),
        ("利用シーン",     data.get("usage_scene", "")),
    ]
    for label, value in fields:
        lines = max(1, value.count("\n") + 1, len(value) // 50 + 1) if value else 1
        r = _label_row(ws, r, label, value, value_rows=lines)

    # 空白区切り
    ws.row_dimensions[r].height = 8
    r += 1

    # ── セクション2: 業務の流れ ──
    r = _section_header(ws, r, "2. 業務の流れ")
    r = _table_header(ws, r, [
        (BF_STEP_CS,  BF_STEP_CE,  "No"),
        (BF_ACTOR_CS, BF_ACTOR_CE, "担当"),
        (BF_ACTION_CS, BF_ACTION_CE, "操作・処理内容"),
        (BF_SYS_CS,   BF_SYS_CE,   "関連コンポーネント"),
    ])

    flows = data.get("business_flow", [])
    if not flows:
        set_h(ws, r, 20)
        MW(ws, r, COL_START, COL_END, "（業務フロー未定義）",
           fg=C_FONT_GRAY, italic=True, border=_B(), h="center")
        r += 1
    else:
        for i, flow in enumerate(flows):
            bg = C_STEP_BG if i % 2 == 0 else None
            action = flow.get("action", "")
            lines = max(1, len(action) // 35 + action.count("\n") + 1)
            set_h(ws, r, max(20, lines * 15 + 5))
            MW(ws, r, BF_STEP_CS,  BF_STEP_CE,  flow.get("step", str(i + 1)),
               border=_B(), bg=bg, h="center")
            MW(ws, r, BF_ACTOR_CS, BF_ACTOR_CE, flow.get("actor", ""),
               border=_B(), bg=bg, h="center")
            MW(ws, r, BF_ACTION_CS, BF_ACTION_CE, action,
               border=_B(), bg=bg, wrap=True, v="top")
            MW(ws, r, BF_SYS_CS,   BF_SYS_CE,   flow.get("system", ""),
               border=_B(), bg=bg, wrap=True, v="top")
            r += 1

    ws.row_dimensions[r].height = 8
    r += 1

    # ── セクション3: 構成コンポーネント ──
    r = _section_header(ws, r, "3. 構成コンポーネント")
    r = _table_header(ws, r, [
        (CM_TYPE_CS, CM_TYPE_CE, "種別"),
        (CM_API_CS,  CM_API_CE,  "API名"),
        (CM_ROLE_CS, CM_ROLE_CE, "役割概要"),
    ])

    components = data.get("components", [])
    if not components:
        set_h(ws, r, 20)
        MW(ws, r, COL_START, COL_END, "（コンポーネント未定義）",
           fg=C_FONT_GRAY, italic=True, border=_B(), h="center")
        r += 1
    else:
        for i, comp in enumerate(components):
            bg = None if i % 2 == 0 else C_ALT_BG
            role = comp.get("role", "")
            lines = max(1, len(role) // 45 + role.count("\n") + 1)
            set_h(ws, r, max(20, lines * 15 + 5))
            MW(ws, r, CM_TYPE_CS, CM_TYPE_CE, comp.get("type", ""),
               border=_B(), bg=bg, h="center")
            MW(ws, r, CM_API_CS,  CM_API_CE,  comp.get("api_name", ""),
               border=_B(), bg=bg)
            MW(ws, r, CM_ROLE_CS, CM_ROLE_CE, role,
               border=_B(), bg=bg, wrap=True, v="top")
            r += 1

    ws.row_dimensions[r].height = 8
    r += 1

    # ── セクション4: 関連オブジェクト ──
    r = _section_header(ws, r, "4. 関連オブジェクト")
    r = _table_header(ws, r, [
        (OB_API_CS,   OB_API_CE,   "API名"),
        (OB_LABEL_CS, OB_LABEL_CE, "ラベル"),
        (OB_USAGE_CS, OB_USAGE_CE, "用途"),
    ])

    objects = data.get("related_objects", [])
    if not objects:
        set_h(ws, r, 20)
        MW(ws, r, COL_START, COL_END, "（関連オブジェクト未定義）",
           fg=C_FONT_GRAY, italic=True, border=_B(), h="center")
        r += 1
    else:
        for i, obj in enumerate(objects):
            bg = None if i % 2 == 0 else C_ALT_BG
            set_h(ws, r, 22)
            MW(ws, r, OB_API_CS,   OB_API_CE,   obj.get("api_name", ""),
               border=_B(), bg=bg)
            MW(ws, r, OB_LABEL_CS, OB_LABEL_CE, obj.get("label", ""),
               border=_B(), bg=bg, h="center")
            MW(ws, r, OB_USAGE_CS, OB_USAGE_CE, obj.get("usage", ""),
               border=_B(), bg=bg, wrap=True)
            r += 1

    ws.row_dimensions[r].height = 8
    r += 1

    # ── セクション5: 外部連携（データがある場合のみ）──
    integrations = data.get("external_integrations", [])
    if integrations:
        r = _section_header(ws, r, "5. 外部連携")
        r = _table_header(ws, r, [
            (EX_TARGET_CS, EX_TARGET_CE, "連携先"),
            (EX_DIR_CS,    EX_DIR_CE,    "方向"),
            (EX_DATA_CS,   EX_DATA_CE,   "データ内容"),
            (EX_TIME_CS,   EX_TIME_CE,   "タイミング"),
        ])
        for i, itg in enumerate(integrations):
            bg = None if i % 2 == 0 else C_ALT_BG
            set_h(ws, r, 22)
            MW(ws, r, EX_TARGET_CS, EX_TARGET_CE, itg.get("target", ""),
               border=_B(), bg=bg)
            MW(ws, r, EX_DIR_CS,    EX_DIR_CE,    itg.get("direction", ""),
               border=_B(), bg=bg, h="center")
            MW(ws, r, EX_DATA_CS,   EX_DATA_CE,   itg.get("data", ""),
               border=_B(), bg=bg, wrap=True)
            MW(ws, r, EX_TIME_CS,   EX_TIME_CE,   itg.get("timing", ""),
               border=_B(), bg=bg, wrap=True)
            r += 1
        ws.row_dimensions[r].height = 8
        r += 1

    # ── セクション6: 前提条件・備考 ──
    r = _section_header(ws, r, "6. 前提条件・備考")
    prerequisites = data.get("prerequisites", "特になし")
    notes = data.get("notes", "")
    pre_lines = max(1, len(prerequisites) // 55 + prerequisites.count("\n") + 1)
    r = _label_row(ws, r, "前提条件", prerequisites or "特になし", value_rows=pre_lines)
    if notes:
        note_lines = max(1, len(notes) // 55 + notes.count("\n") + 1)
        r = _label_row(ws, r, "備考", notes, value_rows=note_lines)

    # シートの印刷設定
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.print_area = f"A1:{get_column_letter(COL_END)}{r}"


# ── 改版履歴シート ──────────────────────────────────────────────────
def fill_revision(ws, data: dict):
    # 列幅
    col_widths = {1: 1.5, 2: 6, 3: 8, 4: 20, 5: 30, 6: 20, 7: 10, 8: 12, 9: 8}
    for col, w in col_widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[1].height = 10

    # タイトル
    set_h(ws, 2, 28)
    MW(ws, 2, 2, 9, "改版履歴",
       bold=True, fg=C_FONT_W, bg=C_TITLE_BG, size=13, h="center", border=_BM())

    # メタ
    set_h(ws, 3, 20)
    meta = [
        (2, 3, "プロジェクト名"), (4, 5, data.get("project_name", "")),
        (6, 7, "機能グループ"),   (8, 9, data.get("name_ja", "")),
    ]
    for cs, ce, val in meta:
        is_label = val in ("プロジェクト名", "機能グループ")
        MW(ws, 3, cs, ce, val, bold=is_label,
           bg=C_META_BG if is_label else None,
           border=_B(), h="center" if is_label else "left")

    set_h(ws, 4, 8)

    # テーブルヘッダー
    set_h(ws, 5, 22)
    hdrs = [(2, "項番"), (3, "版数"), (4, "変更箇所"), (5, "変更内容"),
            (6, "変更理由"), (7, "変更日"), (8, "変更者"), (9, "備考")]
    for col, label in hdrs:
        W(ws, 5, col, label, bold=True, fg=C_FONT_W, bg=C_BAND_BLUE,
          border=_B(), h="center")

    # 初版行
    set_h(ws, 6, 20)
    today = data.get("date", str(_date.today()))
    row_data = [
        (2, "1"), (3, "1.0"), (4, "新規作成"), (5, "初版作成"),
        (6, ""), (7, today), (8, data.get("author", "")), (9, ""),
    ]
    for col, val in row_data:
        W(ws, 6, col, val, border=_B(), h="center" if col in (2, 3, 7) else "left")


# ── メイン ──────────────────────────────────────────────────────────
def generate(data: dict, output_dir: Path) -> Path:
    group_id = data.get("group_id", "GRP-000")
    name_ja  = data.get("name_ja", "機能グループ")

    wb = Workbook()
    # デフォルトシートを「機能概要」として使用
    ws_ov = wb.active
    ws_ov.title = "機能概要"
    fill_overview(ws_ov, data)

    ws_rev = wb.create_sheet("改版履歴")
    fill_revision(ws_rev, data)

    # 出力先
    out_dir = output_dir / "basic"
    out_dir.mkdir(parents=True, exist_ok=True)
    # ファイル名に使えない文字を除去
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", name_ja)
    out_path = out_dir / f"【{group_id}】{safe_name}.xlsx"
    wb.save(str(out_path))
    return out_path


def main():
    parser = argparse.ArgumentParser(description="基本設計書 Excel 生成")
    parser.add_argument("--input",      required=True, help="基本設計 JSON ファイルパス")
    parser.add_argument("--output-dir", required=True, help="出力先ディレクトリ")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} が見つかりません", file=sys.stderr)
        sys.exit(1)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    out_path = generate(data, Path(args.output_dir))
    sys.stdout.buffer.write(f"[OK] 基本設計書を生成しました: {out_path}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
