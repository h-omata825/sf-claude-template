# -*- coding: utf-8 -*-
"""
backlog-xlsx / create_records.py
対応記録.xlsx を生成するスクリプト (GF-327 テンプレート互換版)

Usage:
    python create_records.py --folder FOLDER --issue-id ID --title TITLE
                             --type TYPE --priority PRIORITY --deadline DEADLINE
                             --summary SUMMARY
"""

import argparse
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
    HDR  = PatternFill("solid", fgColor="1F3461")   # 紺（列ヘッダー）
    SEC  = PatternFill("solid", fgColor="2E74B5")   # 青（セクション見出し）
    WHT  = Font(color="FFFFFF", bold=True)
    BLD  = Font(bold=True)
    WRAP = Alignment(wrap_text=True, vertical="top")

    def sec_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = SEC; c.font = WHT; c.alignment = WRAP
        return c

    def hdr_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.fill = HDR; c.font = WHT; c.alignment = WRAP
        return c

    def bold_cell(ws, row, col, val):
        c = ws.cell(row=row, column=col, value=val)
        c.font = BLD; c.alignment = WRAP
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

    # r1: タイトル, r2: セクション見出し (A:F merged)
    sec_cell(ws1, 1, 1, "サマリー・経緯"); merge(ws1, 1, 1, 1, 6)
    sec_cell(ws1, 2, 1, "■ 課題サマリー"); merge(ws1, 2, 1, 2, 6)

    # r3-9: 課題サマリー 7行 (A=ラベル bold, B:F merged value)
    summary_rows = [
        ("課題ID",           ISSUE_ID),
        ("件名",             ISSUE_TITLE),
        ("優先度・期限",     f"優先度: {PRIORITY} / 期限: {DEADLINE}"),
        ("課題種別",         ISSUE_TYPE),
        ("ステータス",       "対応中"),
        ("背景・要件",       BG_DESC),
        ("最終対応サマリー", "（完了時に記入）"),
    ]
    for i, (k, v) in enumerate(summary_rows, start=3):
        bold_cell(ws1, i, 1, k)
        val_cell(ws1, i, 2, v)
        merge(ws1, i, 2, i, 6)

    # r10: blank
    # r11: タイムライン見出し, r12: カラムヘッダー
    sec_cell(ws1, 11, 1, "■ 対応経緯タイムライン"); merge(ws1, 11, 1, 11, 6)
    for i, h in enumerate(["No", "日時", "発生元", "フェーズ", "内容・決定事項", "変更・判断の理由"], 1):
        hdr_cell(ws1, 12, i, h)

    # ==========================================================
    # Sheet2: 対応方針
    # ==========================================================
    ws2 = wb.create_sheet("対応方針")
    ws2.column_dimensions["A"].width = 10
    for col, w in zip("BCDEFG", [22, 45, 32, 32, 22, 14]):
        ws2.column_dimensions[col].width = w

    # r1: タイトル, r2: 方針比較テーブル (A:G merged)
    sec_cell(ws2, 1, 1, "対応方針"); merge(ws2, 1, 1, 1, 7)
    sec_cell(ws2, 2, 1, "■ 方針比較テーブル"); merge(ws2, 2, 1, 2, 7)
    for i, h in enumerate(["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"], 1):
        hdr_cell(ws2, 3, i, h)
    bold_cell(ws2, 4, 1, "A★")
    bold_cell(ws2, 6, 1, "B")

    # r7: 採用方針, r8: プレースホルダー (A:G merged)
    sec_cell(ws2, 7, 1, "■ 採用方針"); merge(ws2, 7, 1, 7, 7)
    val_cell(ws2, 8, 1, "（方針確定後にここに採用理由を記録する）"); merge(ws2, 8, 1, 8, 7)

    # r9: blank
    # r10: 構成比較・差分記録 (A:G merged), r11: ヘッダー
    sec_cell(ws2, 10, 1, "■ 構成比較・差分記録（必要に応じて）"); merge(ws2, 10, 1, 10, 7)
    for i, h in enumerate(["要素", "既存（比較元）", "今回（実装対象）", "差分"], 1):
        hdr_cell(ws2, 11, i, h)

    # r12-19: blank (構成比較データエリア)
    # r20: 実施前確認事項 (A:G merged), r21: ヘッダー, r22-26: チェック行
    sec_cell(ws2, 20, 1, "■ 実施前確認事項"); merge(ws2, 20, 1, 20, 7)
    for i, h in enumerate(["□", "確認内容", "確認者", "備考"], 1):
        hdr_cell(ws2, 21, i, h)
    for r in range(22, 27):
        val_cell(ws2, r, 1, "□")

    # r27: 懸念事項 (A:G merged), r28-30: blank merged 行
    sec_cell(ws2, 27, 1, "■ 懸念事項"); merge(ws2, 27, 1, 27, 7)
    for r in range(28, 31):
        val_cell(ws2, r, 1, "")
        merge(ws2, r, 1, r, 7)

    # ==========================================================
    # Sheet3: 調査・影響範囲
    # ==========================================================
    ws3 = wb.create_sheet("調査・影響範囲")
    for col, w in zip("ABCDE", [6, 35, 35, 45, 10]):
        ws3.column_dimensions[col].width = w

    # r1: タイトル (A:E merged)
    sec_cell(ws3, 1, 1, "調査・影響範囲"); merge(ws3, 1, 1, 1, 5)

    # 仮説検証テーブル: r2 見出し, r3 ヘッダー, r4-9 データエリア
    sec_cell(ws3, 2, 1, "■ 仮説検証テーブル"); merge(ws3, 2, 1, 2, 5)
    for i, h in enumerate(["No", "仮説内容", "検証方法", "検証結果", "判定"], 1):
        hdr_cell(ws3, 3, i, h)

    # コード根拠テーブル: r10 見出し, r11 ヘッダー, r12-17 データエリア
    sec_cell(ws3, 10, 1, "■ コード根拠テーブル"); merge(ws3, 10, 1, 10, 5)
    for i, h in enumerate(["ファイル名", "行番号", "コード内容", "説明"], 1):
        hdr_cell(ws3, 11, i, h)

    # 影響範囲テーブル: r18 見出し, r19 ヘッダー, r20-26 データエリア
    sec_cell(ws3, 18, 1, "■ 影響範囲テーブル"); merge(ws3, 18, 1, 18, 5)
    for i, h in enumerate(["種別", "対象", "内容", "根拠"], 1):
        hdr_cell(ws3, 19, i, h)

    # 関連コンポーネント一覧: r27 見出し, r28 ヘッダー, r29-33 データエリア
    sec_cell(ws3, 27, 1, "■ 関連コンポーネント一覧"); merge(ws3, 27, 1, 27, 5)
    for i, h in enumerate(["種別", "名前", "役割", "調査結果"], 1):
        hdr_cell(ws3, 28, i, h)

    # ==========================================================
    # Sheet4: 対応内容
    # ==========================================================
    ws4 = wb.create_sheet("対応内容")
    ws4.column_dimensions["A"].width = 28
    ws4.column_dimensions["B"].width = 55
    ws4.column_dimensions["C"].width = 15
    ws4.column_dimensions["D"].width = 50
    ws4.column_dimensions["E"].width = 50
    ws4.column_dimensions["F"].width = 30

    # r1: タイトル, r2: バックアップ情報 (A:E merged)
    sec_cell(ws4, 1, 1, "対応内容"); merge(ws4, 1, 1, 1, 5)
    sec_cell(ws4, 2, 1, "■ バックアップ情報（修正前に記録）"); merge(ws4, 2, 1, 2, 5)

    # r3-5: バックアップ情報 (A=ラベル bold, B:E merged value)
    bold_cell(ws4, 3, 1, "Git hash（修正前）")
    val_cell(ws4, 3, 2, "（実装前に記録: git rev-parse HEAD）"); merge(ws4, 3, 2, 3, 5)
    bold_cell(ws4, 4, 1, "stash名")
    val_cell(ws4, 4, 2, "（stash使用時に記録）"); merge(ws4, 4, 2, 4, 5)
    bold_cell(ws4, 5, 1, "巻き戻し方法")
    val_cell(ws4, 5, 2, "git reset --hard [hash] または git stash pop"); merge(ws4, 5, 2, 5, 5)

    # r6: blank
    # r7: 変更ファイル一覧 (A:E merged), r8: ヘッダー, r9-12: データエリア (4行)
    sec_cell(ws4, 7, 1, "■ 変更ファイル一覧"); merge(ws4, 7, 1, 7, 5)
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要"], 1):
        hdr_cell(ws4, 8, i, h)

    # r13: Before/After 見出し (A:E merged)
    # r14: 説明行 (A:E merged), r15-17: blank merged 行
    sec_cell(ws4, 13, 1, "■ Before / After（実装後に記入）"); merge(ws4, 13, 1, 13, 5)
    val_cell(ws4, 14, 1, "実装完了後、各ファイルの変更前後を記載する"); merge(ws4, 14, 1, 14, 5)
    for r in [15, 16, 17]:
        merge(ws4, r, 1, r, 5)

    # r18: blank
    # r19: 影響確認チェックリスト (A:E merged), r20: ヘッダー, r21-27: チェック行
    sec_cell(ws4, 19, 1, "■ 影響確認チェックリスト"); merge(ws4, 19, 1, 19, 5)
    for i, h in enumerate(["□", "確認内容", "結果", "備考"], 1):
        hdr_cell(ws4, 20, i, h)
    for r in range(21, 28):
        val_cell(ws4, r, 1, "□")

    # r28: blank
    # r29: 追加修正 (A:F merged), r30: ヘッダー
    sec_cell(ws4, 29, 1, "■ 追加修正（必要に応じて追記）"); merge(ws4, 29, 1, 29, 6)
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要", "詳細・根拠"], 1):
        hdr_cell(ws4, 30, i, h)

    # ==========================================================
    # Sheet5: テスト・検証記録
    # ==========================================================
    ws5 = wb.create_sheet("テスト・検証記録")
    for col, w in zip("ABCDEFGH", [6, 16, 32, 32, 32, 32, 10, 35]):
        ws5.column_dimensions[col].width = w

    # r1: タイトル, r2: テスト方針, r3: プレースホルダー (A:H merged)
    sec_cell(ws5, 1, 1, "テスト・検証記録"); merge(ws5, 1, 1, 1, 8)
    sec_cell(ws5, 2, 1, "■ テスト方針"); merge(ws5, 2, 1, 2, 8)
    val_cell(ws5, 3, 1, "（テスト方針・観点をここに記載する）"); merge(ws5, 3, 1, 3, 8)

    # r4: blank
    # r5: テストテーブル (A:H merged), r6: ヘッダー, r7-16: データエリア
    sec_cell(ws5, 5, 1, "■ テストテーブル"); merge(ws5, 5, 1, 5, 8)
    for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
        hdr_cell(ws5, 6, i, h)

    # r17: テスト結果見出し (A:H merged), r18: ヘッダー (完了後に記入)
    sec_cell(ws5, 17, 1, "■ テスト結果（完了後に記入）"); merge(ws5, 17, 1, 17, 8)
    for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
        hdr_cell(ws5, 18, i, h)

    # ==========================================================
    # Sheet6: リリース・ロールバック
    # ==========================================================
    ws6 = wb.create_sheet("リリース・ロールバック")
    for col, w in zip("ABCDEF", [6, 22, 35, 20, 32, 32]):
        ws6.column_dimensions[col].width = w

    # r1: タイトル (A:F merged)
    sec_cell(ws6, 1, 1, "リリース・ロールバック"); merge(ws6, 1, 1, 1, 6)

    # r2: リリース対象一覧, r3: ヘッダー, r4-5: データエリア (2行)
    sec_cell(ws6, 2, 1, "■ リリース対象一覧"); merge(ws6, 2, 1, 2, 6)
    for i, h in enumerate(["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"], 1):
        hdr_cell(ws6, 3, i, h)

    # r6: blank
    # r7: リリース前確認事項, r8: ヘッダー, r9-12: チェック行
    sec_cell(ws6, 7, 1, "■ リリース前確認事項"); merge(ws6, 7, 1, 7, 6)
    for i, h in enumerate(["□", "確認内容", "確認者", "結果"], 1):
        hdr_cell(ws6, 8, i, h)
    for r in range(9, 13):
        val_cell(ws6, r, 1, "□")

    # r13: blank
    # r14: デプロイ手順 (A:F merged), r15-18: blank merged 行
    sec_cell(ws6, 14, 1, "■ デプロイ手順"); merge(ws6, 14, 1, 14, 6)
    for r in [15, 16, 17, 18]:
        merge(ws6, r, 1, r, 6)

    # r19: blank
    # r20: デプロイ後確認事項, r21: ヘッダー, r22-25: チェック行
    sec_cell(ws6, 20, 1, "■ デプロイ後確認事項"); merge(ws6, 20, 1, 20, 6)
    for i, h in enumerate(["□", "確認内容", "確認者", "結果"], 1):
        hdr_cell(ws6, 21, i, h)
    for r in range(22, 26):
        val_cell(ws6, r, 1, "□")

    # r26: blank
    # r27: 注意事項・リスク (A:F merged), r28-29: blank merged 行
    sec_cell(ws6, 27, 1, "■ 注意事項・リスク"); merge(ws6, 27, 1, 27, 6)
    for r in [28, 29]:
        merge(ws6, r, 1, r, 6)

    # r30: blank
    # r31: ロールバック手順 (A:F merged), r32-35: blank merged 行
    sec_cell(ws6, 31, 1, "■ ロールバック手順"); merge(ws6, 31, 1, 31, 6)
    for r in [32, 33, 34, 35]:
        merge(ws6, r, 1, r, 6)

    # r36: blank
    # r37: リリース実施記録 (A:F merged), r38: ヘッダー
    sec_cell(ws6, 37, 1, "■ リリース実施記録"); merge(ws6, 37, 1, 37, 6)
    for i, h in enumerate(["実施日", "実施者", "結果", "備考"], 1):
        hdr_cell(ws6, 38, i, h)

    path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
