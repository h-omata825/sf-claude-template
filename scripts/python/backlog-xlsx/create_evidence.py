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
TITLE_FILL  = PatternFill("solid", fgColor="1F4E79")
SEC_FILL    = PatternFill("solid", fgColor="D6E4F0")
HDR_FILL    = PatternFill("solid", fgColor="2E75B6")
KEY_FILL    = PatternFill("solid", fgColor="F5F5F5")
WHT_FILL    = PatternFill("solid", fgColor="FFFFFF")
STRIPE_FILL = PatternFill("solid", fgColor="F2F7FB")
NOTE_FILL   = PatternFill("solid", fgColor="FFF2CC")  # 黄: 説明・貼付欄

TITLE_FONT  = Font(color="FFFFFF", bold=True, size=14)
SEC_FONT    = Font(bold=True, size=10)
HDR_FONT    = Font(color="FFFFFF", bold=True, size=10)
KEY_FONT    = Font(bold=True, size=10)
STD_FONT    = Font(size=10)

WRAP = Alignment(wrap_text=True, vertical="top")


def _merge_fill(ws, r, c1, c2, fill, font, val=""):
    cell = ws.cell(row=r, column=c1, value=val)
    cell.fill  = fill
    cell.font  = font
    cell.alignment = WRAP
    if c2 > c1:
        ws.merge_cells(
            f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}"
        )
    return cell


def title_row(ws, r, last_col, text):
    _merge_fill(ws, r, 1, last_col, TITLE_FILL, TITLE_FONT, text)


def sec_row(ws, r, last_col, text):
    _merge_fill(ws, r, 1, last_col, SEC_FILL, SEC_FONT, text)


def hdr_row(ws, r, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=r, column=i, value=h)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = WRAP


def note_row(ws, r, last_col, text):
    """黄色の説明/貼付欄ブロック (merge で大きく取る)"""
    _merge_fill(ws, r, 1, last_col, NOTE_FILL, STD_FONT, text)


def key_label(ws, r, last_col, text):
    """KEY_FILL の太字ラベル行 (貼付欄の見出し)"""
    _merge_fill(ws, r, 1, last_col, KEY_FILL, KEY_FONT, text)


def data_row(ws, r, cells, stripe=False):
    fill = STRIPE_FILL if stripe else WHT_FILL
    for i, val in enumerate(cells, 1):
        c = ws.cell(row=r, column=i, value=val)
        c.fill = fill
        c.font = STD_FONT
        c.alignment = WRAP


def _paste_block(ws, r, last_col, label, placeholder,
                 block_rows=10):
    """エビデンス貼付欄1ブロック (ラベル + 大きなNOTEエリア)"""
    key_label(ws, r, last_col, label);  r += 1
    # NOTE_FILL で block_rows 行を縦マージ
    cell = ws.cell(row=r, column=1, value=placeholder)
    cell.fill = NOTE_FILL
    cell.font = STD_FONT
    cell.alignment = WRAP
    ws.merge_cells(
        f"A{r}:{get_column_letter(last_col)}{r + block_rows - 1}"
    )
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
                     "期待結果", "エビデンスの取り方", "貼付先シート"])

    # ================================================================
    # Sheet2: 実装前エビデンス
    # ================================================================
    ws2 = wb.create_sheet("実装前エビデンス")
    for col, w in zip("ABCD", [6, 50, 12, 40]):
        ws2.column_dimensions[col].width = w

    r = 1
    title_row(ws2, r, 4, "実装前エビデンス");  r += 1
    note_row(ws2, r, 4,
             "テスト仕様シートの「実装前」「両方」の項目を実施し、"
             "エビデンスを貼り付けてください。");  r += 1
    r += 1  # 空行
    sec_row(ws2, r, 4, "■ 確認チェックリスト（実装前）");  r += 1
    hdr_row(ws2, r, ["□", "確認観点", "結果", "メモ"]);  r += 1
    for i in range(3):
        data_row(ws2, r, ["□", "", "", ""], stripe=(i % 2 == 1));  r += 1
    r += 1  # 空行
    sec_row(ws2, r, 4, "■ エビデンス貼付欄");  r += 1
    r = _paste_block(ws2, r, 4,
                     "エビデンス①: 実装前スクリーンショット",
                     "ここにスクリーンショットを貼り付けてください")
    r += 1
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
    title_row(ws3, r, 4, "実装後エビデンス");  r += 1
    note_row(ws3, r, 4,
             "テスト仕様シートの「実装後」「両方」の項目を実施し、"
             "エビデンスを貼り付けてください。");  r += 1
    r += 1  # 空行
    sec_row(ws3, r, 4, "■ 確認チェックリスト（実装後）");  r += 1
    hdr_row(ws3, r, ["□", "確認観点", "結果", "メモ"]);  r += 1
    for i in range(5):
        data_row(ws3, r, ["□", "", "", ""], stripe=(i % 2 == 1));  r += 1
    r += 1  # 空行
    sec_row(ws3, r, 4, "■ エビデンス貼付欄");  r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス①: 実装後スクリーンショット",
                     "ここにスクリーンショットを貼り付けてください")
    r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス②: 追加確認",
                     "ここにスクリーンショットを貼り付けてください")
    r += 1
    r = _paste_block(ws3, r, 4,
                     "エビデンス③: （必要に応じて追加）",
                     "ここにスクリーンショットを貼り付けてください")

    path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
