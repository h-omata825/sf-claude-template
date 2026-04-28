# -*- coding: utf-8 -*-
"""backlog-xlsx / create_records.py
対応記録.xlsx を生成する（Phase 3 完了直後に MD3点を読んで全シート埋め）

Usage:
    python create_records.py \\
      --folder FOLDER --issue-id ID \\
      --investigation PATH \\
      --approach-plan PATH \\
      --implementation-plan PATH
"""

import argparse
import datetime
import os
import re
import sys
from pathlib import Path

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, PatternFill
except ImportError:
    print("[ERROR] openpyxl がインストールされていません。`pip install openpyxl` を実行してください。")
    sys.exit(1)

TEMPLATE = Path(__file__).parent / "対応記録テンプレート.xlsx"
WRAP = Alignment(wrap_text=True, vertical="top")
STRIPE_A = PatternFill("solid", fgColor="FFFFFF")
STRIPE_B = PatternFill("solid", fgColor="F2F7FB")


# ── MD パースユーティリティ ─────────────────────────────────────────────────

def read_md(path):
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return ""


def extract_section(md, *headings):
    """指定見出し（## または ###）のセクション本文を返す。複数見出しは先にマッチしたものを使用。"""
    for h in headings:
        pat = r"^#{1,3}\s+" + re.escape(h) + r"\s*$"
        m = re.search(pat, md, re.MULTILINE)
        if m:
            start = m.end()
            rest = md[start:]
            end_m = re.search(r"^#{1,3}\s", rest, re.MULTILINE)
            body = rest[: end_m.start()] if end_m else rest
            return body.strip()
    return ""


def parse_md_table(section_text):
    """Markdown テーブルを [{col_name: value, ...}] のリストに変換する。"""
    rows = []
    headers = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.match(r"^[-: ]+$", c) for c in cells):
            continue  # 区切り行
        if not headers:
            headers = cells
        else:
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_checklist(section_text):
    """- [ ] または - [x] の行からチェックリスト文字列のリストを返す。"""
    items = []
    for line in section_text.splitlines():
        m = re.match(r"^\s*-\s+\[[ xX]\]\s+(.+)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def parse_numbered_list(section_text):
    """1. 2. ... の番号付きリストを文字列リストで返す。"""
    items = []
    for line in section_text.splitlines():
        m = re.match(r"^\s*\d+[\.\)]\s+(.+)", line)
        if m:
            items.append(m.group(1).strip())
        elif line.strip() and not re.match(r"^#", line) and items:
            # 継続行
            items[-1] += " " + line.strip()
    return items


def extract_metadata(md, key):
    """## 課題サマリー 等の key: value 形式から値を取る。"""
    m = re.search(rf"^{re.escape(key)}\s*[:|]\s*(.+)", md, re.MULTILINE)
    return m.group(1).strip() if m else ""


# ── セル書き込みユーティリティ ──────────────────────────────────────────────

def wset(ws, row, col, value, stripe=None):
    cell = ws.cell(row=row, column=col, value=value)
    cell.alignment = WRAP
    if stripe:
        cell.fill = stripe
    return cell


def write_rows(ws, data_rows, start_row, col_names, max_rows=None):
    """data_rows（list of dict or list of list）を start_row から書き込む。max_rows を超えたら動的増行。"""
    for i, row_data in enumerate(data_rows):
        if max_rows and i >= max_rows:
            # 最終行の書式を複製してから追記（簡易）
            pass
        r = start_row + i
        fill = STRIPE_A if (i % 2 == 0) else STRIPE_B
        if isinstance(row_data, dict):
            for j, col in enumerate(col_names, start=1):
                wset(ws, r, j, row_data.get(col, ""), fill)
        else:
            for j, val in enumerate(row_data, start=1):
                wset(ws, r, j, val, fill)


# ── サマリー・経緯シート ────────────────────────────────────────────────────

def fill_summary(ws, args, inv_md, approach_md, impl_md):
    # 課題情報
    issue_id   = args.issue_id
    title      = extract_metadata(inv_md, "件名") or extract_metadata(inv_md, "タイトル") or ""
    priority   = extract_metadata(inv_md, "優先度") or ""
    deadline   = extract_metadata(inv_md, "期限") or ""
    issue_type = extract_metadata(inv_md, "種別") or extract_metadata(inv_md, "課題種別") or ""
    summary_bg = extract_section(inv_md, "概要", "背景", "背景・要件", "課題概要")
    if not summary_bg:
        # 最初の段落を背景として使う
        paras = [p.strip() for p in inv_md.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        summary_bg = paras[0][:200] if paras else ""

    wset(ws, 3, 2, issue_id)
    wset(ws, 4, 2, title)
    wset(ws, 5, 2, f"優先度: {priority} / 期限: {deadline}")
    wset(ws, 6, 2, issue_type)
    wset(ws, 7, 2, "対応中")
    wset(ws, 8, 2, summary_bg)

    # タイムライン 3 行（Phase 1〜3）
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    # Phase 1: 調査完了
    inv_result = extract_section(inv_md, "根本原因", "調査結果", "原因", "調査・まとめ")
    inv_result_oneliner = inv_result.replace("\n", " ")[:80] if inv_result else "調査完了"
    # Phase 2: 対応方針確定
    approach_adopted = extract_section(approach_md, "採用方針")
    approach_oneliner = approach_adopted.replace("\n", " ")[:80] if approach_adopted else "対応方針確定"
    # Phase 3: 実装方針確定
    impl_summary = extract_section(impl_md, "実装方針まとめ", "概要", "方針まとめ")
    if not impl_summary:
        change_files = extract_section(impl_md, "変更ファイル一覧", "変更ファイル")
        impl_summary = change_files[:80] if change_files else "実装方針確定"
    impl_oneliner = impl_summary.replace("\n", " ")[:80]

    tl_rows = [
        (1, now, "Claude", "調査", f"調査完了: {inv_result_oneliner}", ""),
        (2, now, "ユーザ", "方針策定", f"対応方針確定: {approach_oneliner}", ""),
        (3, now, "ユーザ", "実装方針確定", f"全判断ポイント確定: {impl_oneliner}", ""),
    ]
    for i, row in enumerate(tl_rows):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, val in enumerate(row, start=1):
            wset(ws, 13 + i, j, val, fill)


# ── 対応方針シート ──────────────────────────────────────────────────────────

def fill_approach(ws, approach_md):
    # 方針比較テーブル（r4-6）
    table_text = extract_section(approach_md, "方針比較", "方針比較テーブル", "対応方針比較")
    rows = parse_md_table(table_text)
    col_order = ["案No", "方針名", "概要", "メリット", "デメリット", "リスク", "工数"]
    for i, row in enumerate(rows[:3]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(col_order, start=1):
            wset(ws, 4 + i, j, row.get(col, ""), fill)

    # 採用方針（r8）
    adopted = extract_section(approach_md, "採用方針")
    if adopted:
        wset(ws, 8, 1, adopted)

    # 実施前確認事項（r22-25）
    checks = parse_checklist(extract_section(approach_md, "実施前確認事項", "確認事項", "事前確認"))
    for i, item in enumerate(checks[:4]):
        wset(ws, 22 + i, 1, "□")
        wset(ws, 22 + i, 2, item)

    # 懸念事項（r28-30）
    concerns_text = extract_section(approach_md, "懸念事項", "リスク・懸念事項")
    concerns = parse_numbered_list(concerns_text)
    if not concerns:
        concerns = [l.strip().lstrip("- ") for l in concerns_text.splitlines() if l.strip().startswith("-")]
    for i, item in enumerate(concerns[:3]):
        wset(ws, 28 + i, 1, item)


# ── 調査・影響範囲シート ────────────────────────────────────────────────────

def fill_investigation(ws, inv_md):
    # 仮説検証（r4-9）
    rows = parse_md_table(extract_section(inv_md, "仮説検証", "仮説・検証"))
    for i, row in enumerate(rows[:6]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["No", "仮説内容", "検証方法", "検証結果", "判定"], start=1):
            wset(ws, 4 + i, j, row.get(col, ""), fill)

    # コード根拠（r12-17）
    rows = parse_md_table(extract_section(inv_md, "コード根拠", "コード根拠テーブル"))
    for i, row in enumerate(rows[:6]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["ファイル名", "行番号", "コード内容", "説明"], start=1):
            wset(ws, 12 + i, j, row.get(col, ""), fill)

    # 影響範囲（r20-25）
    rows = parse_md_table(extract_section(inv_md, "影響範囲", "影響範囲テーブル"))
    for i, row in enumerate(rows[:6]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["種別", "対象", "内容", "根拠"], start=1):
            wset(ws, 20 + i, j, row.get(col, ""), fill)

    # 関連コンポーネント（r29-33）
    rows = parse_md_table(extract_section(inv_md, "関連コンポーネント", "関連コンポーネント一覧"))
    for i, row in enumerate(rows[:5]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["種別", "名前", "役割", "調査結果"], start=1):
            wset(ws, 29 + i, j, row.get(col, ""), fill)


# ── 対応内容シート ──────────────────────────────────────────────────────────

def fill_content(ws, impl_md):
    # 変更ファイル一覧（r9-12）
    rows = parse_md_table(extract_section(impl_md, "変更ファイル一覧", "変更ファイル"))
    for i, row in enumerate(rows[:4]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["No", "ファイルパス", "変更種別", "変更概要"], start=1):
            wset(ws, 9 + i, j, row.get(col, ""), fill)

    # Before/After（r14）— 実装後に記入する旨の案内を入れる
    wset(ws, 14, 1, "実装完了後、各ファイルの変更前後を記載する")

    # 影響確認チェックリスト（r21-25）
    checks = parse_checklist(extract_section(impl_md, "影響確認チェックリスト", "影響確認"))
    for i, item in enumerate(checks[:5]):
        wset(ws, 21 + i, 1, "□")
        wset(ws, 21 + i, 2, item)


# ── テスト・検証記録シート ──────────────────────────────────────────────────

def fill_test(ws, impl_md):
    # テスト方針（r3-4）
    policy = extract_section(impl_md, "テスト方針", "テスト概要")
    if not policy:
        policy = "実装前後での動作確認を行う。実装前は現状把握、実装後は修正確認。"
    wset(ws, 3, 1, policy)

    # テストテーブル（r7〜）
    rows = parse_md_table(extract_section(impl_md, "テスト仕様", "テストケース", "テスト仕様テーブル"))
    for i, row in enumerate(rows):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        # 列: No | 区分(タイミング) | テスト項目(確認観点) | 確認方法(確認手順) | 期待結果 | 実際の結果 | 判定 | 根拠
        vals = [
            row.get("No", str(i + 1)),
            row.get("タイミング", row.get("区分", "")),
            row.get("確認観点", row.get("テスト項目", "")),
            row.get("確認手順", row.get("確認方法", "")),
            row.get("期待結果", ""),
            "",  # 実際の結果（実装後記入）
            "",  # 判定（実装後記入）
            row.get("エビデンス取得方法", row.get("根拠", "")),
        ]
        for j, val in enumerate(vals, start=1):
            wset(ws, 7 + i, j, val, fill)


# ── リリース・ロールバックシート ────────────────────────────────────────────

def fill_release(ws, impl_md):
    # リリース対象（r4-6）
    rows = parse_md_table(extract_section(impl_md, "リリース対象", "リリース対象一覧"))
    for i, row in enumerate(rows[:3]):
        fill = STRIPE_A if i % 2 == 0 else STRIPE_B
        for j, col in enumerate(["No", "種別", "API名", "変更種別", "デプロイ方法", "備考"], start=1):
            wset(ws, 4 + i, j, row.get(col, ""), fill)

    # リリース前確認事項（r9-13）
    checks = parse_checklist(extract_section(impl_md, "リリース前確認事項", "リリース前確認", "デプロイ前確認"))
    for i, item in enumerate(checks[:5]):
        wset(ws, 9 + i, 1, "□")
        wset(ws, 9 + i, 2, item)

    # デプロイ手順（r15-19）
    steps = parse_numbered_list(extract_section(impl_md, "デプロイ手順", "リリース手順"))
    for i, step in enumerate(steps[:5]):
        wset(ws, 15 + i, 1, f"{i + 1}. {step}")

    # デプロイ後確認事項（r22-26）
    post_checks = parse_checklist(extract_section(impl_md, "デプロイ後確認事項", "リリース後確認", "デプロイ後確認"))
    for i, item in enumerate(post_checks[:5]):
        wset(ws, 22 + i, 1, "□")
        wset(ws, 22 + i, 2, item)

    # 注意事項（r28-30）
    notes_text = extract_section(impl_md, "注意事項", "リスク・注意事項", "注意点")
    notes = parse_numbered_list(notes_text)
    if not notes:
        notes = [l.strip().lstrip("- ") for l in notes_text.splitlines() if l.strip().startswith("-")]
    for i, item in enumerate(notes[:3]):
        wset(ws, 28 + i, 1, item)

    # ロールバック手順（r32-37）
    rb_steps = parse_numbered_list(extract_section(impl_md, "ロールバック手順"))
    for i, step in enumerate(rb_steps[:6]):
        wset(ws, 32 + i, 1, f"{i + 1}. {step}")


# ── main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="対応記録.xlsx を生成する（Phase 3 完了後の全シート埋め版）")
    parser.add_argument("--folder",              required=True)
    parser.add_argument("--issue-id",            required=True, dest="issue_id")
    parser.add_argument("--investigation",       required=True, dest="investigation",
                        help="docs/logs/{issueID}/investigation.md のパス")
    parser.add_argument("--approach-plan",       required=True, dest="approach_plan",
                        help="docs/logs/{issueID}/approach-plan.md のパス")
    parser.add_argument("--implementation-plan", required=True, dest="implementation_plan",
                        help="docs/logs/{issueID}/implementation-plan.md のパス")
    args = parser.parse_args()

    if not TEMPLATE.exists():
        print(f"[ERROR] テンプレートが見つかりません: {TEMPLATE}")
        sys.exit(1)

    inv_md    = read_md(args.investigation)
    app_md    = read_md(args.approach_plan)
    impl_md   = read_md(args.implementation_plan)

    missing = []
    if not inv_md:
        missing.append(args.investigation)
    if not app_md:
        missing.append(args.approach_plan)
    if not impl_md:
        missing.append(args.implementation_plan)
    if missing:
        print(f"[ERROR] 以下の MD ファイルが見つかりません:\n" + "\n".join(f"  {p}" for p in missing))
        sys.exit(1)

    os.makedirs(args.folder, exist_ok=True)
    wb = load_workbook(TEMPLATE)

    fill_summary(wb["サマリー・経緯"], args, inv_md, app_md, impl_md)
    fill_approach(wb["対応方針"], app_md)
    fill_investigation(wb["調査・影響範囲"], inv_md)
    fill_content(wb["対応内容"], impl_md)
    fill_test(wb["テスト・検証記録"], impl_md)
    fill_release(wb["リリース・ロールバック"], impl_md)

    path = os.path.join(args.folder, f"{args.issue_id}_対応記録.xlsx")
    wb.save(path)
    print(f"生成完了: {path}")


if __name__ == "__main__":
    main()
