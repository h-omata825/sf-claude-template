# -*- coding: utf-8 -*-
"""
backlog-xlsx / create_records.py
対応記録.xlsx を生成するスクリプト (GF-327 ビジュアル互換版)

GF-327 の実ファイルから抽出したスタイル（列幅・行高・カラーパレット・ボーダー・
偶数行ストライプ・垂直 center）を完全再現する。

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
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)


# ================= スタイルパレット（GF-327 から抽出） =================
TITLE_FILL  = PatternFill("solid", fgColor="1F4E79")  # 濃紺（シートタイトル）
SEC_FILL    = PatternFill("solid", fgColor="D6E4F0")  # 薄青（セクション見出し ■）
HDR_FILL    = PatternFill("solid", fgColor="2E75B6")  # 明青（列ヘッダー）
WHITE_FILL  = PatternFill("solid", fgColor="FFFFFF")  # 白（奇数行）
STRIPE_FILL = PatternFill("solid", fgColor="F2F7FB")  # 超薄青（偶数行ストライプ）

TITLE_FONT = Font(color="FFFFFF", bold=True, size=14)
SEC_FONT   = Font(color="000000", bold=True, size=10)
HDR_FONT   = Font(color="FFFFFF", bold=True, size=10)
BOLD_FONT  = Font(bold=True, size=10)
CELL_FONT  = Font(size=10)

TITLE_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
SEC_ALIGN   = Alignment(horizontal="left",   vertical="center", wrap_text=True)
HDR_ALIGN   = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGN  = Alignment(horizontal="left",   vertical="center", wrap_text=True)

_THIN = Side(style="thin", color="000000")
BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _style(cell, fill, font, align, border=None):
    cell.fill = fill
    cell.font = font
    cell.alignment = align
    if border:
        cell.border = border


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

    # ---------- 汎用ヘルパー ----------
    def title_cell(ws, row, col, val):
        """シートタイトル（濃紺・白・14pt・中央）"""
        c = ws.cell(row=row, column=col, value=val)
        _style(c, TITLE_FILL, TITLE_FONT, TITLE_ALIGN)
        return c

    def sec_cell(ws, row, col, val):
        """セクション見出し ■（薄青・黒・左中央）"""
        c = ws.cell(row=row, column=col, value=val)
        _style(c, SEC_FILL, SEC_FONT, SEC_ALIGN)
        return c

    def hdr_cell(ws, row, col, val):
        """列ヘッダー（明青・白・中央・ボーダー）"""
        c = ws.cell(row=row, column=col, value=val)
        _style(c, HDR_FILL, HDR_FONT, HDR_ALIGN, BORDER)
        return c

    def bold_cell(ws, row, col, val, stripe=False):
        """ラベル（ボールド・ボーダー・行ストライプ対応）"""
        c = ws.cell(row=row, column=col, value=val)
        fill = STRIPE_FILL if stripe else WHITE_FILL
        _style(c, fill, BOLD_FONT, CELL_ALIGN, BORDER)
        return c

    def data_cell(ws, row, col, val="", stripe=False):
        """通常セル（ボーダー・行ストライプ対応）"""
        c = ws.cell(row=row, column=col, value=val)
        fill = STRIPE_FILL if stripe else WHITE_FILL
        _style(c, fill, CELL_FONT, CELL_ALIGN, BORDER)
        return c

    def merge(ws, r1, c1, r2, c2):
        ws.merge_cells(f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}")

    def set_col_widths(ws, widths):
        """widths: {'A': 20, 'B': 14, ...}"""
        for col, w in widths.items():
            ws.column_dimensions[col].width = w

    def set_row_heights(ws, heights):
        """heights: {1: 38, 2: 28, ...}"""
        for r, h in heights.items():
            ws.row_dimensions[r].height = h

    def fill_row_border(ws, row, c1, c2, stripe=False):
        """指定行の c1..c2 に空セル＋ボーダー＋ストライプを張る（値は None 維持）"""
        fill = STRIPE_FILL if stripe else WHITE_FILL
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=row, column=c)
            if cell.value is None:
                _style(cell, fill, CELL_FONT, CELL_ALIGN, BORDER)

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # ==========================================================
    # Sheet1: サマリー・経緯
    # ==========================================================
    ws1 = wb.active
    ws1.title = "サマリー・経緯"
    set_col_widths(ws1, {"A": 20, "B": 14, "C": 16, "D": 60, "E": 40, "F": 10})
    set_row_heights(ws1, {1: 38, 2: 28, **{r: 25 for r in range(3, 10)}, 10: 8, 11: 28, 12: 28})

    # r1: タイトル (A:F merged)
    title_cell(ws1, 1, 1, "サマリー・経緯"); merge(ws1, 1, 1, 1, 6)
    # r2: セクション見出し
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
        stripe = (i % 2 == 0)
        bold_cell(ws1, i, 1, k, stripe=stripe)
        data_cell(ws1, i, 2, v, stripe=stripe)
        merge(ws1, i, 2, i, 6)

    # r10: セパレーター / r11: タイムライン見出し / r12: カラムヘッダー
    sec_cell(ws1, 11, 1, "■ 対応経緯タイムライン"); merge(ws1, 11, 1, 11, 6)
    for i, h in enumerate(["No", "日時", "発生元", "フェーズ", "内容・決定事項", "変更・判断の理由"], 1):
        hdr_cell(ws1, 12, i, h)

    # ==========================================================
    # Sheet2: 対応方針
    # ==========================================================
    ws2 = wb.create_sheet("対応方針")
    set_col_widths(ws2, {"A": 6, "B": 20, "C": 50, "D": 35, "E": 35, "F": 25, "G": 12})
    set_row_heights(ws2, {
        1: 38, 2: 28, 3: 28, 4: 80, 5: 80, 6: 8, 7: 28, 8: 90, 9: 8,
        10: 28, 11: 28, **{r: 35 for r in range(12, 20)}, 20: 28, 21: 28,
        **{r: 25 for r in range(22, 27)}, 27: 28, **{r: 35 for r in range(28, 31)}
    })

    # r1: タイトル
    title_cell(ws2, 1, 1, "対応方針"); merge(ws2, 1, 1, 1, 7)
    # r2: 方針比較テーブル見出し
    sec_cell(ws2, 2, 1, "■ 方針比較テーブル"); merge(ws2, 2, 1, 2, 7)
    # r3: カラムヘッダー
    for i, h in enumerate(["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"], 1):
        hdr_cell(ws2, 3, i, h)
    # r4, 5: 案A/B プレースホルダー（ストライプ: r5=偶数行）
    for r_idx, label in [(4, "A★"), (5, "B")]:
        stripe = (r_idx % 2 == 0)
        bold_cell(ws2, r_idx, 1, label, stripe=stripe)
        for c in range(2, 8):
            data_cell(ws2, r_idx, c, "", stripe=stripe)

    # r6: セパレーター / r7: 採用方針見出し / r8: プレースホルダー (A:G merged)
    sec_cell(ws2, 7, 1, "■ 採用方針"); merge(ws2, 7, 1, 7, 7)
    data_cell(ws2, 8, 1, "（方針確定後にここに採用理由を記録する）"); merge(ws2, 8, 1, 8, 7)

    # r9: セパレーター / r10: 構成比較見出し / r11: カラムヘッダー / r12-19: データ
    sec_cell(ws2, 10, 1, "■ 構成比較・差分記録（必要に応じて）"); merge(ws2, 10, 1, 10, 7)
    for i, h in enumerate(["要素", "既存（比較元）", "今回（実装対象）", "差分"], 1):
        hdr_cell(ws2, 11, i, h)
    for r in range(12, 20):
        stripe = (r % 2 == 0)
        for c in range(1, 5):
            data_cell(ws2, r, c, "", stripe=stripe)

    # r20: 実施前確認事項 / r21: カラムヘッダー / r22-26: チェック行
    sec_cell(ws2, 20, 1, "■ 実施前確認事項"); merge(ws2, 20, 1, 20, 7)
    for i, h in enumerate(["□", "確認内容", "確認者", "備考"], 1):
        hdr_cell(ws2, 21, i, h)
    for r in range(22, 27):
        stripe = (r % 2 == 0)
        data_cell(ws2, r, 1, "□", stripe=stripe)
        for c in range(2, 5):
            data_cell(ws2, r, c, "", stripe=stripe)

    # r27: 懸念事項 / r28-30: merged blank
    sec_cell(ws2, 27, 1, "■ 懸念事項"); merge(ws2, 27, 1, 27, 7)
    for r in [28, 29, 30]:
        stripe = (r % 2 == 0)
        data_cell(ws2, r, 1, "", stripe=stripe); merge(ws2, r, 1, r, 7)

    # ==========================================================
    # Sheet3: 調査・影響範囲
    # ==========================================================
    ws3 = wb.create_sheet("調査・影響範囲")
    set_col_widths(ws3, {"A": 6, "B": 40, "C": 40, "D": 50, "E": 20})
    set_row_heights(ws3, {
        1: 38, 2: 28, 3: 28, **{r: 55 for r in range(4, 10)}, 9: 8,
        10: 28, 11: 28, **{r: 45 for r in range(12, 18)}, 17: 8,
        18: 28, 19: 28, **{r: 40 for r in range(20, 27)}, 26: 8,
        27: 28, 28: 28, **{r: 40 for r in range(29, 34)}
    })

    # r1: タイトル
    title_cell(ws3, 1, 1, "調査・影響範囲"); merge(ws3, 1, 1, 1, 5)

    # 仮説検証テーブル (r2=見出し, r3=ヘッダー, r4-8=データ)
    sec_cell(ws3, 2, 1, "■ 仮説検証テーブル"); merge(ws3, 2, 1, 2, 5)
    for i, h in enumerate(["No", "仮説内容", "検証方法", "検証結果", "判定"], 1):
        hdr_cell(ws3, 3, i, h)
    for r in range(4, 9):
        stripe = (r % 2 == 0)
        for c in range(1, 6):
            data_cell(ws3, r, c, "", stripe=stripe)

    # コード根拠テーブル (r10=見出し, r11=ヘッダー, r12-16=データ)
    sec_cell(ws3, 10, 1, "■ コード根拠テーブル"); merge(ws3, 10, 1, 10, 5)
    for i, h in enumerate(["ファイル名", "行番号", "コード内容", "説明", "根拠"], 1):
        hdr_cell(ws3, 11, i, h)
    for r in range(12, 17):
        stripe = (r % 2 == 0)
        for c in range(1, 6):
            data_cell(ws3, r, c, "", stripe=stripe)

    # 影響範囲テーブル (r18=見出し, r19=ヘッダー, r20-25=データ)
    sec_cell(ws3, 18, 1, "■ 影響範囲テーブル"); merge(ws3, 18, 1, 18, 5)
    for i, h in enumerate(["種別", "対象", "内容", "根拠", "備考"], 1):
        hdr_cell(ws3, 19, i, h)
    for r in range(20, 26):
        stripe = (r % 2 == 0)
        for c in range(1, 6):
            data_cell(ws3, r, c, "", stripe=stripe)

    # 関連コンポーネント一覧 (r27=見出し, r28=ヘッダー, r29-33=データ)
    sec_cell(ws3, 27, 1, "■ 関連コンポーネント一覧"); merge(ws3, 27, 1, 27, 5)
    for i, h in enumerate(["種別", "名前", "役割", "調査結果", "備考"], 1):
        hdr_cell(ws3, 28, i, h)
    for r in range(29, 34):
        stripe = (r % 2 == 0)
        for c in range(1, 6):
            data_cell(ws3, r, c, "", stripe=stripe)

    # ==========================================================
    # Sheet4: 対応内容
    # ==========================================================
    ws4 = wb.create_sheet("対応内容")
    set_col_widths(ws4, {"A": 6, "B": 50, "C": 15, "D": 50, "E": 20, "F": 30})
    set_row_heights(ws4, {
        1: 38, 2: 28, 3: 25, 4: 25, 5: 25, 6: 8, 7: 28, 8: 28,
        **{r: 35 for r in range(9, 13)}, 12: 8, 13: 28, 14: 30,
        **{r: 25 for r in range(15, 19)}, 18: 8, 19: 28, 20: 28,
        **{r: 25 for r in range(21, 28)}, 29: 28, 30: 28,
        **{r: 50 for r in range(31, 38)}
    })

    # r1: タイトル
    title_cell(ws4, 1, 1, "対応内容"); merge(ws4, 1, 1, 1, 5)

    # ■ バックアップ情報 (r2=見出し, r3-5=データ)
    sec_cell(ws4, 2, 1, "■ バックアップ情報（修正前に記録）"); merge(ws4, 2, 1, 2, 5)
    backup_rows = [
        ("Git hash（修正前）", "（実装前に記録: git rev-parse HEAD）"),
        ("stash名",             "（stash使用時に記録）"),
        ("巻き戻し方法",        "git reset --hard [hash] または git stash pop"),
    ]
    for i, (k, v) in enumerate(backup_rows, start=3):
        stripe = (i % 2 == 0)
        bold_cell(ws4, i, 1, k, stripe=stripe)
        data_cell(ws4, i, 2, v, stripe=stripe); merge(ws4, i, 2, i, 5)

    # ■ 変更ファイル一覧 (r7=見出し, r8=ヘッダー, r9-11=データ)
    sec_cell(ws4, 7, 1, "■ 変更ファイル一覧"); merge(ws4, 7, 1, 7, 5)
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要", "備考"], 1):
        hdr_cell(ws4, 8, i, h)
    for r in range(9, 12):
        stripe = (r % 2 == 0)
        for c in range(1, 6):
            data_cell(ws4, r, c, "", stripe=stripe)

    # ■ Before / After (r13=見出し, r14=説明, r15-17=データ)
    sec_cell(ws4, 13, 1, "■ Before / After（実装後に記入）"); merge(ws4, 13, 1, 13, 5)
    data_cell(ws4, 14, 1, "実装完了後、各ファイルの変更前後を記載する"); merge(ws4, 14, 1, 14, 5)
    for r in [15, 16, 17]:
        stripe = (r % 2 == 0)
        data_cell(ws4, r, 1, "", stripe=stripe); merge(ws4, r, 1, r, 5)

    # ■ 影響確認チェックリスト (r19=見出し, r20=ヘッダー, r21-27=データ)
    sec_cell(ws4, 19, 1, "■ 影響確認チェックリスト"); merge(ws4, 19, 1, 19, 5)
    for i, h in enumerate(["□", "確認内容", "結果", "備考", "根拠"], 1):
        hdr_cell(ws4, 20, i, h)
    for r in range(21, 28):
        stripe = (r % 2 == 0)
        data_cell(ws4, r, 1, "□", stripe=stripe)
        for c in range(2, 6):
            data_cell(ws4, r, c, "", stripe=stripe)

    # ■ 追加修正 (r29=見出し, r30=ヘッダー, r31-37=データ)
    sec_cell(ws4, 29, 1, "■ 追加修正（必要に応じて追記）"); merge(ws4, 29, 1, 29, 6)
    for i, h in enumerate(["No", "ファイルパス", "変更種別", "変更概要", "詳細・根拠", "日付"], 1):
        hdr_cell(ws4, 30, i, h)
    for r in range(31, 38):
        stripe = (r % 2 == 0)
        for c in range(1, 7):
            data_cell(ws4, r, c, "", stripe=stripe)

    # ==========================================================
    # Sheet5: テスト・検証記録
    # ==========================================================
    ws5 = wb.create_sheet("テスト・検証記録")
    set_col_widths(ws5, {"A": 6, "B": 12, "C": 35, "D": 35, "E": 30, "F": 30, "G": 10, "H": 30})
    set_row_heights(ws5, {
        1: 38, 2: 28, 3: 45, 4: 8, 5: 28, 6: 28,
        **{r: 45 for r in range(7, 15)}, 14: 8, 17: 28, 18: 28,
        **{r: 50 for r in range(19, 26)}
    })

    # r1: タイトル
    title_cell(ws5, 1, 1, "テスト・検証記録"); merge(ws5, 1, 1, 1, 8)

    # ■ テスト方針 (r2=見出し, r3=プレースホルダー)
    sec_cell(ws5, 2, 1, "■ テスト方針"); merge(ws5, 2, 1, 2, 8)
    data_cell(ws5, 3, 1, "（テスト方針・観点をここに記載する）"); merge(ws5, 3, 1, 3, 8)

    # ■ テストテーブル (r5=見出し, r6=ヘッダー, r7-13=データ)
    sec_cell(ws5, 5, 1, "■ テストテーブル"); merge(ws5, 5, 1, 5, 8)
    for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
        hdr_cell(ws5, 6, i, h)
    for r in range(7, 14):
        stripe = (r % 2 == 0)
        for c in range(1, 9):
            data_cell(ws5, r, c, "", stripe=stripe)

    # ■ テスト結果（完了後に記入） (r17=見出し, r18=ヘッダー, r19-25=データ)
    sec_cell(ws5, 17, 1, "■ テスト結果（完了後に記入）"); merge(ws5, 17, 1, 17, 8)
    for i, h in enumerate(["No", "区分", "テスト項目", "確認方法", "期待結果", "実際の結果", "判定", "根拠"], 1):
        hdr_cell(ws5, 18, i, h)
    for r in range(19, 26):
        stripe = (r % 2 == 0)
        for c in range(1, 9):
            data_cell(ws5, r, c, "", stripe=stripe)

    # ==========================================================
    # Sheet6: リリース・ロールバック
    # ==========================================================
    ws6 = wb.create_sheet("リリース・ロールバック")
    set_col_widths(ws6, {"A": 6, "B": 15, "C": 40, "D": 20, "E": 25, "F": 30})
    set_row_heights(ws6, {
        1: 38, 2: 28, 3: 28, 4: 25, 5: 25, 6: 8, 7: 28, 8: 28,
        **{r: 25 for r in range(9, 13)}, 13: 8, 14: 28,
        **{r: 25 for r in range(15, 19)}, 19: 8, 20: 28, 21: 28,
        **{r: 25 for r in range(22, 26)}, 26: 8, 27: 28,
        28: 35, 29: 35, 30: 8, 31: 28, **{r: 25 for r in range(32, 36)},
        36: 8, 37: 28, 38: 28, 39: 25
    })

    # r1: タイトル
    title_cell(ws6, 1, 1, "リリース・ロールバック"); merge(ws6, 1, 1, 1, 6)

    # ■ リリース対象一覧 (r2=見出し, r3=ヘッダー, r4-5=データ)
    sec_cell(ws6, 2, 1, "■ リリース対象一覧"); merge(ws6, 2, 1, 2, 6)
    for i, h in enumerate(["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"], 1):
        hdr_cell(ws6, 3, i, h)
    for r in [4, 5]:
        stripe = (r % 2 == 0)
        for c in range(1, 7):
            data_cell(ws6, r, c, "", stripe=stripe)

    # ■ リリース前確認事項 (r7=見出し, r8=ヘッダー, r9-12=チェック行)
    sec_cell(ws6, 7, 1, "■ リリース前確認事項"); merge(ws6, 7, 1, 7, 6)
    for i, h in enumerate(["□", "確認内容", "確認者", "結果", "根拠", "備考"], 1):
        hdr_cell(ws6, 8, i, h)
    for r in range(9, 13):
        stripe = (r % 2 == 0)
        data_cell(ws6, r, 1, "□", stripe=stripe)
        for c in range(2, 7):
            data_cell(ws6, r, c, "", stripe=stripe)

    # ■ デプロイ手順 (r14=見出し, r15-18=merged blank)
    sec_cell(ws6, 14, 1, "■ デプロイ手順"); merge(ws6, 14, 1, 14, 6)
    for r in [15, 16, 17, 18]:
        stripe = (r % 2 == 0)
        data_cell(ws6, r, 1, "", stripe=stripe); merge(ws6, r, 1, r, 6)

    # ■ デプロイ後確認事項 (r20=見出し, r21=ヘッダー, r22-25=チェック行)
    sec_cell(ws6, 20, 1, "■ デプロイ後確認事項"); merge(ws6, 20, 1, 20, 6)
    for i, h in enumerate(["□", "確認内容", "確認者", "結果", "根拠", "備考"], 1):
        hdr_cell(ws6, 21, i, h)
    for r in range(22, 26):
        stripe = (r % 2 == 0)
        data_cell(ws6, r, 1, "□", stripe=stripe)
        for c in range(2, 7):
            data_cell(ws6, r, c, "", stripe=stripe)

    # ■ 注意事項・リスク (r27=見出し, r28-29=merged blank)
    sec_cell(ws6, 27, 1, "■ 注意事項・リスク"); merge(ws6, 27, 1, 27, 6)
    for r in [28, 29]:
        stripe = (r % 2 == 0)
        data_cell(ws6, r, 1, "", stripe=stripe); merge(ws6, r, 1, r, 6)

    # ■ ロールバック手順 (r31=見出し, r32-35=merged blank)
    sec_cell(ws6, 31, 1, "■ ロールバック手順"); merge(ws6, 31, 1, 31, 6)
    for r in [32, 33, 34, 35]:
        stripe = (r % 2 == 0)
        data_cell(ws6, r, 1, "", stripe=stripe); merge(ws6, r, 1, r, 6)

    # ■ リリース実施記録 (r37=見出し, r38=ヘッダー, r39=データ)
    sec_cell(ws6, 37, 1, "■ リリース実施記録"); merge(ws6, 37, 1, 37, 6)
    for i, h in enumerate(["実施日", "実施者", "結果", "備考", "根拠", "備考2"], 1):
        hdr_cell(ws6, 38, i, h)
    for r in [39]:
        stripe = (r % 2 == 0)
        for c in range(1, 7):
            data_cell(ws6, r, c, "", stripe=stripe)

    path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
