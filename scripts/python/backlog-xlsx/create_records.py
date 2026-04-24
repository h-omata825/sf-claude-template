# -*- coding: utf-8 -*-
"""backlog-xlsx / create_records.py
対応記録.xlsx を生成する (GF-327 リッチ版スタイル準拠)

Usage:
    python create_records.py --folder FOLDER --issue-id ID --title TITLE
                             --type TYPE --priority PRIORITY --deadline DEADLINE
                             --summary SUMMARY
"""

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)

# ── スタイル定数 ────────────────────────────────────────────────
TITLE_FILL  = PatternFill("solid", fgColor="1F4E79")  # 濃紺
SEC_FILL    = PatternFill("solid", fgColor="D6E4F0")  # 薄青
HDR_FILL    = PatternFill("solid", fgColor="2E75B6")  # 水色
KEY_FILL    = PatternFill("solid", fgColor="F5F5F5")  # 薄灰
WHT_FILL    = PatternFill("solid", fgColor="FFFFFF")  # 白
STRIPE_FILL = PatternFill("solid", fgColor="F2F7FB")  # ストライプ薄青

TITLE_FONT = Font(color="FFFFFF", bold=True, size=14)
SEC_FONT   = Font(bold=True, size=10)
HDR_FONT   = Font(color="FFFFFF", bold=True, size=10)
KEY_FONT   = Font(bold=True, size=10)
STD_FONT   = Font(size=10)

WRAP = Alignment(wrap_text=True, vertical="top")
TOP  = Alignment(vertical="top")


def _merge_fill(ws, r, c1, c2, fill, font, val="", align=None):
    cell = ws.cell(row=r, column=c1, value=val)
    cell.fill = fill
    cell.font = font
    cell.alignment = align or WRAP
    if c2 > c1:
        from openpyxl.utils import get_column_letter
        ws.merge_cells(f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}")
    return cell


def title_row(ws, r, last_col, text):
    _merge_fill(ws, r, 1, last_col, TITLE_FILL, TITLE_FONT, text)


def sec_row(ws, r, last_col, text):
    _merge_fill(ws, r, 1, last_col, SEC_FILL, SEC_FONT, text)


def kv_row(ws, r, last_col, key, val=""):
    ws.cell(row=r, column=1, value=key).fill   = KEY_FILL
    ws.cell(row=r, column=1).font              = KEY_FONT
    ws.cell(row=r, column=1).alignment         = WRAP
    _merge_fill(ws, r, 2, last_col, WHT_FILL, STD_FONT, val)


def hdr_row(ws, r, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=r, column=i, value=h)
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = WRAP


def data_row(ws, r, cells, stripe=False):
    fill = STRIPE_FILL if stripe else WHT_FILL
    for i, val in enumerate(cells, 1):
        c = ws.cell(row=r, column=i, value=val)
        c.fill = fill
        c.font = STD_FONT
        c.alignment = WRAP


def main():
    parser = argparse.ArgumentParser(description="対応記録.xlsx を生成する")
    parser.add_argument("--folder",   required=True)
    parser.add_argument("--issue-id", required=True, dest="issue_id")
    parser.add_argument("--title",    required=True)
    parser.add_argument("--type",     required=True, dest="issue_type")
    parser.add_argument("--priority", required=True)
    parser.add_argument("--deadline", required=True)
    parser.add_argument("--summary",  required=True)
    args = parser.parse_args()

    FOLDER      = args.folder
    ISSUE_ID    = args.issue_id
    ISSUE_TITLE = args.title
    ISSUE_TYPE  = args.issue_type
    PRIORITY    = args.priority
    DEADLINE    = args.deadline
    BG_DESC     = args.summary

    os.makedirs(FOLDER, exist_ok=True)
    wb = openpyxl.Workbook()

    # ================================================================
    # Sheet1: サマリー・経緯
    # ================================================================
    ws1 = wb.active
    ws1.title = "サマリー・経緯"
    for col, w in zip("ABCDEF", [20, 14, 16, 60, 40, 10]):
        ws1.column_dimensions[col].width = w

    r = 1
    title_row(ws1, r, 6, "サマリー・経緯");                r += 1
    sec_row(ws1, r, 6, "■ 課題サマリー");                  r += 1
    kv_row(ws1, r, 6, "課題ID", ISSUE_ID);                 r += 1
    kv_row(ws1, r, 6, "件名", ISSUE_TITLE);                r += 1
    kv_row(ws1, r, 6, "優先度・期限",
           f"優先度: {PRIORITY} / 期限: {DEADLINE}");       r += 1
    kv_row(ws1, r, 6, "課題種別", ISSUE_TYPE);             r += 1
    kv_row(ws1, r, 6, "ステータス", "対応中");             r += 1
    kv_row(ws1, r, 6, "背景・要件", BG_DESC);              r += 1
    kv_row(ws1, r, 6, "最終対応サマリー", "（完了時に記入）"); r += 1
    r += 1  # 空行
    sec_row(ws1, r, 6, "■ 工数");                          r += 1
    for k in ["対応開始日時", "対応完了日時",
              "見積工数（CC使用）", "見積工数（CC未使用）",
              "実績工数（CC使用）", "削減効果"]:
        kv_row(ws1, r, 6, k);                              r += 1
    r += 1  # 空行
    sec_row(ws1, r, 6, "■ 対応経緯タイムライン");          r += 1
    hdr_row(ws1, r,
            ["No", "日時", "発生元", "フェーズ", "内容・決定事項", "変更・判断の理由"])

    # ================================================================
    # Sheet2: 対応方針
    # ================================================================
    ws2 = wb.create_sheet("対応方針")
    for col, w in zip("ABCDEFG", [6, 20, 50, 35, 35, 25, 12]):
        ws2.column_dimensions[col].width = w

    r = 1
    title_row(ws2, r, 7, "対応方針");                      r += 1
    sec_row(ws2, r, 7, "■ 方針比較テーブル");              r += 1
    hdr_row(ws2, r,
            ["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"]); r += 1
    data_row(ws2, r, ["A★", "", "", "", "", "", ""],
             stripe=False);                                 r += 1
    data_row(ws2, r, ["B",  "", "", "", "", "", ""],
             stripe=True);                                  r += 1
    r += 1  # 空行
    sec_row(ws2, r, 7, "■ 採用方針");                      r += 1
    _merge_fill(ws2, r, 1, 7, WHT_FILL, STD_FONT,
                "（方針確定後にここに採用理由を記録する）"); r += 1
    r += 1  # 空行
    sec_row(ws2, r, 7, "■ 構成比較・差分記録（必要に応じて）"); r += 1
    hdr_row(ws2, r, ["要素", "既存（比較元）", "今回（実装対象）", "差分",
                     "", "", ""])

    # ================================================================
    # Sheet3: 調査・影響範囲
    # ================================================================
    ws3 = wb.create_sheet("調査・影響範囲")
    for col, w in zip("ABCDE", [6, 40, 40, 50, 20]):
        ws3.column_dimensions[col].width = w

    r = 1
    title_row(ws3, r, 5, "調査・影響範囲");                r += 1
    sec_row(ws3, r, 5, "■ 仮説検証テーブル");              r += 1
    hdr_row(ws3, r,
            ["No", "仮説内容 / 種別", "検証方法", "検証結果・根拠", "判定"])

    # ================================================================
    # Sheet4: 対応内容
    # ================================================================
    ws4 = wb.create_sheet("対応内容")
    for col, w in zip("ABCDE", [6, 50, 15, 50, 20]):
        ws4.column_dimensions[col].width = w

    r = 1
    title_row(ws4, r, 5, "対応内容");                      r += 1
    sec_row(ws4, r, 5, "■ バックアップ情報（修正前に記録）"); r += 1
    kv_row(ws4, r, 5, "Git hash（修正前）",
           "（実装前に記録: git rev-parse HEAD）");         r += 1
    kv_row(ws4, r, 5, "stash名", "（stash使用時に記録）"); r += 1
    kv_row(ws4, r, 5, "巻き戻し方法",
           "git reset --hard [hash] または git stash pop"); r += 1
    r += 1  # 空行
    sec_row(ws4, r, 5, "■ 変更ファイル一覧");              r += 1
    hdr_row(ws4, r,
            ["No", "ファイルパス", "変更種別", "変更概要", ""]); r += 1
    for i in range(6):
        data_row(ws4, r, ["", "", "", "", ""], stripe=(i % 2 == 1)); r += 1
    sec_row(ws4, r, 5, "■ Before / After（実装後に記入）"); r += 1
    _merge_fill(ws4, r, 1, 5, WHT_FILL, STD_FONT,
                "実装完了後、各ファイルの変更前後を記載する"); r += 1
    r += 3  # 余白
    sec_row(ws4, r, 5, "■ 影響確認チェックリスト");        r += 1
    hdr_row(ws4, r, ["□", "確認内容", "結果", "備考", ""]); r += 1
    for i in range(6):
        data_row(ws4, r, ["□", "", "", "", ""], stripe=(i % 2 == 1)); r += 1
    sec_row(ws4, r, 5, "■ 追加修正（必要に応じて追記）");  r += 1
    hdr_row(ws4, r, ["No", "ファイルパス", "変更種別", "変更概要", "詳細・根拠"])

    # ================================================================
    # Sheet5: テスト・検証記録
    # ================================================================
    ws5 = wb.create_sheet("テスト・検証記録")
    for col, w in zip("ABCDEFGH", [6, 12, 35, 35, 30, 30, 10, 30]):
        ws5.column_dimensions[col].width = w

    r = 1
    title_row(ws5, r, 8, "テスト・検証記録");              r += 1
    sec_row(ws5, r, 8, "■ テスト方針");                   r += 1
    _merge_fill(ws5, r, 1, 8, WHT_FILL, STD_FONT,
                "（テスト方針・観点をここに記載する）");     r += 1
    r += 1  # 空行
    sec_row(ws5, r, 8, "■ テストテーブル");               r += 1
    hdr_row(ws5, r,
            ["No", "区分", "テスト項目", "確認方法",
             "期待結果", "実際の結果", "判定", "根拠"])

    # ================================================================
    # Sheet6: リリース・ロールバック
    # ================================================================
    ws6 = wb.create_sheet("リリース・ロールバック")
    for col, w in zip("ABCDEF", [6, 15, 40, 20, 25, 30]):
        ws6.column_dimensions[col].width = w

    r = 1
    title_row(ws6, r, 6, "リリース・ロールバック");        r += 1
    sec_row(ws6, r, 6, "■ リリース対象一覧");             r += 1
    hdr_row(ws6, r,
            ["No", "種別", "API名 / 対象", "変更種別", "デプロイ方法", "備考"]); r += 1
    for i in range(8):
        data_row(ws6, r, ["", "", "", "", "", ""], stripe=(i % 2 == 1)); r += 1
    r += 1  # 空行
    sec_row(ws6, r, 6, "■ リリース前確認事項");           r += 1
    hdr_row(ws6, r, ["□", "確認内容", "確認者", "結果", "", ""]); r += 1
    for i in range(4):
        data_row(ws6, r, ["□", "", "", "", "", ""],
                 stripe=(i % 2 == 1));                     r += 1
    r += 1
    sec_row(ws6, r, 6, "■ ロールバック手順");             r += 1
    _merge_fill(ws6, r, 1, 6, WHT_FILL, STD_FONT,
                "（ロールバックが必要な場合の手順を記載する）"); r += 1
    r += 3
    sec_row(ws6, r, 6, "■ 本番デプロイ記録");             r += 1
    for k in ["デプロイ日時", "実施者", "検証結果"]:
        kv_row(ws6, r, 6, k);                              r += 1

    path = os.path.join(FOLDER, f"{ISSUE_ID}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
