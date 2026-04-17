"""
詳細設計書テンプレート Excel を生成する。

5シート構成:
  1. 改版履歴                 : 基本情報 + 改版履歴テーブル
  2. グループ詳細             : 処理目的 / データ連携概要 / 前提条件
  3. コンポーネント仕様       : 担当処理 / 入力 / 出力 / エラー処理
  4. インターフェース定義     : メソッド/API名 / パラメータ / 返却値 / 例外
  5. 画面仕様                 : 画面項目 / UI種別 / 型 / 必須 / バリデーション

方針:
  - 設計書テンプレートと同じデザインシステム（狭幅グリッド + セル結合 + 罫線統一）
  - グリッド: col A=2.0、col 2〜31=4.2（30列）

Usage:
  python build_detail_design_template.py --output "C:/.../詳細設計書テンプレート.xlsx"
"""
from __future__ import annotations
import argparse
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ── カラー ──────────────────────────────────────────────────────
C_TITLE_DARK = "1F3864"
C_HDR_BLUE   = "2E75B6"
C_BAND_BLUE  = "0070C0"
C_LABEL_BG   = "D9E1F2"
C_FONT_W     = "FFFFFF"
C_FONT_D     = "000000"

THIN = Side(style="thin",   color="8B9DC3")
MED  = Side(style="medium", color="1F3864")

# ── ヘルパー ───────────────────────────────────────────────────
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

def set_h(ws, row, h): ws.row_dimensions[row].height = h
def set_w(ws, letter, w): ws.column_dimensions[letter].width = w

# ── 共通グリッド ───────────────────────────────────────────────
GRID_LEFT  = 2
GRID_RIGHT = 31

def setup_grid(ws):
    set_w(ws, "A", 2.0)
    for i in range(GRID_LEFT, GRID_RIGHT + 1):
        set_w(ws, get_column_letter(i), 4.2)
    ws.sheet_view.showGridLines = False

def title_band(ws, row, text, height=36):
    set_h(ws, row, height)
    MW(ws, row, GRID_LEFT, GRID_RIGHT, text,
       bold=True, fg=C_FONT_W, bg=C_TITLE_DARK, h="center", size=14)

def section_band(ws, row, text, height=26, cs=None, ce=None):
    cs = cs if cs is not None else GRID_LEFT
    ce = ce if ce is not None else GRID_RIGHT
    set_h(ws, row, height)
    MW(ws, row, cs, ce, text,
       bold=True, fg=C_FONT_W, bg=C_BAND_BLUE, size=11)

def table_header(ws, row, cols: list[tuple], height=26):
    """cols: [(cs, ce, label), ...]"""
    set_h(ws, row, height)
    for cs, ce, label in cols:
        MW(ws, row, cs, ce, label,
           bold=True, fg=C_FONT_W, bg=C_HDR_BLUE, h="center", border=B_all())

def data_rows(ws, row_start, row_end, col_groups: list[tuple], row_h=22):
    for r in range(row_start, row_end + 1):
        set_h(ws, r, row_h)
        for cs, ce in col_groups:
            MW(ws, r, cs, ce, "", border=B_all())

def label_row(ws, row, label, label_cs=2, label_ce=6, val_cs=7, val_ce=31, height=22):
    set_h(ws, row, height)
    MW(ws, row, label_cs, label_ce, label,
       bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, row, val_cs, val_ce, "", border=B_all())


# ─────────────────────────────────────────────────────────────
# Sheet 1: 改版履歴
# ─────────────────────────────────────────────────────────────
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

def build_revision(wb):
    ws = wb.active
    ws.title = "改版履歴"
    setup_grid(ws)

    title_band(ws, 1, "改版履歴")
    set_h(ws, 2, 6)

    set_h(ws, 3, 22)
    MW(ws, 3, 2, 5,  "プロジェクト名", bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 6, 18, "", border=B_all())
    MW(ws, 3, 19, 22, "作成日",        bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 23, 31, "", border=B_all())

    set_h(ws, 4, 8)
    table_header(ws, 5, [(cs, ce, label) for label, (cs, ce) in REV_COLS.items()])
    data_rows(ws, 6, 25, [(cs, ce) for cs, ce in REV_COLS.values()])


# ─────────────────────────────────────────────────────────────
# Sheet 2: グループ詳細
# ─────────────────────────────────────────────────────────────
def build_group_detail(wb):
    ws = wb.create_sheet("グループ詳細")
    setup_grid(ws)

    title_band(ws, 1, "詳細設計書 — グループ詳細")
    set_h(ws, 2, 6)

    # メタ 1段目
    set_h(ws, 3, 22)
    MW(ws, 3, 2,  5,  "プロジェクト名", bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 6,  16, "", border=B_all())
    MW(ws, 3, 17, 20, "グループID",    bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 21, 24, "", border=B_all())
    MW(ws, 3, 25, 27, "作成者",        bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 28, 29, "", border=B_all())
    MW(ws, 3, 30, 30, "版数",          bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 3, 31, 31, "", border=B_all())

    # メタ 2段目
    set_h(ws, 4, 22)
    MW(ws, 4, 2,  5,  "グループ名",    bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 4, 6,  24, "", border=B_all())
    MW(ws, 4, 25, 27, "作成日",        bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
    MW(ws, 4, 28, 31, "", border=B_all())

    set_h(ws, 5, 10)

    # セクション1: 処理目的
    section_band(ws, 6, "■ 1. 処理目的")
    label_row(ws, 7, "処理目的", height=44)

    set_h(ws, 8, 10)

    # セクション2: データ連携概要
    section_band(ws, 9, "■ 2. データ連携概要")
    label_row(ws, 10, "概要", height=44)

    set_h(ws, 11, 10)

    # セクション3: 前提条件・備考
    section_band(ws, 12, "■ 3. 前提条件・備考")
    label_row(ws, 13, "前提条件", height=36)
    label_row(ws, 14, "備考",     height=30)


# ─────────────────────────────────────────────────────────────
# Sheet 3: コンポーネント仕様
# ─────────────────────────────────────────────────────────────
# | コンポーネント名 | 種別 | 担当処理 | 入力 | 出力 | エラー処理 |
CM_COLS = [
    (2,  8,  "コンポーネント名"),
    (9,  11, "種別"),
    (12, 20, "担当処理"),
    (21, 24, "入力"),
    (25, 28, "出力"),
    (29, 31, "エラー処理"),
]

def build_component_spec(wb):
    ws = wb.create_sheet("コンポーネント仕様")
    setup_grid(ws)

    title_band(ws, 1, "詳細設計書 — コンポーネント仕様")
    set_h(ws, 2, 6)

    section_band(ws, 3, "■ コンポーネント仕様")
    table_header(ws, 4, CM_COLS)
    data_rows(ws, 5, 19, [(cs, ce) for cs, ce, _ in CM_COLS], row_h=36)


# ─────────────────────────────────────────────────────────────
# Sheet 4: インターフェース定義
# ─────────────────────────────────────────────────────────────
# | コンポーネント | メソッド/API名 | 処理内容 | 入力パラメータ | 返却値 | 例外 |
IF_COLS = [
    (2,  6,  "コンポーネント"),
    (7,  12, "メソッド/API名"),
    (13, 19, "処理内容"),
    (20, 25, "入力パラメータ"),
    (26, 29, "返却値"),
    (30, 31, "例外"),
]

def build_interface_def(wb):
    ws = wb.create_sheet("インターフェース定義")
    setup_grid(ws)

    title_band(ws, 1, "詳細設計書 — インターフェース定義")
    set_h(ws, 2, 6)

    section_band(ws, 3, "■ インターフェース定義")
    table_header(ws, 4, IF_COLS)
    data_rows(ws, 5, 24, [(cs, ce) for cs, ce, _ in IF_COLS], row_h=36)


# ─────────────────────────────────────────────────────────────
# Sheet 5: 画面仕様
# ─────────────────────────────────────────────────────────────
# | No | 項目名 | API名/プロパティ | UI種別 | 型 | 必須 | 初期値 | バリデーション |
SC_COLS = [
    (2,  3,  "No"),
    (4,  8,  "項目名"),
    (9,  14, "API名/プロパティ"),
    (15, 17, "UI種別"),
    (18, 19, "型"),
    (20, 21, "必須"),
    (22, 24, "初期値"),
    (25, 31, "バリデーション"),
]

def build_screen_spec(wb):
    ws = wb.create_sheet("画面仕様")
    setup_grid(ws)

    title_band(ws, 1, "詳細設計書 — 画面仕様")
    set_h(ws, 2, 6)

    # 画面名セクション（generate 側で画面ごとに追記）
    section_band(ws, 3, "■ {画面名}")
    table_header(ws, 4, SC_COLS)
    data_rows(ws, 5, 19, [(cs, ce) for cs, ce, _ in SC_COLS])


# ─────────────────────────────────────────────────────────────
# エントリポイント
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="出力先 xlsx パス")
    args = parser.parse_args()

    wb = Workbook()
    build_revision(wb)
    build_group_detail(wb)
    build_component_spec(wb)
    build_interface_def(wb)
    build_screen_spec(wb)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(out))
    print(f"詳細設計書テンプレート生成完了: {out}")


if __name__ == "__main__":
    main()
