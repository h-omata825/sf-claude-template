"""
プロジェクト概要書.xlsx を生成する（テンプレート読込方式）。

テンプレート: プロジェクト概要書テンプレート.xlsx（build_basic_doc_template.py で生成）

入力 (docs/ 配下):
  docs/overview/org-profile.md         — 組織・プロジェクト基本情報
  docs/requirements/requirements.md    — 目的・背景
  docs/architecture/system.json        — 外部連携先情報
  docs/catalog/_data-model.md          — オブジェクト関連情報（ER図用）
  docs/flow/usecases.md                — 用語集・UC情報

出力:
  プロジェクト概要書.xlsx（5シート: 表紙/システム概要/業務フロー図/ER図/用語集）
  ※ 図エリアは手動貼り付け用プレースホルダー。テキスト情報のみ自動入力。

Usage:
  python generate_basic_doc.py \\
    --docs-dir <path/to/project/docs> \\
    --output <output/プロジェクト概要書.xlsx> \\
    --author "作成者名" \\
    [--project-name "プロジェクト名"] \\
    [--template <path/to/プロジェクト概要書テンプレート.xlsx>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

DEFAULT_TEMPLATE = Path(__file__).parent / "プロジェクト概要書テンプレート.xlsx"
FONT_NAME = "游ゴシック"
C_FONT_D = "000000"


# ── セル書き込みヘルパー ──────────────────────────────────────────

def _set(ws, row: int, col: int, value: str, wrap: bool = True, size: int = 10):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(name=FONT_NAME, color=C_FONT_D, size=size)
    c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=wrap)


def _set_row(ws, row: int, col_start: int, cols: list[tuple[int, int]], values: list[str]):
    """data行: cols=[(cs,ce),...], values=[str,...] を対応させてセル書き込み"""
    for (cs, _ce), val in zip(cols, values):
        _set(ws, row, cs, val or "")


# ── docs パーサー ─────────────────────────────────────────────────

def _section(text: str, heading: str) -> str:
    m = re.search(rf'##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _table_val(text: str, key: str) -> str:
    m = re.search(rf'\|\s*{re.escape(key)}\s*\|\s*(.+?)\s*\|', text)
    return m.group(1).strip() if m else ""


def parse_org_profile(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return {
        "system_name":   _table_val(text, "システム名") or _table_val(text, "会社名"),
        "project_name":  _table_val(text, "プロジェクト名"),
        "sf_edition":    _table_val(text, "Salesforce Edition") or _table_val(text, "Edition"),
        "start_date":    _table_val(text, "開始日") or _table_val(text, "プロジェクト開始日"),
        "end_date":      _table_val(text, "終了予定日") or _table_val(text, "リリース予定日"),
        "go_live_date":  _table_val(text, "本番公開日"),
        "target_biz":    _table_val(text, "対象業務"),
        "users":         _parse_users(text),
        "stakeholders":  _parse_stakeholders(text),
    }


def _parse_users(text: str) -> list[dict]:
    sec = _section(text, "利用ユーザー")
    if not sec:
        sec = _section(text, "ユーザー")
    rows = []
    for line in sec.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0] and cols[0] not in ("ユーザー区分", "---", "区分"):
            rows.append({
                "category":    cols[0],
                "profile":     cols[1] if len(cols) > 1 else "",
                "count":       cols[2] if len(cols) > 2 else "",
                "main_feature": cols[3] if len(cols) > 3 else "",
            })
    return rows[:8]


def _parse_stakeholders(text: str) -> list[dict]:
    sec = _section(text, "ステークホルダー") or _section(text, "関係者")
    rows = []
    for line in sec.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0] and cols[0] not in ("役割", "---"):
            rows.append({
                "role":   cols[0],
                "name":   cols[1] if len(cols) > 1 else "",
                "note":   cols[2] if len(cols) > 2 else "",
            })
    return rows[:5]


def parse_requirements(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    bg = _section(text, "背景・目的") or _section(text, "目的")
    intro_m = re.match(r'^([^\n\-\*].+?)(?=\n\n|\n[-*]|\Z)', bg, re.DOTALL) if bg else None
    return {
        "purpose": intro_m.group(1).strip() if intro_m else bg[:200],
    }


def parse_system_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        "org_id":      d.get("org_id", ""),
        "instance_url": d.get("instance_url", ""),
        "edition":     d.get("edition") or (d.get("core") or {}).get("name", ""),
        "api_version": d.get("api_version", ""),
        "login_user":  d.get("login_user", ""),
        "externals":   d.get("external_systems", [])[:10],
        "named_creds": d.get("named_credentials", [])[:6],
    }



def parse_data_model(path: Path) -> list[dict]:
    """_data-model.md からオブジェクト関連（ER図用）を抽出"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    rels = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 3 and cols[0] and cols[0] not in ("親オブジェクト", "---"):
            rels.append({
                "parent":  cols[0],
                "rel":     cols[1] if len(cols) > 1 else "",
                "child":   cols[2] if len(cols) > 2 else "",
                "field":   cols[3] if len(cols) > 3 else "",
                "note":    cols[4] if len(cols) > 4 else "",
            })
    return rels[:15]


def parse_glossary(org_profile_path: Path) -> list[dict]:
    """org-profile.md の用語集セクションから用語を抽出"""
    if not org_profile_path.exists():
        return []
    text = org_profile_path.read_text(encoding="utf-8")
    sec = _section(text, "用語集") or _section(text, "Glossary")
    terms = []
    for line in sec.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0] and cols[0] not in ("業務用語", "---", "用語"):
            terms.append({
                "biz_term": cols[0],
                "sf_term":  cols[1] if len(cols) > 1 else "",
                "desc":     cols[2] if len(cols) > 2 else "",
            })
    return terms[:30]


# ── シート書き込み ────────────────────────────────────────────────
# 新テンプレート: 表紙 / システム概要 / 業務フロー図 / ER図 / 用語集
# 図エリアはプレースホルダーのため書き込み不要。テキスト情報のみ自動入力。

_META_VAL_COL = 9  # meta_row: col_label_end+1 = 8+1


def fill_cover(ws, org: dict, req: dict, author: str):
    # build_cover_sheet:
    # margin(1),margin(2),title(3),margin(4),section(5)
    # プロジェクト名(6),システム名(7),目的・背景(8),スコープ対象(9),スコープ対象外(10)
    # 開始日(11),終了予定日(12),本番公開日(13)
    vals = [
        org.get("project_name", ""),
        org.get("system_name", ""),
        req.get("purpose", ""),
        "",  # スコープ（対象）
        "",  # スコープ（対象外）
        org.get("start_date", ""),
        org.get("end_date", ""),
        org.get("go_live_date", ""),
    ]
    for i, val in enumerate(vals):
        _set(ws, 6 + i, _META_VAL_COL, val)

    # 体制テーブル: section(15), header(16), data rows 17..22
    # cols: (2,6) 役割 / (7,16) 氏名 / (17,22) 担当領域 / (23,31) 備考
    stake_cols = [(2, 6), (7, 16), (17, 22), (23, 31)]
    for i, s in enumerate(org.get("stakeholders", [])):
        r = 17 + i
        _set_row(ws, r, 0, stake_cols, [s["role"], s["name"], s.get("domain", ""), s.get("note", "")])


def fill_system_overview(ws, sys_info: dict, req: dict):
    # build_system_overview_sheet:
    # margin(1),margin(2),title(3),margin(4),section(5)
    # 導入背景テキストエリア: rows 6..13（結合済み）→ row6 のみ書き込む
    # 外部連携一覧: section(固定offset後), header, data rows
    _set(ws, 6, GRID_LEFT, req.get("purpose", ""))

    # 外部連携一覧の開始行は:
    # margin(1)+margin(2)+title(3)+margin(4)+section(5)+textarea8行(6-13)+margin(14)+
    # section(15)+diagram19行(16-34)+margin(35)+section(36)+header(37)+data38..
    ext_cols = [(2, 8), (9, 12), (13, 18), (19, 22), (23, 31)]
    for i, ex in enumerate(sys_info.get("externals", [])[:8]):
        r = 38 + i
        _set_row(ws, r, 0, ext_cols, [
            ex.get("name", ""), ex.get("direction", ""),
            ex.get("protocol", ""), ex.get("frequency", ""),
            ex.get("purpose", ""),
        ])


def fill_er(ws, rels: list[dict]):
    # build_er_sheet:
    # margin(1)+margin(2)+title(3)+margin(4)+section(5)+diagram29行(6-34)+margin(35)
    # +section(36)+header(37)+data rows 38..
    rel_cols = [(2, 8), (9, 10), (11, 17), (18, 23), (24, 31)]
    for i, rel in enumerate(rels[:15]):
        r = 38 + i
        _set_row(ws, r, 0, rel_cols, [
            rel["parent"], rel["rel"], rel["child"], rel["field"], rel["note"],
        ])


def fill_glossary(ws, terms: list[dict]):
    # build_glossary_sheet:
    # margin(1)+margin(2)+title(3)+margin(4)+section(5)+header(6)+data rows 7..
    term_cols = [(2, 3), (4, 10), (11, 18), (19, 31)]
    for i, t in enumerate(terms[:30]):
        r = 7 + i
        _set_row(ws, r, 0, term_cols, [str(i + 1), t["biz_term"], t["sf_term"], t["desc"]])


# ── メイン ────────────────────────────────────────────────────────

GRID_LEFT = 2


def generate(docs_dir: Path, output: Path, author: str, project_name: str,
             template: Path = DEFAULT_TEMPLATE):
    if not template.exists():
        print(
            f"ERROR: テンプレートが見つかりません: {template}\n"
            "先に build_basic_doc_template.py を実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    org      = parse_org_profile(docs_dir / "overview" / "org-profile.md")
    req      = parse_requirements(docs_dir / "requirements" / "requirements.md")
    sys_info = parse_system_json(docs_dir / "architecture" / "system.json")
    rels     = parse_data_model(docs_dir / "catalog" / "_data-model.md")
    terms    = parse_glossary(docs_dir / "overview" / "org-profile.md")

    if project_name:
        org["project_name"] = project_name

    wb = load_workbook(str(template))

    fill_cover(wb["表紙"],               org, req, author)
    fill_system_overview(wb["システム概要"], sys_info, req)
    # 業務フロー図・ER図は図エリアが主体のため、テキスト補足のみ
    fill_er(wb["ER図"],                  rels)
    fill_glossary(wb["用語集"],           terms)

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output))
    print(f"saved: {output}")


def main():
    ap = argparse.ArgumentParser(description="プロジェクト概要書.xlsx 生成")
    ap.add_argument("--docs-dir",     required=True, help="docs/ フォルダのパス")
    ap.add_argument("--output",       required=True, help="出力先 .xlsx パス")
    ap.add_argument("--author",       default="",    help="作成者名")
    ap.add_argument("--project-name", default="",    help="プロジェクト名（省略時はorg-profile.mdから取得）")
    ap.add_argument("--template",     default=str(DEFAULT_TEMPLATE), help="テンプレート.xlsxパス")
    args = ap.parse_args()
    generate(
        docs_dir=Path(args.docs_dir),
        output=Path(args.output),
        author=args.author,
        project_name=args.project_name,
        template=Path(args.template),
    )


if __name__ == "__main__":
    main()
