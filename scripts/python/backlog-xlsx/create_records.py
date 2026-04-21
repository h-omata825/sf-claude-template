# -*- coding: utf-8 -*-
"""
backlog-xlsx / create_records.py
対応記録.xlsx を生成するスクリプト

Usage:
    python create_records.py --folder FOLDER --issue-id ID --title TITLE
                             --type TYPE --priority PRIORITY --deadline DEADLINE
                             --summary SUMMARY

Arguments:
    --folder     : 保存先フォルダパス
    --issue-id   : 課題ID (例: GF-327)
    --title      : 件名
    --type       : 課題種別 (バグ / 追加要望 / その他)
    --priority   : 優先度
    --deadline   : 期限 (YYYY-MM-DD or "未設定")
    --summary    : 背景・要件の要約（改行・特殊文字を含んでもよい）
"""

import argparse
import os
import sys

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="対応記録.xlsx を生成する")
    parser.add_argument("--folder",   required=True, help="保存先フォルダパス")
    parser.add_argument("--issue-id", required=True, dest="issue_id", help="課題ID (例: GF-327)")
    parser.add_argument("--title",    required=True, help="件名")
    parser.add_argument("--type",     required=True, dest="issue_type", help="課題種別")
    parser.add_argument("--priority", required=True, help="優先度")
    parser.add_argument("--deadline", required=True, help="期限 (YYYY-MM-DD or 未設定)")
    parser.add_argument("--summary",  required=True, help="背景・要件の要約")
    args = parser.parse_args()

    FOLDER      = args.folder
    ISSUE_ID    = args.issue_id
    ISSUE_TITLE = args.title
    ISSUE_TYPE  = args.issue_type
    PRIORITY    = args.priority
    DEADLINE    = args.deadline
    BG_DESC     = args.summary

    # --- スタイル定義 ---
    HDR  = PatternFill("solid", fgColor="1F3461")
    SEC  = PatternFill("solid", fgColor="2E74B5")
    WHT  = Font(color="FFFFFF", bold=True)
    BLD  = Font(bold=True)
    WRAP = Alignment(wrap_text=True, vertical="top")

    def sec_header(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = SEC; c.font = WHT; c.alignment = WRAP
        return c

    def col_header(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = HDR; c.font = WHT; c.alignment = WRAP
        return c

    def bold_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.font = BLD; c.alignment = WRAP
        return c

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # ==========================================================
    # Sheet1: サマリー・経緯
    # ==========================================================
    ws1 = wb.active; ws1.title = "サマリー・経緯"
    ws1.column_dimensions["A"].width = 22
    ws1.column_dimensions["B"].width = 60
    ws1.column_dimensions["C"].width = 12
    ws1.column_dimensions["D"].width = 18
    ws1.column_dimensions["E"].width = 60
    ws1.column_dimensions["F"].width = 40

    sec_header(ws1, 1, 1, "サマリー・経緯")
    sec_header(ws1, 2, 1, "■ 課題サマリー")

    info = [
        ("課題ID",    ISSUE_ID),
        ("件名",      ISSUE_TITLE),
        ("優先度・期限", f"優先度: {PRIORITY} / 期限: {DEADLINE}"),
        ("課題種別",  ISSUE_TYPE),
        ("ステータス", "対応中"),
        ("背景・要件", BG_DESC),
        ("最終対応サマリー", "（完了時に記入）"),
    ]
    r = 3
    for k, v in info:
        bold_cell(ws1, r, 1, k)
        ws1.cell(row=r, column=2, value=v).alignment = WRAP
        r += 1

    r += 1
    sec_header(ws1, r, 1, "■ 工数")
    r += 1
    for k in ["対応開始日時", "対応完了日時", "見積工数（CC使用）", "見積工数（CC未使用）", "実績工数（CC使用）", "削減効果"]:
        bold_cell(ws1, r, 1, k)
        r += 1

    r += 1
    sec_header(ws1, r, 1, "■ 対応経緯タイムライン")
    r += 1
    for i, h in enumerate(["No", "日時", "発生元", "フェーズ", "内容・決定事項", "変更・判断の理由"], 1):
        col_header(ws1, r, i, h)

    # ==========================================================
    # Sheet2: 対応方針
    # ==========================================================
    ws2 = wb.create_sheet("対応方針")
    ws2.column_dimensions["A"].width = 10
    for col, w in zip("BCDEFG", [22, 45, 32, 32, 22, 14]):
        ws2.column_dimensions[col].width = w

    sec_header(ws2, 1, 1, "対応方針")
    sec_header(ws2, 2, 1, "■ 方針比較テーブル")
    for i, h in enumerate(["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"], 1):
        col_header(ws2, 3, i, h)
    bold_cell(ws2, 4, 1, "A★")
    ws2.cell(row=5, column=1, value="（根拠）").alignment = WRAP
    bold_cell(ws2, 6, 1, "B")
    ws2.cell(row=7, column=1, value="（根拠）").alignment = WRAP

    sec_header(ws2, 9, 1, "■ 採用方針")
    ws2.cell(row=10, column=1, value="（方針確定後にここに採用理由を記録する）").alignment = WRAP

    sec_header(ws2, 12, 1, "■ 構成比較・差分記録（必要に応じて）")
    for i, h in enumerate(["要素", "既存（比較元）", "今回（実装対象）", "差分"], 1):
        col_header(ws2, 13, i, h)

    # ==========================================================
    # Sheet3: 調査・影響範囲
    # ==========================================================
    ws3 = wb.create_sheet("調査・影響範囲")
    for col, w in zip("ABCDE", [6, 35, 35, 45, 10]):
        ws3.column_dimensions[col].width = w

    sec_header(ws3, 1, 1, "調査・影響範囲")
    sec_header(ws3, 2, 1, "■ 仮説検証テーブル")
    for i, h in enumerate(["No", "仮説内容 / 種別", "検証方法", "検証結果・根拠", "判定"], 1):
        col_header(ws3, 3, i, h)

    # ==========================================================
    # Sheet4: 対応内容
    # ==========================================================
    ws4 = wb.create_sheet("対応内容")
    ws4.column_dimensions["A"].width = 28
    ws4.column_dimensions["B"].width = 55
    ws4.column_dimensions["C"].width = 15
    ws4.column_dimensions["D"].width = 50
    ws4.column_dimensions["E"].width = 50

    CHANGE_LIST_ROWS  = 6   # 変更ファイル一覧のデータ行数（余裕をもたせる）
    BEFORE_AFTER_ROWS = 3   # Before/After セクションの説明行数
    CHECKLIST_ROWS    = 7   # 影響確認チェックリストのデータ行数

    r4 = 1
    sec_header(ws4, r4, 1, "対応内容"); r4 += 1
    sec_header(ws4, r4, 1, "■ バックアップ情報（修正前に記録）"); r4 += 1
    bold_cell(ws4, r4, 1, "Git hash（修正前）")
    ws4.cell(row=r4, column=2, value="（実装前に記録: git rev-parse HEAD）"); r4 += 1
    bold_cell(ws4, r4, 1, "stash名")
    ws4.cell(row=r4, column=2, value="（stash使用時に記録）"); r4 += 1
    bold_cell(ws4, r4, 1, "巻き戻し方法")
    ws4.cell(row=r4, column=2, value="git reset --hard [hash] または git stash pop"); r4 += 2

    sec_header(ws4, r4, 1, "■ 変更ファイル一覧"); r4 += 1
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要"], 1):
        col_header(ws4, r4, i, h)
    r4 += 1 + CHANGE_LIST_ROWS  # ヘッダー行 + データ行分を確保

    sec_header(ws4, r4, 1, "■ Before / After（実装後に記入）"); r4 += 1
    ws4.cell(row=r4, column=1, value="実装完了後、各ファイルの変更前後を記載する").alignment = WRAP
    r4 += BEFORE_AFTER_ROWS

    sec_header(ws4, r4, 1, "■ 影響確認チェックリスト"); r4 += 1
    for i, h in enumerate(["□", "確認内容", "結果", "備考"], 1):
        col_header(ws4, r4, i, h)
    r4 += 1 + CHECKLIST_ROWS

    sec_header(ws4, r4, 1, "■ 追加修正（必要に応じて追記）"); r4 += 1
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要", "詳細・根拠"], 1):
        col_header(ws4, r4, i, h)

    # ==========================================================
    # Sheet5: テスト・検証記録
    # ==========================================================
    ws5 = wb.create_sheet("テスト・検証記録")
    for col, w in zip("ABCDEFGH", [6, 16, 32, 32, 32, 32, 10, 35]):
        ws5.column_dimensions[col].width = w

    sec_header(ws5, 1, 1, "テスト・検証記録")
    sec_header(ws5, 2, 1, "■ テスト方針")
    ws5.cell(row=3, column=1, value="（テスト方針・観点をここに記載する）").alignment = WRAP
    sec_header(ws5, 5, 1, "■ テスト結果")
    for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
        col_header(ws5, 6, i, h)

    # ==========================================================
    # Sheet6: リリース・ロールバック
    # ==========================================================
    ws6 = wb.create_sheet("リリース・ロールバック")
    for col, w in zip("ABCDEF", [6, 22, 35, 20, 32, 32]):
        ws6.column_dimensions[col].width = w

    RELEASE_LIST_ROWS    = 8  # リリース対象一覧のデータ行数
    ROLLBACK_DETAIL_ROWS = 3  # ロールバック手順の説明行数

    r6 = 1
    sec_header(ws6, r6, 1, "リリース・ロールバック"); r6 += 1
    sec_header(ws6, r6, 1, "■ リリース対象一覧"); r6 += 1
    for i, h in enumerate(["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"], 1):
        col_header(ws6, r6, i, h)
    r6 += 1 + RELEASE_LIST_ROWS

    sec_header(ws6, r6, 1, "■ ロールバック手順"); r6 += 1
    ws6.cell(row=r6, column=1, value="（ロールバックが必要な場合の手順を記載する）").alignment = WRAP
    r6 += ROLLBACK_DETAIL_ROWS

    sec_header(ws6, r6, 1, "■ 本番デプロイ記録"); r6 += 1
    for k in ["デプロイ日時", "実施者", "検証結果"]:
        bold_cell(ws6, r6, 1, k)
        r6 += 1

    path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
