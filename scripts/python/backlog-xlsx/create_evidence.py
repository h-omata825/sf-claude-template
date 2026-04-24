# -*- coding: utf-8 -*-
"""backlog-xlsx / create_evidence.py
エビデンス.xlsx を生成する (GF-327 リッチ版スタイル準拠)

Usage:
    python create_evidence.py --folder FOLDER --issue-id ID
    # 後方互換: positional も受け付ける
    python create_evidence.py <folder> <issue_id>
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)

# ── スタイル定数 ────────────────────────────────────────────────
TITLE_FILL    = PatternFill("solid", fgColor="1F4E79")
SEC_FILL      = PatternFill("solid", fgColor="D6E4F0")
HDR_FILL      = PatternFill("solid", fgColor="2E75B6")
KEY_FILL      = PatternFill("solid", fgColor="F5F5F5")
WHT_FILL      = PatternFill("solid", fgColor="FFFFFF")
STRIPE_FILL   = PatternFill("solid", fgColor="F2F7FB")
NOTE_FILL     = PatternFill("solid", fgColor="FFF2CC")  # 黄: 説明・貼付欄
TIMING_BEFORE = PatternFill("solid", fgColor="DDEEFF")  # 実装前 = 薄青
TIMING_AFTER  = PatternFill("solid", fgColor="FFE4C0")  # 実装後 = 薄橙
TIMING_BOTH   = PatternFill("solid", fgColor="E2EFDA")  # 両方   = 薄緑

TITLE_FONT = Font(color="FFFFFF", bold=True, size=14)
SEC_FONT   = Font(bold=True, size=10)
HDR_FONT   = Font(color="FFFFFF", bold=True, size=10)
KEY_FONT   = Font(bold=True, size=10)
STD_FONT   = Font(size=10)

# GF-327 準拠 Alignment 定数
ALIGN_TITLE = Alignment(horizontal="center", vertical="center")
ALIGN_HDR   = Alignment(horizontal="center", vertical="center")
ALIGN_SEC   = Alignment(horizontal="left",   vertical="center")
ALIGN_KV    = Alignment(horizontal="left",   vertical="center")
ALIGN_LONG  = Alignment(horizontal="left",   vertical="center", wrap_text=True)
ALIGN_DATA  = Alignment(horizontal="left",   vertical="center", wrap_text=True)
ALIGN_CTR   = Alignment(horizontal="center", vertical="center")


def _merge_fill(ws, r, c1, c2, fill, font, val=""):
    cell = ws.cell(row=r, column=c1, value=val)
    cell.fill = fill
    cell.font = font
    if c2 > c1:
        ws.merge_cells(
            f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}"
        )
    return cell


def title_row(ws, r, last_col, text):
    cell = _merge_fill(ws, r, 1, last_col, TITLE_FILL, TITLE_FONT, text)
    cell.alignment = ALIGN_TITLE
    ws.row_dimensions[r].height = 38


def sec_row(ws, r, last_col, text):
    cell = _merge_fill(ws, r, 1, last_col, SEC_FILL, SEC_FONT, text)
    cell.alignment = ALIGN_SEC
    ws.row_dimensions[r].height = 28


def hdr_row(ws, r, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=r, column=i, value=h)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = ALIGN_HDR
    ws.row_dimensions[r].height = 28


def note_row(ws, r, last_col, text, height=45):
    """黄色の説明行（テスト仕様の注意事項等）"""
    cell = _merge_fill(ws, r, 1, last_col, NOTE_FILL, STD_FONT, text)
    cell.alignment = ALIGN_LONG
    ws.row_dimensions[r].height = height


def key_label(ws, r, last_col, text):
    """貼付欄の見出しラベル行 (KEY_FILL)"""
    cell = _merge_fill(ws, r, 1, last_col, KEY_FILL, KEY_FONT, text)
    cell.alignment = ALIGN_KV
    ws.row_dimensions[r].height = 25


def data_row(ws, r, cells, stripe=False, height=45):
    fill = STRIPE_FILL if stripe else WHT_FILL
    for i, val in enumerate(cells, 1):
        c = ws.cell(row=r, column=i, value=val)
        c.fill = fill
        c.font = STD_FONT
        c.alignment = ALIGN_DATA
    ws.row_dimensions[r].height = height


def data_row_with_timing(ws, r, cells, stripe=False, height=45):
    """テスト仕様用: タイミング列（C列=index 2）を色分けする"""
    data_row(ws, r, cells, stripe=stripe, height=height)
    timing = cells[2].strip() if len(cells) > 2 and cells[2] else ""
    c = ws.cell(row=r, column=3)
    if timing == "実装前":
        c.fill = TIMING_BEFORE
    elif timing == "実装後":
        c.fill = TIMING_AFTER
    elif timing == "両方":
        c.fill = TIMING_BOTH


def check_row(ws, r, cells, stripe=False):
    fill = STRIPE_FILL if stripe else WHT_FILL
    for i, val in enumerate(cells, 1):
        c = ws.cell(row=r, column=i, value=val)
        c.fill = fill
        c.font = STD_FONT
        c.alignment = ALIGN_CTR if i == 1 else ALIGN_DATA
    ws.row_dimensions[r].height = 25


def spacer(ws, r):
    ws.row_dimensions[r].height = 8


def _paste_block(ws, r, last_col, label, placeholder, block_rows=10):
    """エビデンス貼付欄: ラベル + 黄色プレースホルダ + マージ余白"""
    key_label(ws, r, last_col, label);  r += 1
    # 黄色プレースホルダ（1行目: center/center）
    cell = ws.cell(row=r, column=1, value=placeholder)
    cell.fill = NOTE_FILL
    cell.font = STD_FONT
    cell.alignment = ALIGN_CTR
    ws.row_dimensions[r].height = 30
    # block_rows 行まとめてマージ
    ws.merge_cells(
        f"A{r}:{get_column_letter(last_col)}{r + block_rows - 1}"
    )
    for row_i in range(r, r + block_rows):
        ws.row_dimensions[row_i].height = 30
    return r + block_rows  # 次の空き行


def main():
    # CLI: --folder/--issue-id (argparse) または positional 2 引数の後方互換
    if len(sys.argv) >= 3 and not sys.argv[1].startswith("--"):
        FOLDER   = sys.argv[1]
        ISSUE_ID = sys.argv[2]
    else:
        import argparse
        parser = argparse.ArgumentParser(description="エビデンス.xlsx を生成する")
        parser.add_argument("--folder",   required=True)
        parser.add_argument("--issue-id", required=True, dest="issue_id")
        args = parser.parse_args()
        FOLDER   = args.folder
        ISSUE_ID = args.issue_id

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # ================================================================
    # Sheet1: テスト仕様
    # ================================================================
    ws1 = wb.active
    ws1.title = "テスト仕様"
    for col, w in zip("ABCDEFG", [6, 40, 15, 50, 40, 35, 20]):
        ws1.column_dimensions[col].width = w

    r = 1
    title_row(ws1, r, 7, "テスト仕様");  r += 1
    hdr_row(ws1, r, ["No", "確認観点", "タイミング", "確認手順",
                     "期待結果", "エビデンスの取り方", "貼付先シート"]); r += 1
    for i in range(9):
        data_row_with_timing(ws1, r, ["", "", "", "", "", "", ""],
                             stripe=(i % 2 == 1), height=45);     r += 1

    # ================================================================
    # Sheet2: 実装前エビデンス
    # ================================================================
    ws2 = wb.create_sheet("実装前エビデンス")
    for col, w in zip("ABCD", [6, 50, 12, 40]):
        ws2.column_dimensions[col].width = w

    r = 1
    title_row(ws2, r, 4, "実装前エビデンス");                      r += 1
    note_row(ws2, r, 4,
             "テスト仕様シートの「実装前」「両方」の項目を実施し、"
             "エビデンスを貼り付けてください。",
             height=45);                                           r += 1
    spacer(ws2, r);                                                r += 1
    sec_row(ws2, r, 4, "■ 確認チェックリスト（実装前）");          r += 1
    hdr_row(ws2, r, ["□", "確認観点", "結果", "メモ"]);           r += 1
    for i in range(3):
        check_row(ws2, r, ["□", "", "", ""],
                  stripe=(i % 2 == 1));                            r += 1
    spacer(ws2, r);                                                r += 1
    sec_row(ws2, r, 4, "■ エビデンス貼付欄");                      r += 1
    r = _paste_block(ws2, r, 4,
                     "エビデンス①: 実装前スクリーンショット",
                     "ここにスクリーンショットを貼り付けてください")
    spacer(ws2, r);                                                r += 1
    r = _paste_block(ws2, r, 4,
                     "エビデンス②: （必要に応じて追加）",
                     "ここにスクリーンショットを貼り付けてください")

    # ================================================================
    # Sheet3: 実装後エビデンス
    # ================================================================
    ws3 = wb.create_sheet("実装後エビデンス")
    for col, w in zip("ABCD", [6, 50, 12, 40]):
        ws3.column_dimensions[col].width = w

    r = 1
    title_row(ws3, r, 4, "実装後エビデンス");                      r += 1
    note_row(ws3, r, 4,
             "テスト仕様シートの「実装後」「両方」の項目を実施し、"
             "エビデンスを貼り付けてください。",
             height=45);                                           r += 1
    spacer(ws3, r);                                                r += 1
    sec_row(ws3, r, 4, "■ 確認チェックリスト（実装後）");          r += 1
    hdr_row(ws3, r, ["□", "確認観点", "結果", "メモ"]);           r += 1
    for i in range(5):
        check_row(ws3, r, ["□", "", "", ""],
                  stripe=(i % 2 == 1));                            r += 1
    spacer(ws3, r);                                                r += 1
    sec_row(ws3, r, 4, "■ エビデンス貼付欄");                      r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス①: 実装後スクリーンショット",
                     "ここにスクリーンショットを貼り付けてください")
    spacer(ws3, r);                                                r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス②: 追加確認",
                     "ここにスクリーンショットを貼り付けてください")
    spacer(ws3, r);                                                r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス③: （必要に応じて追加）",
                     "ここにスクリーンショットを貼り付けてください")

    path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
