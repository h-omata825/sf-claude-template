# -*- coding: utf-8 -*-
"""
backlog-xlsx / create_evidence.py
エビデンス.xlsx を生成するスクリプト (GF-327 テンプレート互換版)

Usage:
    python create_evidence.py <folder> <issue_id>
"""

import os
import sys

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_evidence.py <folder> <issue_id>")
        sys.exit(1)

    FOLDER   = sys.argv[1]
    ISSUE_ID = sys.argv[2]

    HDR  = PatternFill("solid", fgColor="1F3461")
    SEC  = PatternFill("solid", fgColor="2E74B5")
    WHT  = Font(color="FFFFFF", bold=True)
    WRAP = Alignment(wrap_text=True, vertical="top")

    def sec_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = SEC; c.font = WHT; c.alignment = WRAP
        return c

    def hdr_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = HDR; c.font = WHT; c.alignment = WRAP
        return c

    def val_cell(ws, row, col, val=""):
        c = ws.cell(row=row, column=col, value=val)
        c.alignment = WRAP
        return c

    def merge(ws, r1, c1, r2, c2):
        col1 = get_column_letter(c1)
        col2 = get_column_letter(c2)
        ws.merge_cells(f"{col1}{r1}:{col2}{r2}")

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # =========================================================
    # Sheet1: テスト仕様
    # =========================================================
    ws1 = wb.active; ws1.title = "テスト仕様"
    for col, w in zip("ABCDEFG", [6, 32, 15, 42, 42, 32, 18]):
        ws1.column_dimensions[col].width = w

    # r1: タイトル (A:G merged), r2: ヘッダー
    sec_cell(ws1, 1, 1, "テスト仕様"); merge(ws1, 1, 1, 1, 7)
    for i, h in enumerate(["No", "確認観点", "タイミング", "確認手順", "期待結果", "エビデンスの取り方", "貼付先シート"], 1):
        hdr_cell(ws1, 2, i, h)

    # =========================================================
    # Sheet2: 実装前エビデンス
    # =========================================================
    ws2 = wb.create_sheet("実装前エビデンス")
    for col, w in zip("ABCD", [5, 42, 20, 50]):
        ws2.column_dimensions[col].width = w

    # r1: タイトル (A:D merged)
    sec_cell(ws2, 1, 1, "実装前エビデンス"); merge(ws2, 1, 1, 1, 4)
    # r2: 説明 (A:D merged)
    val_cell(ws2, 2, 1,
             "テスト仕様シートの「実装前」「両方」の項目を実施し、エビデンスを貼り付けてください。")
    merge(ws2, 2, 1, 2, 4)

    # r3: blank
    # r4: チェックリスト見出し (A:D merged), r5: ヘッダー, r6-8: チェック行
    sec_cell(ws2, 4, 1, "■ 確認チェックリスト（実装前）"); merge(ws2, 4, 1, 4, 4)
    for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
        hdr_cell(ws2, 5, i, h)
    for r in range(6, 9):
        val_cell(ws2, r, 1, "□")

    # r9: エビデンス貼付欄見出し (A:D merged)
    sec_cell(ws2, 9, 1, "■ エビデンス貼付欄"); merge(ws2, 9, 1, 9, 4)
    # r10: エビデンス① テキスト
    val_cell(ws2, 10, 1, "エビデンス①: （スクリーンショットを貼り付けてください）")
    # r11-20: スクリーンショット貼付枠 (A:D merged, 10行)
    val_cell(ws2, 11, 1, "ここにスクリーンショットを貼り付けてください")
    merge(ws2, 11, 1, 20, 4)

    # r21: blank
    # r22: エビデンス② テキスト (A:D merged)
    val_cell(ws2, 22, 1, "エビデンス②: （スクリーンショットを貼り付けてください）")
    merge(ws2, 22, 1, 22, 4)
    # r23+: 貼付エリア (非merged、利用者が自由に拡張)

    # =========================================================
    # Sheet3: 実装後エビデンス
    # =========================================================
    ws3 = wb.create_sheet("実装後エビデンス")
    for col, w in zip("ABCD", [5, 42, 20, 50]):
        ws3.column_dimensions[col].width = w

    # r1: タイトル (A:D merged)
    sec_cell(ws3, 1, 1, "実装後エビデンス"); merge(ws3, 1, 1, 1, 4)
    # r2: 説明
    val_cell(ws3, 2, 1, "テスト仕様シートの「実装後」「両方」の項目を実施し、エビデンスを貼り付けてください。")

    # r3: blank
    # r4: チェックリスト見出し (A:D merged), r5: ヘッダー, r6-13: チェック行 (8行)
    sec_cell(ws3, 4, 1, "■ 確認チェックリスト（実装後）"); merge(ws3, 4, 1, 4, 4)
    for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
        hdr_cell(ws3, 5, i, h)
    for r in range(6, 14):
        val_cell(ws3, r, 1, "□")

    # r14: blank
    # r15: エビデンス① テキスト (A:D merged)
    val_cell(ws3, 15, 1, "エビデンス①: （スクリーンショットを貼り付けてください）")
    merge(ws3, 15, 1, 15, 4)
    # r16-25: 貼付枠 (A:D merged, 10行)
    val_cell(ws3, 16, 1, "ここにスクリーンショットを貼り付けてください")
    merge(ws3, 16, 1, 25, 4)

    # r26: blank
    # r27: エビデンス② テキスト (A:D merged)
    val_cell(ws3, 27, 1, "エビデンス②: （スクリーンショットを貼り付けてください）")
    merge(ws3, 27, 1, 27, 4)
    # r28-37: 貼付エリア (非merged)

    # r38: blank
    # r39: エビデンス③ テキスト (A:D merged)
    val_cell(ws3, 39, 1, "エビデンス③: （スクリーンショットを貼り付けてください）")
    merge(ws3, 39, 1, 39, 4)

    path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
