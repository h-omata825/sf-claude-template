#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
プロジェクト資料 PPTX 生成スクリプト（概要＋システム構成図＋業務フロー図UC別 統合版）

入力:
  docs/overview/org-profile.md            — 会社・組織プロフィール
  docs/requirements/requirements.md       — 背景・目的・スコープ・機能要件
  docs/architecture/system.json           — システム構成図（新フォーマット）
  docs/flow/usecases.md                   — 業務ユースケース一覧
  docs/flow/swimlanes.json                — 業務フロー図（複数UC対応・新フォーマット）

出力:
  プロジェクト資料.pptx（表紙・目次・プロジェクト概要・システム構成図・業務フロー図群）

Usage:
  python generate_project_doc.py \\
    --docs-dir <path/to/project/docs> \\
    --output-dir <output dir> \\
    --author "作成者名"
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


# ── ソース解析 ──────────────────────────────────────────────────────────────

def parse_org_profile(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")

    def _val(key: str) -> str:
        m = re.search(rf'\|\s*{re.escape(key)}\s*\|\s*(.+?)\s*\|', text)
        return m.group(1).strip() if m else ""

    return {
        "company":    _val("会社名"),
        "industry":   _val("業種"),
        "business":   _val("主な事業"),
        "sf_purpose": _val("Salesforce利用目的"),
    }


def _extract_section(text: str, pattern: str) -> str:
    m = re.search(rf'##\s+{pattern}\s*\n(.*?)(?=\n##|\Z)', text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _bullets(text: str) -> list:
    return [m.group(1).strip()
            for m in re.finditer(r'^[-*]\s+(.+)$', text, re.MULTILINE)]


def parse_requirements(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    result = {}

    bg = _extract_section(text, r"背景・目的")
    if bg:
        intro_m = re.match(r'^([^\n\-\*].+?)(?=\n\n|\n[-*]|\Z)', bg, re.DOTALL)
        result["background_intro"]   = intro_m.group(1).strip() if intro_m else ""
        result["background_bullets"] = _bullets(bg)

    scope = _extract_section(text, r"プロジェクトスコープ")
    if scope:
        in_m  = re.search(r'###\s*対象(?!外)(.*?)(?=\n###|\Z)', scope, re.DOTALL)
        out_m = re.search(r'###\s*対象外(.*?)(?=\n###|\Z)', scope, re.DOTALL)
        result["in_scope"]  = _bullets(in_m.group(1))  if in_m  else []
        result["out_scope"] = _bullets(out_m.group(1)) if out_m else []

    fr_rows = []
    fr_sec = _extract_section(text, r"機能要件.*?")
    for line in fr_sec.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 4 and re.match(r'FR-\d+', cols[0]):
            fr_rows.append([cols[0], cols[1], cols[2], cols[3]])
    result["fr_rows"] = fr_rows[:20]

    return result


def parse_system_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_usecases(path: Path) -> list:
    """usecases.md から UC 一覧（id, title, trigger 等）を抽出。"""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    usecases = []
    for m in re.finditer(
        r'^##\s+(UC-\d+)[:：\s]*(.+)$((?:.*\n)*?)(?=^##\s|\Z)',
        text, re.MULTILINE,
    ):
        uc_id, title, body = m.group(1), m.group(2).strip(), m.group(3)
        uc = {"id": uc_id, "title": title, "items": []}
        for b in re.finditer(r'^-\s+([^:：]+)[:：]\s*(.+)$', body, re.MULTILINE):
            uc["items"].append((b.group(1).strip(), b.group(2).strip()))
        usecases.append(uc)
    return usecases


def parse_swimlanes(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── システム構成図スライド生成 ──────────────────────────────────────────────

_LANE_TYPE_TO_STYLE = {
    "external_actor":  "accent",
    "internal_actor":  "secondary",
    "system":          "primary",
    "external_system": "light",
}

_SYS_PROTOCOL_SHORT = {
    "REST": "REST", "SOAP": "SOAP", "Bulk": "Bulk API",
    "Platform Event": "PE", "File": "File",
}


def build_system_slide(system: dict) -> dict:
    """system.json → diagram layout スライド。
    中央に core、左に actors、右に external_systems、下に data_stores。
    """
    title = system.get("system_name") or "システム構成図"
    core  = system.get("core") or {"name": "Salesforce", "role": ""}
    actors         = system.get("actors", [])[:6]
    external_syss  = system.get("external_systems", [])[:6]
    data_stores    = system.get("data_stores", [])[:4]
    touchpoints    = system.get("touchpoints", [])[:3]

    boxes, arrows = [], []
    # Slide canvas: x 0.3..13.0, y 1.2..7.0
    CENTER_X, CENTER_Y = 6.65, 4.0
    CORE_W, CORE_H = 3.0, 1.3

    # Core box
    core_label = core.get("name", "Salesforce")
    if core.get("role"):
        core_label += f"\n{core['role'][:30]}"
    boxes.append({
        "id": "core", "label": core_label,
        "x": CENTER_X - CORE_W / 2, "y": CENTER_Y - CORE_H / 2,
        "w": CORE_W, "h": CORE_H, "style": "primary",
    })

    # Actors (left column)
    if actors:
        ax = 0.6
        aw = 2.3
        ah = 0.8
        total_h = len(actors) * ah + (len(actors) - 1) * 0.2
        ay0 = CENTER_Y - total_h / 2
        for i, a in enumerate(actors):
            aid = f"actor{i}"
            label = a.get("name", f"利用者{i+1}")
            if a.get("count"):
                label += f"\n({a['count']}名)"
            y = ay0 + i * (ah + 0.2)
            boxes.append({
                "id": aid, "label": label,
                "x": ax, "y": y, "w": aw, "h": ah, "style": "secondary",
            })
            arrows.append({
                "from": aid, "to": "core",
                "side_from": "right", "side_to": "left",
                "label": (a.get("channels") or [""])[0] if a.get("channels") else "",
            })

    # External systems (right column)
    if external_syss:
        ex_x = 10.0
        ex_w = 2.7
        ex_h = 0.9
        total_h = len(external_syss) * ex_h + (len(external_syss) - 1) * 0.2
        ey0 = CENTER_Y - total_h / 2
        for i, ex in enumerate(external_syss):
            eid = f"ext{i}"
            label = ex.get("name", f"外部{i+1}")
            if ex.get("purpose"):
                label += f"\n{ex['purpose'][:24]}"
            y = ey0 + i * (ex_h + 0.2)
            boxes.append({
                "id": eid, "label": label,
                "x": ex_x, "y": y, "w": ex_w, "h": ex_h, "style": "light",
            })
            direction = ex.get("direction", "out")
            proto = _SYS_PROTOCOL_SHORT.get(ex.get("protocol", ""), ex.get("protocol", ""))
            freq = ex.get("frequency", "")
            lbl_parts = [x for x in [proto, freq] if x]
            arrow_label = " / ".join(lbl_parts)
            if direction == "in":
                arrows.append({
                    "from": eid, "to": "core",
                    "side_from": "left", "side_to": "right",
                    "label": arrow_label,
                })
            elif direction == "both":
                arrows.append({
                    "from": "core", "to": eid,
                    "side_from": "right", "side_to": "left",
                    "label": arrow_label, "bidirectional": True,
                })
            else:
                arrows.append({
                    "from": "core", "to": eid,
                    "side_from": "right", "side_to": "left",
                    "label": arrow_label,
                })

    # Data stores (bottom)
    if data_stores:
        ds_w = 2.2
        ds_h = 0.7
        total_w = len(data_stores) * ds_w + (len(data_stores) - 1) * 0.3
        dx0 = CENTER_X - total_w / 2
        dy = CENTER_Y + CORE_H / 2 + 0.9
        for i, ds in enumerate(data_stores):
            did = f"ds{i}"
            label = ds.get("name", f"データ{i+1}")
            if ds.get("purpose"):
                label += f"\n{ds['purpose'][:20]}"
            x = dx0 + i * (ds_w + 0.3)
            boxes.append({
                "id": did, "label": label,
                "x": x, "y": dy, "w": ds_w, "h": ds_h, "style": "light",
            })
            arrows.append({
                "from": "core", "to": did,
                "side_from": "bottom", "side_to": "top", "label": "",
            })

    # Touchpoints (top)
    if touchpoints:
        tp_w = 2.0
        tp_h = 0.6
        total_w = len(touchpoints) * tp_w + (len(touchpoints) - 1) * 0.3
        tx0 = CENTER_X - total_w / 2
        ty = CENTER_Y - CORE_H / 2 - 0.9
        for i, tp in enumerate(touchpoints):
            tid = f"tp{i}"
            label = tp.get("name", f"接点{i+1}")
            if tp.get("platform"):
                label += f"\n{tp['platform'][:20]}"
            x = tx0 + i * (tp_w + 0.3)
            boxes.append({
                "id": tid, "label": label,
                "x": x, "y": ty, "w": tp_w, "h": tp_h, "style": "accent",
            })
            arrows.append({
                "from": tid, "to": "core",
                "side_from": "bottom", "side_to": "top", "label": "",
            })

    return {
        "layout": "diagram",
        "title":  "システム構成図",
        "elements": {"boxes": boxes, "arrows": arrows},
    }


# ── Swimlane 変換（新スキーマ → build_swimlane elements） ─────────────────

def _assign_cols(steps: list, transitions: list) -> dict:
    """steps と transitions から各ステップの col（1始まり）を決定する。
    最長パス層化。孤立ノードは col=1。
    """
    step_ids = [s["id"] for s in steps]
    edges = [(t["from"], t["to"]) for t in transitions
             if t["from"] in step_ids and t["to"] in step_ids]
    incoming = {sid: 0 for sid in step_ids}
    succ = {sid: [] for sid in step_ids}
    for a, b in edges:
        incoming[b] += 1
        succ[a].append(b)
    col = {sid: 1 for sid in step_ids}
    # Kahn で最長パス
    from collections import deque
    q = deque([sid for sid, n in incoming.items() if n == 0])
    visited = 0
    indeg = dict(incoming)
    while q:
        u = q.popleft()
        visited += 1
        for v in succ[u]:
            if col[v] < col[u] + 1:
                col[v] = col[u] + 1
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return col


def convert_new_swimlane(flow: dict) -> dict:
    """新スキーマ flow → build_swimlane elements。"""
    lanes_in = flow.get("lanes", [])
    steps_in = flow.get("steps", [])
    trans_in = flow.get("transitions", [])

    lanes = []
    for ln in lanes_in:
        name = ln.get("name") or ln.get("label") or ""
        lanes.append({
            "id":    name,
            "label": name,
            "style": _LANE_TYPE_TO_STYLE.get(ln.get("type", ""), "light"),
        })

    col_map = _assign_cols(steps_in, trans_in)

    steps = []
    for s in steps_in:
        sid = s["id"]
        label_parts = [s.get("title", "")]
        if s.get("trigger"):
            label_parts.append(f"契機: {s['trigger']}")
        if s.get("output"):
            label_parts.append(f"→ {s['output']}")
        steps.append({
            "id":    str(sid),
            "lane":  s.get("lane", ""),
            "col":   col_map.get(sid, 1),
            "num":   sid if isinstance(sid, int) else None,
            "label": "\n".join(p for p in label_parts if p),
            "style": "white",
        })

    arrows = []
    for t in trans_in:
        arrows.append({
            "from":  str(t["from"]),
            "to":    str(t["to"]),
            "label": t.get("condition", ""),
        })

    return {"lanes": lanes, "steps": steps, "arrows": arrows}


# ── スライド組み立て ───────────────────────────────────────────────────────

_FLOW_TYPE_ORDER = {"overall": 0, "usecase": 1, "exception": 2, "dataflow": 3}


def build_json(org: dict, req: dict, system: dict, usecases: list,
               swimlanes: dict, author: str) -> dict:
    company = org.get("company", "")
    today   = datetime.date.today().strftime("%Y年%m月")

    # 目次構築用
    toc_items = []
    slides = []

    # ── 1. プロジェクト概要 ──
    toc_items.append({"label": "1. プロジェクト概要", "target": "プロジェクト概要"})
    slides.append({"layout": "section", "title": "プロジェクト概要"})

    bg_bullets = []
    if req.get("background_intro"):
        bg_bullets.append(req["background_intro"])
    bg_bullets += req.get("background_bullets", [])
    if bg_bullets:
        slides.append({
            "layout": "bullets", "title": "背景・目的",
            "bullets": bg_bullets[:8],
        })

    # 会社情報
    info_rows = []
    for k, v in [
        ("会社名", org.get("company", "")),
        ("業種",   org.get("industry", "")),
        ("主な事業", org.get("business", "")),
        ("Salesforce利用目的", org.get("sf_purpose", "")),
    ]:
        if v:
            info_rows.append([k, v])
    if info_rows:
        slides.append({
            "layout": "table", "title": "プロジェクト基本情報",
            "table": {
                "headers": ["項目", "内容"], "col_widths": [2.5, 9.5],
                "rows": info_rows,
            },
        })

    # スコープ
    scope_rows = []
    for item in req.get("in_scope", []):
        scope_rows.append(["対象", item])
    for item in req.get("out_scope", []):
        scope_rows.append(["対象外", item])
    if scope_rows:
        slides.append({
            "layout": "table", "title": "プロジェクトスコープ",
            "table": {
                "headers": ["区分", "内容"], "col_widths": [1.5, 10.5],
                "rows": scope_rows[:18],
            },
        })

    # ── 2. システム構成図 ──
    if system:
        n = len(toc_items) + 1
        toc_items.append({"label": f"{n}. システム構成図", "target": "システム構成図"})
        slides.append({"layout": "section", "title": "システム構成図"})
        slides.append(build_system_slide(system))

    # ── 3. 業務ユースケース一覧 ──
    if usecases:
        n = len(toc_items) + 1
        toc_items.append({"label": f"{n}. 業務ユースケース一覧",
                          "target": "業務ユースケース一覧"})
        slides.append({"layout": "section", "title": "業務ユースケース一覧"})
        uc_rows = []
        for uc in usecases[:15]:
            trigger = next((v for k, v in uc.get("items", [])
                            if "トリガー" in k or "契機" in k), "")
            actors = next((v for k, v in uc.get("items", [])
                           if "登場人物" in k or "アクター" in k), "")
            uc_rows.append([uc["id"], uc["title"], trigger[:40], actors[:30]])
        slides.append({
            "layout": "table", "title": "業務ユースケース一覧",
            "table": {
                "headers": ["ID", "ユースケース", "トリガー", "主な登場人物"],
                "col_widths": [1.0, 3.5, 4.0, 3.5],
                "rows": uc_rows,
            },
        })

    # ── 4. 業務フロー図（複数） ──
    flows = swimlanes.get("flows", [])
    flows = sorted(flows, key=lambda f: (_FLOW_TYPE_ORDER.get(f.get("flow_type", "usecase"), 9),
                                          f.get("usecase_id", ""), f.get("id", "")))
    if flows:
        n = len(toc_items) + 1
        toc_items.append({"label": f"{n}. 業務フロー図", "target": "業務フロー図"})
        slides.append({"layout": "section", "title": "業務フロー図"})
        for flow in flows:
            # 新スキーマ（lanes/steps/transitions）か旧スキーマ（elements）か判定
            if "elements" in flow and "lanes" not in flow:
                elements = flow["elements"]
            else:
                elements = convert_new_swimlane(flow)
            if not elements.get("lanes") or not elements.get("steps"):
                continue
            slides.append({
                "layout":   "swimlane",
                "title":    flow.get("title", "業務フロー"),
                "elements": elements,
            })

    # ── 主要機能一覧（あれば末尾に） ──
    if req.get("fr_rows"):
        n = len(toc_items) + 1
        toc_items.append({"label": f"{n}. 主要機能一覧", "target": "主要機能一覧"})
        slides.append({"layout": "section", "title": "主要機能一覧"})
        slides.append({
            "layout": "table", "title": "主要機能一覧",
            "table": {
                "headers":    ["FR#", "機能要件", "優先度", "ステータス"],
                "col_widths": [1.0, 7.5, 1.5, 1.7],
                "rows":       req["fr_rows"],
            },
        })

    # 目次スライドを先頭に挿入
    slides.insert(0, {"layout": "toc", "title": "目次", "items": toc_items})

    return {
        "title":    "プロジェクト資料",
        "subtitle": "Salesforce プロジェクト概要・システム構成・業務フロー",
        "company":  company,
        "version":  "1.0",
        "date":     today,
        "author":   author,
        "slides":   slides,
    }


# ── エントリポイント ───────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="プロジェクト資料 PPTX 生成")
    ap.add_argument("--docs-dir",   required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--author",     default="")
    args = ap.parse_args()

    docs_dir   = Path(args.docs_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    org       = parse_org_profile(docs_dir / "overview" / "org-profile.md")
    req       = parse_requirements(docs_dir / "requirements" / "requirements.md")
    system    = parse_system_json(docs_dir / "architecture" / "system.json")
    usecases  = parse_usecases(docs_dir / "flow" / "usecases.md")
    swimlanes = parse_swimlanes(docs_dir / "flow" / "swimlanes.json")

    if not org and not req:
        print(
            "ERROR: org-profile.md / requirements.md が見つかりません。"
            "先に /sf-memory を実行してください。", file=sys.stderr,
        )
        sys.exit(1)

    data = build_json(org, req, system, usecases, swimlanes, args.author)
    output_path = output_dir / "プロジェクト資料.pptx"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_json = f.name

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate_pptx.py"),
             "--json-file", tmp_json, "--output", str(output_path)],
            capture_output=True,
        )
        if result.returncode != 0:
            print(result.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
            sys.exit(1)
        print(f"完了: {output_path}")
    finally:
        os.unlink(tmp_json)


if __name__ == "__main__":
    main()
