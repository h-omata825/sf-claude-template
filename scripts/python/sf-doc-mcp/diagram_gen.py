"""
高品質図生成モジュール（graphviz + drawsvg ベース）。

diagram_utils.py / er_utils.py の matplotlib 実装を置き換える新実装。

提供関数:
  render_system_diagram(system: dict, out_path: str) -> (width_px, height_px)
  render_er_diagram(relations: list, objects: list, out_path: str) -> (width_px, height_px)
  render_swimlane(flow: dict, out_path: str) -> (width_px, height_px)

依存:
  graphviz (pip + バイナリ)  ── システム構成図・ER図
  drawsvg                    ── スイムレーン図
  svglib + reportlab         ── SVG→PNG変換
  Pillow                     ── PNG サイズ確認
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

# ── 依存チェック ──────────────────────────────────────────────────
try:
    import graphviz as _gv
    _HAS_GV = True
except ImportError:
    _HAS_GV = False

try:
    import drawsvg as dw
    _HAS_DW = True
except ImportError:
    _HAS_DW = False

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

try:
    from PIL import Image as _PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Graphviz バイナリ PATH（winget インストール先）
_GV_BIN = r"C:\Program Files\Graphviz\bin"
if os.path.isdir(_GV_BIN) and _GV_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GV_BIN + os.pathsep + os.environ.get("PATH", "")

# ── カラーパレット ────────────────────────────────────────────────
C_SF_CORE   = "#1F3864"   # Salesforce中核（濃紺）
C_SF_LABEL  = "#FFFFFF"
C_ACTOR_BG  = "#D9E1F2"   # 利用者（薄青）
C_ACTOR_FG  = "#1F3864"
C_EXT_BG    = "#E2EFDA"   # 外部システム（薄緑）
C_EXT_FG    = "#375623"
C_DS_BG     = "#FFF2CC"   # データストア（薄黄）
C_DS_FG     = "#7F6000"
C_EDGE      = "#5A5A5A"
C_LANE_HDR  = "#1F3864"
C_LANE_ALT  = ["#F8FAFD", "#EEF4FB", "#F5FBF0", "#FFFBF0", "#FBF5FF"]
C_STEP_BG   = "#2E75B6"
C_STEP_FG   = "#FFFFFF"
C_STEP_BORDER = "#1F3864"
C_ARROW     = "#444444"

FONT_JP = "MS Gothic"   # graphviz 用（Windows）
DPI     = 150


# ── SVG → PNG 変換ヘルパー ────────────────────────────────────────

def _svg_bytes_to_png(svg_bytes: bytes, out_path: str) -> tuple[int, int]:
    """SVG バイト列を PNG ファイルに変換し (width, height) を返す"""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="wb") as f:
        f.write(svg_bytes)
        tmp_svg = f.name
    try:
        drawing = svg2rlg(tmp_svg)
        if drawing is None:
            raise RuntimeError("svg2rlg returned None")
        renderPM.drawToFile(drawing, out_path, fmt="PNG", dpi=DPI)
    finally:
        os.unlink(tmp_svg)

    if _HAS_PIL:
        img = _PILImage.open(out_path)
        return img.size
    return (0, 0)


def _svg_str_to_png(svg_str: str, out_path: str) -> tuple[int, int]:
    """SVG 文字列を PNG ファイルに変換し (width, height) を返す"""
    full = '<?xml version="1.0" encoding="utf-8"?>\n' + svg_str
    return _svg_bytes_to_png(full.encode("utf-8"), out_path)


# ════════════════════════════════════════════════════════════════
# 1. システム構成図（graphviz）
# ════════════════════════════════════════════════════════════════

def render_system_diagram(system: dict, out_path: str) -> tuple[int, int]:
    """
    system.json の内容からシステム構成図 PNG を生成する。

    system スキーマ:
      core: {name, role}
      actors: [{name, count?, channels?}]
      external_systems: [{name, direction, protocol, frequency, purpose}]
      data_stores: [{name, purpose}]
    """
    if not _HAS_GV or not _HAS_SVG:
        raise RuntimeError("graphviz または svglib が利用できません")

    g = _gv.Digraph(
        "system",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "LR",
            "splines": "polyline",
            "nodesep": "0.5",
            "ranksep": "1.2",
            "fontname": FONT_JP,
            "pad": "0.4",
        },
    )

    core = system.get("core") or {}
    core_label = _gv_label(core.get("name", "Salesforce"), core.get("role", ""))

    # 中核 Salesforce ノード
    g.node(
        "core",
        label=core_label,
        shape="box",
        style="filled,rounded",
        fillcolor=C_SF_CORE,
        fontcolor=C_SF_LABEL,
        fontname=FONT_JP,
        fontsize="12",
        width="2.2",
        height="0.9",
        penwidth="2",
    )

    # 利用者（左）
    with g.subgraph(name="cluster_actors") as sg:
        sg.attr(rank="min", style="invis")
        for i, actor in enumerate(system.get("actors", [])[:6]):
            nid = f"actor_{i}"
            cnt = f"\n({actor['count']}名)" if actor.get("count") else ""
            sg.node(
                nid,
                label=_gv_label(actor["name"] + cnt),
                shape="ellipse",
                style="filled",
                fillcolor=C_ACTOR_BG,
                fontcolor=C_ACTOR_FG,
                fontname=FONT_JP,
                fontsize="10",
                width="1.8",
            )
            g.edge(nid, "core", color=C_EDGE, arrowsize="0.8")

    # 外部システム（右）
    with g.subgraph(name="cluster_ext") as sg:
        sg.attr(rank="max", style="invis")
        for i, ext in enumerate(system.get("external_systems", [])[:8]):
            nid = f"ext_{i}"
            proto = ext.get("protocol", "")
            freq = ext.get("frequency", "")
            edge_lbl = f"{proto}" + (f"\n{freq}" if freq else "")
            sg.node(
                nid,
                label=_gv_label(ext["name"]),
                shape="box",
                style="filled,rounded",
                fillcolor=C_EXT_BG,
                fontcolor=C_EXT_FG,
                fontname=FONT_JP,
                fontsize="10",
                width="1.8",
            )
            direction = ext.get("direction", "out")
            if direction == "in":
                g.edge(nid, "core", xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)
            elif direction == "both":
                g.edge("core", nid, xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       dir="both", fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)
            else:
                g.edge("core", nid, xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)

    # データストア（下）
    for i, ds in enumerate(system.get("data_stores", [])[:4]):
        nid = f"ds_{i}"
        g.node(
            nid,
            label=_gv_label(ds["name"]),
            shape="cylinder",
            style="filled",
            fillcolor=C_DS_BG,
            fontcolor=C_DS_FG,
            fontname=FONT_JP,
            fontsize="10",
        )
        g.edge("core", nid, color=C_EDGE, arrowsize="0.8", style="dashed")

    svg_bytes = g.pipe(format="svg")
    return _svg_bytes_to_png(svg_bytes, out_path)


def _gv_label(*lines: str) -> str:
    return "\n".join(l for l in lines if l)


# ════════════════════════════════════════════════════════════════
# 2. ER図（graphviz record ノード）
# ════════════════════════════════════════════════════════════════

def render_er_diagram(
    objects: list[dict],
    relations: list[dict],
    out_path: str,
) -> tuple[int, int]:
    """
    オブジェクト一覧と関連定義からER図PNGを生成する。

    objects: [{api, label, type}]
    relations: [{parent, child, rel, field}]
      rel: "1-N" | "N-N" | "lookup" | "master-detail"
    """
    if not _HAS_GV or not _HAS_SVG:
        raise RuntimeError("graphviz または svglib が利用できません")

    g = _gv.Digraph(
        "er",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "TB",
            "splines": "polyline",
            "nodesep": "0.6",
            "ranksep": "0.8",
            "fontname": FONT_JP,
            "pad": "0.3",
        },
    )

    # オブジェクトノード（HTML ラベルで2段）
    obj_ids = set()
    for obj in objects:
        nid = obj["api"].replace("__c", "_c").replace("__", "_")
        obj_ids.add(obj["api"])
        kind = obj.get("type", "")
        kind_color = "#1F3864" if kind in ("カスタム", "Custom") else "#2E75B6"
        label = (
            f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            f'<TR><TD BGCOLOR="{kind_color}"><FONT COLOR="white"><B>{obj["api"]}</B></FONT></TD></TR>'
            f'<TR><TD BGCOLOR="#D9E1F2"><FONT COLOR="#1F3864">{obj.get("label", "")}</FONT></TD></TR>'
            f"</TABLE>>"
        )
        g.node(
            nid,
            label=label,
            shape="none",
            fontname=FONT_JP,
            fontsize="10",
        )

    # 関連エッジ
    for rel in relations:
        parent = rel["parent"]
        child = rel["child"]
        pid = parent.replace("__c", "_c").replace("__", "_")
        cid = child.replace("__c", "_c").replace("__", "_")
        rel_type = rel.get("rel", "").lower()
        if "master" in rel_type or "md" in rel_type:
            arrow = "diamond"
            style = "bold"
        elif "n-n" in rel_type or "many" in rel_type:
            arrow = "crow"
            style = "dashed"
        else:
            arrow = "vee"
            style = "solid"
        field_label = rel.get("field", "")
        g.edge(
            pid, cid,
            label=field_label,
            arrowhead=arrow,
            style=style,
            color=C_EDGE,
            fontname=FONT_JP,
            fontsize="8",
            fontcolor=C_EDGE,
        )

    svg_bytes = g.pipe(format="svg")
    return _svg_bytes_to_png(svg_bytes, out_path)


# ════════════════════════════════════════════════════════════════
# 3. スイムレーン図（drawsvg）
# ════════════════════════════════════════════════════════════════

_STEP_W   = 140   # ステップ箱の幅
_STEP_H   = 54    # ステップ箱の高さ
_COL_GAP  = 30    # 列間
_LANE_PAD = 14    # レーン内上下余白
_HDR_W    = 90    # レーンヘッダー幅
_MARGIN   = 20    # 全体余白


def render_swimlane(flow: dict, out_path: str) -> tuple[int, int]:
    """
    swimlanes.json の1フローからスイムレーン図PNGを生成する。

    flow スキーマ:
      title: str
      lanes: [{name, type}]
      steps: [{id, lane, col, label}]
      transitions: [{from, to, condition?}]
    """
    if not _HAS_DW or not _HAS_SVG:
        raise RuntimeError("drawsvg または svglib が利用できません")

    lanes_in  = flow.get("lanes", [])
    steps_in  = flow.get("steps", [])
    trans_in  = flow.get("transitions", [])
    title     = flow.get("title", "業務フロー")

    if not lanes_in or not steps_in:
        return _draw_empty_swimlane(title, out_path)

    # col 番号を計算（なければ step 順に付与）
    max_col = max((s.get("col", i + 1) for i, s in enumerate(steps_in)), default=1)
    n_lanes = len(lanes_in)

    lane_h  = _STEP_H + _LANE_PAD * 2
    total_h = _MARGIN + 30 + n_lanes * lane_h + _MARGIN  # title行 + lanes
    total_w = _MARGIN + _HDR_W + max_col * (_STEP_W + _COL_GAP) + _MARGIN

    d = dw.Drawing(total_w, total_h, origin=(0, 0))
    d.append(dw.Rectangle(0, 0, total_w, total_h, fill="white"))

    title_y = _MARGIN
    # タイトル帯
    d.append(dw.Rectangle(_MARGIN, title_y, total_w - _MARGIN * 2, 26,
                           fill=C_LANE_HDR, rx=4))
    d.append(dw.Text(title, 12, total_w / 2, title_y + 13,
                     center=True, dominant_baseline="middle",
                     fill="white"))

    content_y0 = title_y + 30

    # レーンヘッダー背景
    lane_name_map: dict[str, int] = {}
    for i, lane in enumerate(lanes_in):
        name = lane.get("name", f"Lane{i+1}")
        lane_name_map[name] = i
        ly = content_y0 + i * lane_h
        bg = C_LANE_ALT[i % len(C_LANE_ALT)]
        # レーン背景
        d.append(dw.Rectangle(0, ly, total_w, lane_h,
                               fill=bg, stroke="#CCCCCC", stroke_width=0.8))
        # ヘッダー区切り
        d.append(dw.Rectangle(0, ly, _HDR_W, lane_h,
                               fill=C_LANE_HDR + "22", stroke="#CCCCCC", stroke_width=0.8))
        d.append(dw.Text(name, 10, _HDR_W / 2, ly + lane_h / 2,
                         center=True, dominant_baseline="middle",
                         fill=C_LANE_HDR))

    # ステップ箱の座標マップ
    step_center: dict = {}
    for step in steps_in:
        sid   = str(step.get("id", ""))
        sname = str(step.get("lane", ""))
        col   = int(step.get("col", 1))
        lane_i = lane_name_map.get(sname, 0)
        cx = _MARGIN + _HDR_W + (col - 1) * (_STEP_W + _COL_GAP) + _STEP_W / 2
        cy = content_y0 + lane_i * lane_h + lane_h / 2
        step_center[sid] = (cx, cy)

        # 箱描画
        bx, by = cx - _STEP_W / 2, cy - _STEP_H / 2
        d.append(dw.Rectangle(bx, by, _STEP_W, _STEP_H,
                               fill=C_STEP_BG, stroke=C_STEP_BORDER,
                               stroke_width=1.5, rx=6))
        # ラベル（2行まで折り返し）
        label = str(step.get("label", sid))
        lines = _wrap_label(label, max_chars=16)
        line_h = 13
        y_start = cy - (len(lines) - 1) * line_h / 2
        for j, line in enumerate(lines[:3]):
            d.append(dw.Text(line, 10, cx, y_start + j * line_h,
                             center=True, dominant_baseline="middle",
                             fill=C_STEP_FG))

    # 矢印
    for t in trans_in:
        src = str(t.get("from", ""))
        dst = str(t.get("to", ""))
        if src not in step_center or dst not in step_center:
            continue
        x1, y1 = step_center[src]
        x2, y2 = step_center[dst]
        cond = t.get("condition", "")
        _draw_arrow(d, x1, y1, x2, y2, cond)

    svg_str = d.as_svg()
    return _svg_str_to_png(svg_str, out_path)


def _wrap_label(text: str, max_chars: int = 16) -> list[str]:
    """長いラベルを改行で分割"""
    if "\n" in text:
        return text.split("\n")[:3]
    if len(text) <= max_chars:
        return [text]
    lines = []
    while text:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    return lines[:3]


def _draw_arrow(d: "dw.Drawing", x1: float, y1: float,
                x2: float, y2: float, label: str = ""):
    """ステップ間の矢印を描画"""
    # 出発点・到着点をボックス端に合わせる
    if abs(x2 - x1) > abs(y2 - y1):
        sx = x1 + (_STEP_W / 2 if x2 > x1 else -_STEP_W / 2)
        sy = y1
        ex = x2 - (_STEP_W / 2 if x2 > x1 else -_STEP_W / 2)
        ey = y2
    else:
        sx = x1
        sy = y1 + (_STEP_H / 2 if y2 > y1 else -_STEP_H / 2)
        ex = x2
        ey = y2 - (_STEP_H / 2 if y2 > y1 else -_STEP_H / 2)

    arrow_marker = dw.Marker(0, 0, 9, 6, orient="auto")
    arrow_marker.append(dw.Path(d="M0,0 L0,6 L9,3 z", fill=C_ARROW))
    d.append(dw.Line(sx, sy, ex, ey, stroke=C_ARROW, stroke_width=1.5,
                     marker_end=arrow_marker))
    if label:
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        d.append(dw.Text(label, 8, mx + 4, my - 4, fill=C_ARROW))


def _draw_empty_swimlane(title: str, out_path: str) -> tuple[int, int]:
    W, H = 600, 200
    d = dw.Drawing(W, H)
    d.append(dw.Rectangle(0, 0, W, H, fill="white"))
    d.append(dw.Rectangle(10, 10, W - 20, 30, fill=C_LANE_HDR, rx=4))
    d.append(dw.Text(title, 12, W / 2, 25, center=True,
                     dominant_baseline="middle", fill="white"))
    d.append(dw.Text("(データなし)", 11, W / 2, 110, center=True,
                     dominant_baseline="middle", fill="#999999"))
    return _svg_str_to_png(d.as_svg(), out_path)


# ════════════════════════════════════════════════════════════════
# Excel 埋め込みヘルパー
# ════════════════════════════════════════════════════════════════

def embed_image_in_sheet(ws, img_path: str, anchor_row: int, anchor_col: int = 2,
                         max_width_px: int = 1200, dpi: int = DPI) -> int:
    """
    PNG をワークシートに埋め込み、画像の高さに合わせた行数を返す。

    anchor_row: 画像を配置する開始行
    anchor_col: 画像を配置する開始列（デフォルト=2）
    戻り値: 画像が占める行数（行高 20pt 換算）
    """
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter

    if not _HAS_PIL:
        raise RuntimeError("Pillow が必要です")

    img = _PILImage.open(img_path)
    w_px, h_px = img.size

    # 最大幅に合わせてスケール
    scale = min(1.0, max_width_px / w_px)
    display_w = int(w_px * scale)
    display_h = int(h_px * scale)

    xl_img = XLImage(img_path)
    # EMU: 1pt = 12700 EMU, 1px@96dpi ≈ 9525 EMU
    emu_per_px = 914400 / dpi
    xl_img.width  = int(display_w * emu_per_px / 9525)
    xl_img.height = int(display_h * emu_per_px / 9525)
    xl_img.anchor = f"{get_column_letter(anchor_col)}{anchor_row}"

    ws.add_image(xl_img)

    # 行高を調整（画像高さに合わせて必要行数を確保）
    pt_per_row = 20
    pt_total   = display_h * 0.75  # px → pt 概算
    n_rows     = max(1, int(pt_total / pt_per_row) + 1)
    for r in range(anchor_row, anchor_row + n_rows):
        ws.row_dimensions[r].height = pt_per_row

    return n_rows
