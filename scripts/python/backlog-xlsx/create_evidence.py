# -*- coding: utf-8 -*-
"""backlog-xlsx / create_evidence.py
エビデンス.xlsx を生成する（テンプレートコピー方式）

Usage:
    python create_evidence.py --folder FOLDER --issue-id ID
    # 後方互換: positional も受け付ける
    python create_evidence.py <folder> <issue_id>
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

try:
    from openpyxl import load_workbook
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)

TEMPLATE = Path(__file__).parent / "エビデンステンプレート.xlsx"


def main():
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

    if not TEMPLATE.exists():
        print(f"[ERROR] テンプレートが見つかりません: {TEMPLATE}")
        sys.exit(1)

    os.makedirs(FOLDER, exist_ok=True)
    wb = load_workbook(TEMPLATE)

    path = os.path.join(FOLDER, f"{ISSUE_ID}_エビデンス.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
