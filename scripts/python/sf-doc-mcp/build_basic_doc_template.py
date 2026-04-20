"""
プロジェクト概要書テンプレート Excel を生成する。

5シート構成:
  1. 改版履歴      : 基本情報 + 改版履歴テーブル
  2. プロジェクト概要: 名称・目的・期間・組織情報・利用ユーザー
  3. システム構成   : SF Edition・外部連携一覧・エンドポイント
  4. オブジェクト構成: 主要オブジェクト一覧・ER図（テキスト版）
  5. 業務フロー概要 : ユースケース一覧

方針:
  - 既存設計書と同じデザインシステム（狭幅グリッド + セル結合 + 罫線統一）
  - グリッド: col A=2.0、col 2〜31=4.2（30列）
  - 色: 1F3864（タイトル濃紺）/ 2E75B6（ヘッダ青）/ 0070C0（セクション帯）/ D9E1F2（ラベル薄青）

Usage:
  python build_basic_doc_template.py --output "C:/.../プロジェクト概要書テンプレート.xlsx"
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
def B_med():
    return Border(left=MED, right=MED, top=MED, bottom=MED)

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

GRID_LEFT  = 2
GRID_RIGHT = 31
COL_W      = 4.2

def setup_grid(ws):
    set_w(ws, "A", 2.0)
    for i in range(GRID_LEFT, GRID_RIGHT + 1):
        set_w(ws, get_column_letter(i), COL_W)
    ws.sheet_view.showGridLines = False

def title_row(ws, row, text):
    """濃紺タイトルバー（全幅結合）"""
    MW(ws, row, GRID_LEFT, GRID_RIGHT, text,
       bold=True, fg=C_FONT_W, bg=C_TITLE_DARK,
       h="center", size=14, border=B_med())
    set_h(ws, row, 28)

def section_row(ws, row, text):
    """青セクション帯（全幅結合）"""
    MW(ws, row, GRID_LEFT, GRID_RIGHT, text,
       bold=True, fg=C_FONT_W, bg=C_BAND_BLUE,
       border=B_all())
    set_h(ws, row, 18)

def meta_row(ws, row, label, col_label_end=8, col_val_end=31, value=""):
    """ラベル＋値の1行メタ情報"""
    MW(ws, row, GRID_LEFT, col_label_end, label,
       bold=True, bg=C_LABEL_BG, border=B_all())
    MW(ws, row, col_label_end + 1, col_val_end, value, border=B_all())
    set_h(ws, row, 16)

def hdr_row(ws, row, cols: list[tuple[int, int, str]]):
    """テーブルヘッダ行: [(cs, ce, label), ...]"""
    for cs, ce, label in cols:
        MW(ws, row, cs, ce, label,
           bold=True, fg=C_FONT_W, bg=C_HDR_BLUE,
           h="center", border=B_all())
    set_h(ws, row, 18)

def data_rows(ws, row_start, count, cols: list[tuple[int, int]]):
    """空データ行を count 行分生成"""
    for r in range(row_start, row_start + count):
        for cs, ce in cols:
            for c in range(cs, ce + 1):
                ws.cell(row=r, column=c).border = B_all()
            ws.merge_cells(start_row=r, start_column=cs, end_row=r, end_column=ce)
        set_h(ws, r, 16)


# ── シート 1: 改版履歴 ─────────────────────────────────────────
def build_revision_sheet(ws):
    setup_grid(ws)
    r = 1
    set_h(ws, r, 8); r += 1  # margin

    title_row(ws, r, "プロジェクト概要書"); r += 1
    set_h(ws, r, 6); r += 1

    meta_row(ws, r, "プロジェクト名", value=""); r += 1
    meta_row(ws, r, "作成日",        value=""); r += 1
    meta_row(ws, r, "最終更新日",    value=""); r += 1
    meta_row(ws, r, "バージョン",    value="1.0"); r += 1
    meta_row(ws, r, "作成者",        value=""); r += 1
    set_h(ws, r, 6); r += 1

    section_row(ws, r, "改版履歴"); r += 1
    hdr_row(ws, r, [
        (2, 3, "版"),
        (4, 7, "改版日"),
        (8, 12, "改版者"),
        (13, 31, "改版内容"),
    ]); r += 1
    data_rows(ws, r, 10, [(2, 3), (4, 7), (8, 12), (13, 31)])


# ── シート 2: プロジェクト概要 ─────────────────────────────────
def build_overview_sheet(ws):
    setup_grid(ws)
    r = 1
    set_h(ws, r, 8); r += 1

    title_row(ws, r, "プロジェクト概要"); r += 1
    set_h(ws, r, 6); r += 1

    section_row(ws, r, "基本情報"); r += 1
    for label in ["システム名", "プロジェクト名", "目的・背景", "対象業務",
                  "Salesforce Edition", "開始日", "終了予定日", "本番公開日"]:
        meta_row(ws, r, label); r += 1

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "利用ユーザー"); r += 1
    hdr_row(ws, r, [
        (2, 8,  "ユーザー区分"),
        (9, 16, "プロファイル / 権限セット"),
        (17, 22, "想定人数"),
        (23, 31, "主な利用機能"),
    ]); r += 1
    data_rows(ws, r, 8, [(2, 8), (9, 16), (17, 22), (23, 31)]); r += 8

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "関係者"); r += 1
    hdr_row(ws, r, [
        (2, 8,  "役割"),
        (9, 18, "氏名 / 組織"),
        (19, 31, "備考"),
    ]); r += 1
    data_rows(ws, r, 5, [(2, 8), (9, 18), (19, 31)])


# ── シート 3: システム構成 ─────────────────────────────────────
def build_system_sheet(ws):
    setup_grid(ws)
    r = 1
    set_h(ws, r, 8); r += 1

    title_row(ws, r, "システム構成"); r += 1
    set_h(ws, r, 6); r += 1

    section_row(ws, r, "Salesforce 組織情報"); r += 1
    for label in ["組織ID", "インスタンスURL", "Edition", "APIバージョン", "接続ユーザー"]:
        meta_row(ws, r, label); r += 1

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "外部連携一覧"); r += 1
    hdr_row(ws, r, [
        (2, 8,  "連携先システム"),
        (9, 14, "方向"),
        (15, 20, "方式"),
        (21, 24, "頻度"),
        (25, 31, "目的・概要"),
    ]); r += 1
    data_rows(ws, r, 10, [(2, 8), (9, 14), (15, 20), (21, 24), (25, 31)]); r += 10

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "エンドポイント（Named Credential）"); r += 1
    hdr_row(ws, r, [
        (2, 10, "DeveloperName"),
        (11, 31, "Endpoint URL"),
    ]); r += 1
    data_rows(ws, r, 6, [(2, 10), (11, 31)])


# ── シート 4: オブジェクト構成 ────────────────────────────────
def build_object_sheet(ws):
    setup_grid(ws)
    r = 1
    set_h(ws, r, 8); r += 1

    title_row(ws, r, "オブジェクト構成"); r += 1
    set_h(ws, r, 6); r += 1

    section_row(ws, r, "主要オブジェクト一覧"); r += 1
    hdr_row(ws, r, [
        (2, 6,  "API名"),
        (7, 14, "オブジェクト名（日本語）"),
        (15, 18, "種別"),
        (19, 23, "件数（概算）"),
        (24, 31, "概要・用途"),
    ]); r += 1
    data_rows(ws, r, 20, [(2, 6), (7, 14), (15, 18), (19, 23), (24, 31)]); r += 20

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "主要リレーション"); r += 1
    hdr_row(ws, r, [
        (2, 8,  "親オブジェクト"),
        (9, 10, "関係"),
        (11, 17, "子オブジェクト"),
        (18, 31, "項目名（参照関係項目）"),
    ]); r += 1
    data_rows(ws, r, 10, [(2, 8), (9, 10), (11, 17), (18, 31)])


# ── シート 5: 業務フロー概要 ──────────────────────────────────
def build_flow_sheet(ws):
    setup_grid(ws)
    r = 1
    set_h(ws, r, 8); r += 1

    title_row(ws, r, "業務フロー概要（ユースケース一覧）"); r += 1
    set_h(ws, r, 6); r += 1

    section_row(ws, r, "ユースケース一覧"); r += 1
    hdr_row(ws, r, [
        (2, 5,   "UC番号"),
        (6, 14,  "ユースケース名"),
        (15, 19, "トリガー"),
        (20, 23, "頻度"),
        (24, 31, "主要オブジェクト / 備考"),
    ]); r += 1
    data_rows(ws, r, 15, [(2, 5), (6, 14), (15, 19), (20, 23), (24, 31)]); r += 15

    set_h(ws, r, 6); r += 1
    section_row(ws, r, "備考・全体方針"); r += 1
    MW(ws, r, GRID_LEFT, GRID_RIGHT, "", border=B_all())
    for i in range(r, r + 5):
        set_h(ws, i, 16)
        for c in range(GRID_LEFT, GRID_RIGHT + 1):
            ws.cell(row=i, column=c).border = B_all()
    ws.merge_cells(start_row=r, start_column=GRID_LEFT,
                   end_row=r + 4, end_column=GRID_RIGHT)


# ── メイン ────────────────────────────────────────────────────
def build(output: Path):
    wb = Workbook()
    wb.remove(wb.active)

    sheets = [
        ("改版履歴",       build_revision_sheet),
        ("プロジェクト概要", build_overview_sheet),
        ("システム構成",   build_system_sheet),
        ("オブジェクト構成", build_object_sheet),
        ("業務フロー概要", build_flow_sheet),
    ]
    for name, builder in sheets:
        ws = wb.create_sheet(name)
        builder(ws)

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    print(f"saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(
        Path(__file__).parent / "プロジェクト概要書テンプレート.xlsx"))
    args = parser.parse_args()
    build(Path(args.output))
