# -*- coding: utf-8 -*-
"""
backlog-xlsx / create_evidence.py
エビデンス.xlsx を生成するスクリプト

Usage:
    python create_evidence.py <folder> <issue_id>

Arguments:
    folder    : 保存先フォルダパス
    issue_id  : 課題ID (例: GF-327)
"""

import os
import sys

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
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
    WHT  = Font(color="FFFFFF", bold=True)
    WRAP = Alignment(wrap_text=True, vertical="top")

    def col_header(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = HDR; c.font = WHT; c.alignment = WRAP

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # === Sheet1: テスト仕様 ===
    ws1 = wb.active; ws1.title = "テスト仕様"
    for col, w in zip("ABCDEFG", [6, 32, 15, 42, 42, 32, 18]):
        ws1.column_dimensions[col].width = w
    for i, h in enumerate(["No", "確認観点", "タイミング", "確認手順", "期待結果", "エビデンスの取り方", "貼付先シート"], 1):
        col_header(ws1, 1, i, h)

    # === Sheet2: 実装前エビデンス ===
    ws2 = wb.create_sheet("実装前エビデンス")
    for col, w in zip("ABCD", [5, 42, 20, 50]):
        ws2.column_dimensions[col].width = w
    for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
        col_header(ws2, 1, i, h)

    # === Sheet3: 実装後エビデンス ===
    ws3 = wb.create_sheet("実装後エビデンス")
    for col, w in zip("ABCD", [5, 42, 20, 50]):
        ws3.column_dimensions[col].width = w
    for i, h in enumerate(["□", "確認観点", "結果", "メモ（スクリーンショット貼付欄）"], 1):
        col_header(ws3, 1, i, h)

    path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
