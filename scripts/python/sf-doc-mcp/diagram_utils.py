#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
汎用ダイアグラム PNG 生成モジュール（matplotlib ベース）

システム構成図・業務フロー図などに使用。
er_utils.py と同じアーキテクチャ: generate_diagram_image() を呼ぶだけで PNG が生成される。

座標系: PowerPoint 座標系（inch 単位、左上=0,0）
"""
from __future__ import annotations
import math
import os
from typing import Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── 日本語フォント ────────────────────────────────────────────────────────────
_JP_REG  = "C:/Windows/Fonts/YuGothR.ttc"
_JP_BOLD = "C:/Windows/Fonts/YuGothB.ttc"


def _fpkw(size: float = 10.0, bold: bool = False) -> dict:
    if not HAS_MPL:
        return {}
    try:
        import matplotlib.font_manager as fm
        path = _JP_BOLD if (bold and os.path.exists(_JP_BOLD)) else _JP_REG
        if os.path.exists(path):
            return {"fontproperties": fm.FontProperties(fname=path, size=size)}
    except Exception:
        pass
    return {"fontsize": size}


# ── カラーパレット ────────────────────────────────────────────────────────────
_STYLES: dict[str, dict] = {
    "primary":   {"bg": "#1E3A5F", "fg": "#FFFFFF", "border": "#1E3A5F"},
    "accent":    {"bg": "#E86C00", "fg": "#FFFFFF", "border": "#E86C00"},
    "secondary": {"bg": "#2C6FAC", "fg": "#FFFFFF", "border": "#2C6FAC"},
    "light":     {"bg": "#F0F4F8", "fg": "#1E3A5F", "border": "#AAAAAA"},
    "success":   {"bg": "#1E7E5A", "fg": "#FFFFFF", "border": "#1E7E5A"},
    "warning":   {"bg": "#B85C00", "fg": "#FFFFFF", "border": "#B85C00"},
    "neutral":   {"bg": "#E8EDF2", "fg": "#2D2D2D", "border": "#8090A0"},
}
_GROUP_ALPHA = 0.12  # グループ背景の透明度

SLIDE_W = 13.333
SLIDE_H = 7.5
TITLE_H = 1.10
DPI     = 220


def _hex(s: str) -> tuple:
    s = s.lstrip("#")
    return tuple(int(s[i:i+2], 16) / 255 for i in (0, 2, 4))


def _style(key: str) -> dict:
    return _STYLES.get(key, _STYLES["light"])


# ── ボックス描画 ──────────────────────────────────────────────────────────────

def _draw_box(ax, box: dict, shadow: bool = True) -> dict:
    """ボックスを描画し、辺の中心座標 dict を返す。"""
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    sc = _style(box.get("style", "primary"))
    pad = 0.045

    # 影（オフセット矩形）
    if shadow:
        shadow_patch = FancyBboxPatch(
            (x + pad + 0.06, y + pad + 0.06), w - 2 * pad, h - 2 * pad,
            boxstyle=f"round,pad={pad}",
            linewidth=0, edgecolor="none",
            facecolor=(0, 0, 0, 0.13),
            zorder=1,
        )
        ax.add_patch(shadow_patch)

    # 本体
    outer = FancyBboxPatch(
        (x + pad, y + pad), w - 2 * pad, h - 2 * pad,
        boxstyle=f"round,pad={pad}",
        linewidth=1.8,
        edgecolor=_hex(sc["border"]),
        facecolor=_hex(sc["bg"]),
        zorder=2,
    )
    ax.add_patch(outer)

    # テキスト（複数行対応）
    lines = box.get("label", "").split("\n")
    n = len(lines)
    line_h = h / (n + 0.5)
    for i, line in enumerate(lines):
        ty = y + h / (n + 1) * (i + 1)
        fs = 11.0 if (i == 0 or n == 1) else 8.5
        bold = (i == 0 or n == 1)
        ax.text(x + w / 2, ty, line,
                ha="center", va="center",
                color=_hex(sc["fg"]),
                clip_on=True, zorder=3,
                **_fpkw(fs, bold=bold))

    cx, cy = x + w / 2, y + h / 2
    return {
        "x": x, "y": y, "w": w, "h": h,
        "top":    (cx, y),
        "bottom": (cx, y + h),
        "left":   (x, cy),
        "right":  (x + w, cy),
    }


def _draw_group(ax, grp: dict):
    """グループ（背景領域）を描画する。"""
    x, y, w, h = grp["x"], grp["y"], grp["w"], grp["h"]
    sc = _style(grp.get("style", "light"))
    bg = _hex(sc["bg"])
    pad = 0.06

    patch = FancyBboxPatch(
        (x + pad, y + pad), w - 2 * pad, h - 2 * pad,
        boxstyle=f"round,pad={pad}",
        linewidth=1.2,
        linestyle=(0, (6, 3)),
        edgecolor=_hex(sc["border"]),
        facecolor=(*bg, _GROUP_ALPHA),
        zorder=0,
    )
    ax.add_patch(patch)

    if grp.get("label"):
        ax.text(x + 0.20, y + 0.22, grp["label"],
                ha="left", va="top",
                color=_hex(sc["border"]),
                clip_on=True, zorder=1,
                **_fpkw(9.0, bold=True))


# ── 接続辺の座標計算 ──────────────────────────────────────────────────────────

def _side_pt(edge: dict, side: str, frac: float = 0.5) -> tuple:
    x, y, w, h = edge["x"], edge["y"], edge["w"], edge["h"]
    if side == "top":    return (x + w * frac, y)
    if side == "bottom": return (x + w * frac, y + h)
    if side == "left":   return (x,             y + h * frac)
    if side == "right":  return (x + w,         y + h * frac)
    return (x + w / 2, y + h / 2)


def _auto_sides(from_e: dict, to_e: dict) -> tuple[str, str]:
    fx = from_e["x"] + from_e["w"] / 2
    fy = from_e["y"] + from_e["h"] / 2
    tx = to_e["x"]   + to_e["w"] / 2
    ty = to_e["y"]   + to_e["h"] / 2
    dx, dy = tx - fx, ty - fy
    if abs(dx) >= abs(dy):
        return ("right" if dx > 0 else "left", "left" if dx > 0 else "right")
    else:
        return ("bottom" if dy > 0 else "top", "top" if dy > 0 else "bottom")


# ── 矢印描画 ──────────────────────────────────────────────────────────────────

_ARROWSTYLE_SINGLE = dict(
    arrowstyle="-|>",
    mutation_scale=16,
)
_ARROWSTYLE_BIDIR = dict(
    arrowstyle="<|-|>",
    mutation_scale=16,
)


def _draw_arrow(ax, edges: dict, arrow: dict):
    src_id = arrow.get("from")
    dst_id = arrow.get("to")
    src = edges.get(src_id)
    dst = edges.get(dst_id)
    if not src or not dst:
        return

    side_from = arrow.get("side_from")
    side_to   = arrow.get("side_to")
    sf_frac   = arrow.get("side_from_frac", 0.5)
    st_frac   = arrow.get("side_to_frac",   0.5)

    if side_from and side_to:
        x1, y1 = _side_pt(src, side_from, sf_frac)
        x2, y2 = _side_pt(dst, side_to,   st_frac)
    else:
        side_from, side_to = _auto_sides(src, dst)
        x1, y1 = _side_pt(src, side_from)
        x2, y2 = _side_pt(dst, side_to)

    style = arrow.get("arrow_style", "")
    color = "#1E3A5F" if style == "primary" else "#6080A0"
    lw    = 2.2 if style == "primary" else 1.5

    arrstyle = _ARROWSTYLE_BIDIR if arrow.get("bidirectional") else _ARROWSTYLE_SINGLE
    patch = FancyArrowPatch(
        (x1, y1), (x2, y2),
        **arrstyle,
        linewidth=lw,
        color=_hex(color),
        zorder=4,
        shrinkA=4, shrinkB=4,
    )
    ax.add_patch(patch)

    # ラベル
    label = arrow.get("label", "")
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) > abs(y2 - y1):
            my -= 0.22
        else:
            mx += 0.22
        ax.text(mx, my, label,
                ha="center", va="center",
                color=_hex("#2D2D2D"),
                bbox=dict(boxstyle="round,pad=0.08", facecolor="white",
                          edgecolor=_hex("#CCCCCC"), linewidth=0.8),
                zorder=5, **_fpkw(7.5))


# ── メイン生成関数 ─────────────────────────────────────────────────────────────

def generate_diagram_image(boxes: list, arrows: list, out_path: str,
                            title: str = "",
                            groups: Optional[list] = None,
                            slide_w: float = SLIDE_W,
                            slide_h: float = SLIDE_H) -> bool:
    """ダイアグラムを PNG で出力する。

    Returns:
        True=成功 / False=matplotlib 未インストール
    """
    if not HAS_MPL:
        return False

    fig, ax = plt.subplots(figsize=(slide_w, slide_h), dpi=DPI)
    ax.set_xlim(0, slide_w)
    ax.set_ylim(slide_h, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # タイトルバー
    ax.add_patch(mpatches.Rectangle(
        (0, 0), slide_w, TITLE_H,
        linewidth=0, facecolor=_hex("#1E3A5F"), zorder=10,
    ))
    if title:
        ax.text(0.55, TITLE_H / 2, title,
                ha="left", va="center", color="white",
                zorder=11, **_fpkw(16.0, bold=True))

    # グループ（背景）→ ボックス → 矢印 の順
    for grp in (groups or []):
        _draw_group(ax, grp)

    edges: dict[str, dict] = {}
    for box in boxes:
        edge = _draw_box(ax, box)
        edges[box["id"]] = edge

    for arrow in arrows:
        _draw_arrow(ax, edges, arrow)

    fig.savefig(out_path, dpi=DPI, bbox_inches=None,
                facecolor="white", pad_inches=0)
    plt.close(fig)
    return True


# ====================================================================
# ドメイン設計書向け図形生成（業務フロー・画面遷移・コンポーネント依存）
# ====================================================================

try:
    import networkx as _nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False

from collections import OrderedDict as _OrderedDict

# ── 色定数 ──────────────────────────────────────────────────────
_COMP_COLORS = {
    "Apex":    "#4472C4",
    "LWC":     "#70AD47",
    "Flow":    "#ED7D31",
    "Aura":    "#7030A0",
    "Trigger": "#4472C4",
}
_COMP_DEFAULT_COLOR = "#808080"
_LANE_COLORS = ["#EBF5FB", "#FFFFFF"]


def _dom_wrap(text: str, limit: int = 14) -> str:
    """limit 文字を目安に折り返す。"""
    if not text:
        return ""
    out: list[str] = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            line += ch
            if len(line) >= limit:
                out.append(line)
                line = ""
        if line:
            out.append(line)
    return "\n".join(out)


# ================================================================
# 1. 業務フロー図（スイムレーン横レーン形式）
# ================================================================
def generate_business_flow_diagram(
    flows: list[dict],
    out_path: str,
    fig_w: float = 12,
) -> bool:
    """スイムレーン図を生成する。

    flows: [{"step": "1", "actor": "営業担当者", "action": "見積依頼を入力",
             "system": "QuotationRequestPage"}]
    戻り値: True(成功) / False(失敗)
    """
    if not HAS_MPL or not flows:
        return False

    # アクターごとにステップをグループ化（出現順を維持）
    actor_steps: _OrderedDict[str, list[dict]] = _OrderedDict()
    for f in flows:
        actor = f.get("actor", "不明")
        actor_steps.setdefault(actor, []).append(f)

    actors = list(actor_steps.keys())

    # レイアウト定数
    lane_h = 1.2
    label_w = 2.5
    box_w = 2.8
    box_h = 0.7

    # レーンごとの高さを計算
    lane_heights: list[float] = []
    for actor in actors:
        steps = actor_steps[actor]
        h = max(1.5, len(steps) * lane_h + 0.3)
        lane_heights.append(h)

    total_h = sum(lane_heights) + 0.6
    fig, ax = plt.subplots(figsize=(fig_w, total_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, total_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    y_top = total_h - 0.3
    step_positions: list[tuple[float, float]] = []

    for lane_idx, actor in enumerate(actors):
        lh = lane_heights[lane_idx]
        y_bot = y_top - lh

        # レーン背景
        bg_color = _LANE_COLORS[lane_idx % 2]
        ax.add_patch(FancyBboxPatch(
            (0, y_bot), fig_w, lh,
            boxstyle="square,pad=0",
            facecolor=bg_color, edgecolor="#CCCCCC", linewidth=0.5,
        ))
        ax.plot([0, fig_w], [y_bot, y_bot], color="#BBBBBB", linewidth=0.8)

        # アクターラベル
        ax.text(
            label_w / 2, (y_top + y_bot) / 2, _dom_wrap(actor, 8),
            ha="center", va="center", fontsize=9,
            color=_hex("#1F3864"),
            **_fpkw(9.0, bold=True),
        )
        ax.plot([label_w, label_w], [y_bot, y_top], color="#BBBBBB", linewidth=0.8)

        # ステップ描画
        steps = actor_steps[actor]
        content_w = fig_w - label_w - 0.5
        cx = label_w + content_w / 2
        n_steps = len(steps)
        step_area_h = lh - 0.3
        actual_lane_h = step_area_h / max(n_steps, 1)

        for si, step in enumerate(steps):
            cy = y_top - 0.15 - actual_lane_h * si - actual_lane_h / 2

            ax.add_patch(FancyBboxPatch(
                (cx - box_w / 2, cy - box_h / 2), box_w, box_h,
                boxstyle="round,pad=0.05,rounding_size=0.1",
                facecolor="#DEEAF1", edgecolor="#6A8CAF", linewidth=1.0,
            ))

            step_no = step.get("step", "")
            action = step.get("action", "")
            label_text = f"{step_no}. {action}" if step_no else action
            ax.text(cx, cy + 0.02, _dom_wrap(label_text, 18),
                    ha="center", va="center", fontsize=7.5,
                    color="black", **_fpkw(7.5))

            system = step.get("system", "")
            if system:
                ax.text(cx, cy - box_h / 2 - 0.08, system,
                        ha="center", va="top", fontsize=6, color="#808080",
                        **_fpkw(6.0))

            step_positions.append((cx, cy))

        y_top = y_bot

    # ステップ間の矢印
    for i in range(len(step_positions) - 1):
        x0, y0 = step_positions[i]
        x1, y1 = step_positions[i + 1]
        ax.annotate(
            "", xy=(x1, y1 + box_h / 2 + 0.02),
            xytext=(x0, y0 - box_h / 2 - 0.02),
            arrowprops=dict(arrowstyle="->", color="#444444", lw=1.2,
                            shrinkA=0, shrinkB=0),
        )

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


# ================================================================
# 2. 画面遷移図（純matplotlib実装・networkx不要）
# ================================================================
def generate_screen_transition_diagram(
    screens: list[dict],
    out_path: str,
    fig_w: float = 12,
) -> bool:
    """画面遷移図を生成する（円形レイアウト）。

    screens: [{"name": "見積一覧", "component": "QuotationList",
               "transitions_to": ["見積入力画面"]}]
    戻り値: True(成功) / False(失敗)
    """
    if not HAS_MPL or not screens:
        return False

    import math as _math

    # 全ノードを収集（順序維持）
    screen_map: dict[str, dict] = {}
    all_nodes: list[str] = []
    edges: list[tuple[str, str]] = []

    for s in screens:
        name = s.get("name", "")
        if not name:
            continue
        screen_map[name] = s
        if name not in all_nodes:
            all_nodes.append(name)

    for s in screens:
        name = s.get("name", "")
        for target in s.get("transitions_to", []):
            if target:
                if target not in all_nodes:
                    all_nodes.append(target)
                if name:
                    edges.append((name, target))

    if not all_nodes:
        return False

    # 円形レイアウト
    n = len(all_nodes)
    fig_h = max(6, fig_w * 0.75)
    cx_fig, cy_fig = fig_w / 2, fig_h / 2
    radius = min(fig_w, fig_h) * 0.38

    node_pos: dict[str, tuple[float, float]] = {}
    for i, name in enumerate(all_nodes):
        angle = _math.pi / 2 + 2 * _math.pi * i / max(n, 1)
        node_pos[name] = (
            cx_fig + radius * _math.cos(angle),
            cy_fig + radius * _math.sin(angle),
        )

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    fig.patch.set_facecolor("white")

    box_w_sc, box_h_sc = 2.2, 0.72

    # エッジ描画
    for u, v in edges:
        x0, y0 = node_pos[u]
        x1, y1 = node_pos[v]
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-|>", color="#666666", lw=1.2,
                connectionstyle="arc3,rad=0.15",
                shrinkA=max(box_w_sc, box_h_sc) * 16,
                shrinkB=max(box_w_sc, box_h_sc) * 16,
            ),
        )

    # ノード描画
    for name, (cx, cy) in node_pos.items():
        ax.add_patch(FancyBboxPatch(
            (cx - box_w_sc / 2, cy - box_h_sc / 2), box_w_sc, box_h_sc,
            boxstyle="round,pad=0.05,rounding_size=0.1",
            facecolor="#DEEAF1", edgecolor="#4472C4", linewidth=1.2,
        ))
        ax.text(cx, cy + 0.1, _dom_wrap(name, 12),
                ha="center", va="center", fontsize=8,
                color=_hex("#1F3864"), **_fpkw(8.0, bold=True))
        comp = screen_map.get(name, {}).get("component", "")
        if comp:
            ax.text(cx, cy - 0.2, comp,
                    ha="center", va="center", fontsize=6.5, color="#808080",
                    **_fpkw(6.5))

    plt.tight_layout(pad=0.3)
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


# ================================================================
# 3. コンポーネント依存関係図（純matplotlib実装・networkx不要）
# ================================================================
def generate_component_diagram(
    components: list[dict],
    out_path: str,
    fig_w: float = 12,
) -> bool:
    """コンポーネント依存関係図を生成する（グリッドレイアウト）。

    components: [{"api_name": "QuotationCtrl", "type": "Apex",
                  "role": "...", "calls": ["QuotationService"]}]
    戻り値: True(成功) / False(失敗)
    """
    if not HAS_MPL or not components:
        return False

    import math as _math

    # ノード収集
    comp_type_map: dict[str, str] = {}
    all_nodes: list[str] = []
    edges: list[tuple[str, str]] = []

    for c in components:
        api = c.get("api_name", "")
        if not api:
            continue
        ctype = c.get("type", "")
        comp_type_map[api] = ctype
        if api not in all_nodes:
            all_nodes.append(api)
        for target in c.get("calls", []):
            if target:
                if target not in all_nodes:
                    all_nodes.append(target)
                edges.append((api, target))
                if target not in comp_type_map:
                    comp_type_map[target] = ""

    if not all_nodes:
        return False

    # グリッドレイアウト（呼び出し元を上、呼び出し先を下に配置）
    caller_set = {u for u, _ in edges}
    callee_set = {v for _, v in edges}
    top_nodes = [n for n in all_nodes if n in caller_set]
    bot_nodes = [n for n in all_nodes if n not in caller_set]

    fig_h = max(6, fig_w * 0.7)
    margin = 1.2
    box_w_cp, box_h_cp = 2.0, 0.6

    def _row_positions(nodes: list[str], y: float) -> dict[str, tuple[float, float]]:
        n = len(nodes)
        if n == 0:
            return {}
        span = fig_w - 2 * margin
        gap = span / max(n, 1)
        result = {}
        for i, name in enumerate(nodes):
            cx = margin + gap * i + gap / 2
            result[name] = (cx, y)
        return result

    node_pos: dict[str, tuple[float, float]] = {}
    node_pos.update(_row_positions(top_nodes, fig_h * 0.65))
    node_pos.update(_row_positions(bot_nodes, fig_h * 0.28))

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    fig.patch.set_facecolor("white")

    # エッジ描画
    for u, v in edges:
        x0, y0 = node_pos[u]
        x1, y1 = node_pos[v]
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-|>", color="#666666", lw=1.1,
                connectionstyle="arc3,rad=0.12",
                shrinkA=max(box_w_cp, box_h_cp) * 15,
                shrinkB=max(box_w_cp, box_h_cp) * 15,
            ),
        )

    # ノード描画
    for name, (cx, cy) in node_pos.items():
        ctype = comp_type_map.get(name, "")
        color = _COMP_COLORS.get(ctype, _COMP_DEFAULT_COLOR)
        ax.add_patch(FancyBboxPatch(
            (cx - box_w_cp / 2, cy - box_h_cp / 2), box_w_cp, box_h_cp,
            boxstyle="round,pad=0.05,rounding_size=0.08",
            facecolor=color, edgecolor="#333333", linewidth=1.0,
            alpha=0.85,
        ))
        ax.text(cx, cy, _dom_wrap(name, 16),
                ha="center", va="center", fontsize=7,
                color="white", **_fpkw(7.0, bold=True))

    # 凡例（右下）
    legend_items = [
        ("Apex", _COMP_COLORS["Apex"]),
        ("LWC", _COMP_COLORS["LWC"]),
        ("Flow", _COMP_COLORS["Flow"]),
        ("Aura", _COMP_COLORS["Aura"]),
        ("Other", _COMP_DEFAULT_COLOR),
    ]
    legend_x = fig_w - 1.8
    legend_y = 0.5
    for i, (label, color) in enumerate(legend_items):
        ly = legend_y + i * 0.35
        ax.add_patch(FancyBboxPatch(
            (legend_x, ly - 0.1), 0.4, 0.22,
            boxstyle="round,pad=0.02",
            facecolor=color, edgecolor="#333333", linewidth=0.6,
            alpha=0.85,
        ))
        ax.text(legend_x + 0.55, ly, label,
                ha="left", va="center", fontsize=7, color="#333333",
                **_fpkw(7.0))

    plt.tight_layout(pad=0.3)
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True
