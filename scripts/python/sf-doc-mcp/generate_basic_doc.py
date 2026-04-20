"""
プロジェクト概要書.xlsx を生成する（テンプレート読込方式）。

テンプレート: プロジェクト概要書テンプレート.xlsx（build_basic_doc_template.py で生成）

入力 (docs/ 配下):
  docs/overview/org-profile.md         — 組織・プロジェクト基本情報
  docs/requirements/requirements.md    — 目的・背景
  docs/architecture/system.json        — SF組織情報・外部連携
  docs/flow/usecases.md                — ユースケース一覧
  docs/catalog/_index.md               — オブジェクト一覧（カタログ）

出力:
  プロジェクト概要書.xlsx（5シート）

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


def parse_usecases(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    ucs = []
    for m in re.finditer(
        r'^##\s+(UC-\d+)[:：\s]*(.+)$((?:.*\n)*?)(?=^##\s|\Z)',
        text, re.MULTILINE,
    ):
        uc_id, title, body = m.group(1), m.group(2).strip(), m.group(3)
        trigger = ""
        freq = ""
        objs = ""
        for b in re.finditer(r'^-\s+([^:：]+)[:：]\s*(.+)$', body, re.MULTILINE):
            k, v = b.group(1).strip(), b.group(2).strip()
            if "トリガー" in k or "契機" in k:
                trigger = v[:50]
            elif "頻度" in k:
                freq = v[:20]
            elif "オブジェクト" in k or "主要" in k:
                objs = v[:40]
        ucs.append({"id": uc_id, "name": title, "trigger": trigger, "freq": freq, "objects": objs})
    return ucs[:15]


def parse_catalog(catalog_dir: Path) -> list[dict]:
    index_path = catalog_dir / "_index.md"
    if not index_path.exists():
        return []
    text = index_path.read_text(encoding="utf-8")
    objs = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 2 and cols[0] and cols[0] not in ("API名", "---", "オブジェクト"):
            api = cols[0]
            label = cols[1] if len(cols) > 1 else ""
            kind = cols[2] if len(cols) > 2 else ""
            count = cols[3] if len(cols) > 3 else ""
            overview = cols[4] if len(cols) > 4 else ""
            objs.append({"api": api, "label": label, "type": kind, "count": count, "overview": overview})
    return objs[:20]


# ── シート書き込み ────────────────────────────────────────────────

# シート1の各メタ行（build_basic_doc_template.py の build_revision_sheet と同順）
# 行番号: margin(1), margin(2), title(3), margin(4),
#         プロジェクト名(5), 作成日(6), 最終更新日(7), バージョン(8), 作成者(9)
_SH1_META = [5, 6, 7, 8, 9]
_META_VAL_COL = 9  # col_label_end+1 = 8+1

def fill_revision(ws, project_name: str, author: str):
    today = date.today().strftime("%Y-%m-%d")
    _set(ws, 5, _META_VAL_COL, project_name)
    _set(ws, 6, _META_VAL_COL, today)
    _set(ws, 7, _META_VAL_COL, today)
    _set(ws, 8, _META_VAL_COL, "1.0")
    _set(ws, 9, _META_VAL_COL, author)


def fill_overview(ws, org: dict, req: dict):
    # Sheet2 build_overview_sheet:
    # margin(1), margin(2), title(3), margin(4), section(5),
    # システム名(6), プロジェクト名(7), 目的・背景(8), 対象業務(9),
    # Edition(10), 開始日(11), 終了予定日(12), 本番公開日(13)
    vals = [
        org.get("system_name", ""),
        org.get("project_name", ""),
        req.get("purpose", ""),
        org.get("target_biz", ""),
        org.get("sf_edition", ""),
        org.get("start_date", ""),
        org.get("end_date", ""),
        org.get("go_live_date", ""),
    ]
    for i, val in enumerate(vals):
        _set(ws, 6 + i, _META_VAL_COL, val)

    # 利用ユーザーテーブル:
    # section(15), header(16), data rows 17..
    # cols: (2,8) ユーザー区分 / (9,16) プロファイル / (17,22) 想定人数 / (23,31) 主な利用機能
    user_cols = [(2, 8), (9, 16), (17, 22), (23, 31)]
    for i, u in enumerate(org.get("users", [])):
        r = 17 + i
        _set_row(ws, r, 0, user_cols, [u["category"], u["profile"], u["count"], u["main_feature"]])

    # 関係者テーブル:
    # 利用ユーザー8行後 + margin + section + header = row 17+8+2+2 = 29
    # section(26), header(27), data rows 28..
    # cols: (2,8) 役割 / (9,18) 氏名 / (19,31) 備考
    stake_cols = [(2, 8), (9, 18), (19, 31)]
    for i, s in enumerate(org.get("stakeholders", [])):
        r = 29 + i
        _set_row(ws, r, 0, stake_cols, [s["role"], s["name"], s["note"]])


def fill_system(ws, sys_info: dict):
    # Sheet3 build_system_sheet:
    # margin(1), margin(2), title(3), margin(4), section(5),
    # 組織ID(6), インスタンスURL(7), Edition(8), APIバージョン(9), 接続ユーザー(10)
    vals = [
        sys_info.get("org_id", ""),
        sys_info.get("instance_url", ""),
        sys_info.get("edition", ""),
        sys_info.get("api_version", ""),
        sys_info.get("login_user", ""),
    ]
    for i, val in enumerate(vals):
        _set(ws, 6 + i, _META_VAL_COL, val)

    # 外部連携一覧: section(12), header(13), data rows 14..23
    # cols: (2,8) 連携先 / (9,14) 方向 / (15,20) 方式 / (21,24) 頻度 / (25,31) 目的
    ext_cols = [(2, 8), (9, 14), (15, 20), (21, 24), (25, 31)]
    for i, ex in enumerate(sys_info.get("externals", [])[:10]):
        r = 14 + i
        name = ex.get("name", "")
        direction = ex.get("direction", "")
        protocol = ex.get("protocol", "")
        frequency = ex.get("frequency", "")
        purpose = ex.get("purpose", "")
        _set_row(ws, r, 0, ext_cols, [name, direction, protocol, frequency, purpose])

    # エンドポイント: section(25), header(26), data rows 27..32
    # cols: (2,10) DeveloperName / (11,31) Endpoint URL
    nc_cols = [(2, 10), (11, 31)]
    for i, nc in enumerate(sys_info.get("named_creds", [])[:6]):
        r = 27 + i
        dev_name = nc.get("developer_name", nc.get("DeveloperName", ""))
        endpoint = nc.get("endpoint", nc.get("Endpoint", ""))
        _set_row(ws, r, 0, nc_cols, [dev_name, endpoint])


def fill_objects(ws, objects: list[dict]):
    # Sheet4 build_object_sheet:
    # margin(1), margin(2), title(3), margin(4), section(5), header(6), data 7..26
    # cols: (2,6) API名 / (7,14) オブジェクト名 / (15,18) 種別 / (19,23) 件数 / (24,31) 概要
    obj_cols = [(2, 6), (7, 14), (15, 18), (19, 23), (24, 31)]
    for i, o in enumerate(objects[:20]):
        r = 7 + i
        _set_row(ws, r, 0, obj_cols, [o["api"], o["label"], o["type"], o["count"], o["overview"]])


def fill_flow(ws, usecases: list[dict]):
    # Sheet5 build_flow_sheet:
    # margin(1), margin(2), title(3), margin(4), section(5), header(6), data 7..21
    # cols: (2,5) UC番号 / (6,14) UC名 / (15,19) トリガー / (20,23) 頻度 / (24,31) 主要オブジェクト
    uc_cols = [(2, 5), (6, 14), (15, 19), (20, 23), (24, 31)]
    for i, uc in enumerate(usecases[:15]):
        r = 7 + i
        _set_row(ws, r, 0, uc_cols, [uc["id"], uc["name"], uc["trigger"], uc["freq"], uc["objects"]])


# ── メイン ────────────────────────────────────────────────────────

def generate(docs_dir: Path, output: Path, author: str, project_name: str,
             template: Path = DEFAULT_TEMPLATE):
    if not template.exists():
        print(
            f"ERROR: テンプレートが見つかりません: {template}\n"
            "先に build_basic_doc_template.py を実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    org  = parse_org_profile(docs_dir / "overview" / "org-profile.md")
    req  = parse_requirements(docs_dir / "requirements" / "requirements.md")
    sys_info = parse_system_json(docs_dir / "architecture" / "system.json")
    ucs  = parse_usecases(docs_dir / "flow" / "usecases.md")
    objs = parse_catalog(docs_dir / "catalog")

    if project_name:
        org["project_name"] = project_name

    wb = load_workbook(str(template))

    fill_revision(wb["改版履歴"],       org.get("project_name", ""), author)
    fill_overview(wb["プロジェクト概要"], org, req)
    fill_system(wb["システム構成"],      sys_info)
    fill_objects(wb["オブジェクト構成"], objs)
    fill_flow(wb["業務フロー概要"],      ucs)

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
