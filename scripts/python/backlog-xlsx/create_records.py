# -*- coding: utf-8 -*-
"""backlog-xlsx / create_records.py
対応記録.xlsx を生成する（テンプレートコピー方式）

Usage:
    python create_records.py --folder FOLDER --issue-id ID --title TITLE
                             --type TYPE --priority PRIORITY --deadline DEADLINE
                             --summary SUMMARY
    # 後方互換: positional も受け付ける
    python create_records.py <folder> <issue_id> <title> <type> <priority> <deadline> <summary>
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)

TEMPLATE = Path(__file__).parent / "対応記録テンプレート.xlsx"

# ── テンプレート行番号定数（対応記録テンプレート.xlsx の構造から決定）──
# サマリー・経緯 — KV 値は col 2 にセット（テンプレート内で B:F マージ済み）
SUM_ISSUE_ID_ROW   = 3   # 課題ID
SUM_TITLE_ROW      = 4   # 件名
SUM_PRIORITY_ROW   = 5   # 優先度・期限
SUM_TYPE_ROW       = 6   # 課題種別
SUM_STATUS_ROW     = 7   # ステータス
SUM_BG_ROW         = 8   # 背景・要件
# r9: 最終対応サマリー（完了時に記入 — 初期は空のまま）

WRAP = Alignment(wrap_text=True, vertical="top")


def main():
    if len(sys.argv) >= 8 and not sys.argv[1].startswith("--"):
        FOLDER       = sys.argv[1]
        ISSUE_ID     = sys.argv[2]
        ISSUE_TITLE  = sys.argv[3]
        ISSUE_TYPE   = sys.argv[4]
        PRIORITY     = sys.argv[5]
        DEADLINE     = sys.argv[6]
        BG_DESC      = sys.argv[7]
    else:
        import argparse
        parser = argparse.ArgumentParser(description="対応記録.xlsx を生成する")
        parser.add_argument("--folder",   required=True)
        parser.add_argument("--issue-id", required=True, dest="issue_id")
        parser.add_argument("--title",    required=True)
        parser.add_argument("--type",     required=True)
        parser.add_argument("--priority", required=True)
        parser.add_argument("--deadline", required=True)
        parser.add_argument("--summary",  required=True)
        args = parser.parse_args()
        FOLDER       = args.folder
        ISSUE_ID     = args.issue_id
        ISSUE_TITLE  = args.title
        ISSUE_TYPE   = args.type
        PRIORITY     = args.priority
        DEADLINE     = args.deadline
        BG_DESC      = args.summary

    if not TEMPLATE.exists():
        print(f"[ERROR] テンプレートが見つかりません: {TEMPLATE}")
        sys.exit(1)

    os.makedirs(FOLDER, exist_ok=True)
    wb = load_workbook(TEMPLATE)

    ws = wb["サマリー・経緯"]
    ws.cell(SUM_ISSUE_ID_ROW,  2, value=ISSUE_ID).alignment   = WRAP
    ws.cell(SUM_TITLE_ROW,     2, value=ISSUE_TITLE).alignment = WRAP
    ws.cell(SUM_PRIORITY_ROW,  2,
            value=f"優先度: {PRIORITY} / 期限: {DEADLINE}").alignment = WRAP
    ws.cell(SUM_TYPE_ROW,      2, value=ISSUE_TYPE).alignment  = WRAP
    ws.cell(SUM_STATUS_ROW,    2, value="対応中").alignment     = WRAP
    ws.cell(SUM_BG_ROW,        2, value=BG_DESC).alignment     = WRAP

    path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
