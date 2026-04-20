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


# ── LWC ワイヤーフレーム生成 ─────────────────────────────────────────────────
import re

_SLDS_BRAND  = "#0070D2"
_SLDS_GRAY   = "#F3F2F2"
_SLDS_BORDER = "#DDDBDA"

# タグ名 → (type, 抽出する属性リスト)
# c-lightning-* は lightning-* のカスタムラッパーとして同一マッピング
_LWC_TAG_MAP: dict[str, tuple[str, list[str]]] = {
    "lightning-input":           ("input",    ["label", "type", "required"]),
    "c-lightning-input-text":    ("input",    ["label", "required"]),
    "lightning-combobox":        ("picklist", ["label", "required"]),
    "c-lightning-combobox":      ("picklist", ["label", "required"]),
    "lightning-textarea":        ("textarea", ["label", "required"]),
    "c-lightning-textarea":      ("textarea", ["label", "required"]),
    "lightning-datatable":       ("table",    ["title", "label", "required"]),
    "c-lightning-datatable":     ("table",    ["title", "label", "required"]),
    "lightning-button":          ("button",   ["label", "variant"]),
    "c-lightning-button":        ("button",   ["label", "variant"]),
    "lightning-record-form":     ("record_form", ["object-api-name", "label", "required"]),
    "lightning-record-picker":   ("input",    ["label", "required"]),
    "c-lightning-record-picker": ("input",    ["label", "required"]),
    "lightning-dual-listbox":    ("picklist", ["label", "required"]),
    "c-lightning-dual-listbox":  ("picklist", ["label", "required"]),
}


def extract_lwc_ui_elements(html_content: str) -> list[dict]:
    """LWC HTML から UI エレメント情報を抽出する。"""
    elements: list[dict] = []
    if not html_content:
        return elements

    for tag_name, (elem_type, _attrs) in _LWC_TAG_MAP.items():
        # 自己終了タグ・通常タグ両方にマッチ
        pattern = rf"<{re.escape(tag_name)}\b([^>]*?)(/?>)"
        for m in re.finditer(pattern, html_content, re.DOTALL):
            attr_str = m.group(1)

            # --- 属性値の抽出ヘルパー ---
            def _attr(name: str, _attr_str: str = attr_str) -> str | None:
                am = re.search(
                    rf"""{re.escape(name)}\s*=\s*(?:"([^"]*)"|'([^']*)')""",
                    _attr_str, re.DOTALL,
                )
                if am:
                    return am.group(1) if am.group(1) is not None else am.group(2)
                return None

            # lightning-button: variant フィルタ
            if elem_type == "button":
                label = _attr("label")
                if not label:
                    continue
                variant = _attr("variant") or "neutral"
                if variant not in ("brand", "destructive", "neutral"):
                    continue
                elements.append({
                    "type": "button",
                    "label": label,
                    "required": False,
                    "subtype": variant,
                })
                continue

            # 共通処理
            label = _attr("label")
            required = "required" in attr_str and _attr("required") != "false"

            if elem_type == "table":
                label = _attr("title") or _attr("label") or "データテーブル"
            elif elem_type == "record_form":
                label = _attr("object-api-name") or label or "RecordForm"

            if label is None:
                label = ""

            subtype = ""
            if elem_type == "input":
                subtype = _attr("type") or "text"

            elements.append({
                "type": elem_type,
                "label": label,
                "required": required,
                "subtype": subtype,
            })

    return elements


def generate_screen_wireframe(
    title: str,
    elements: list[dict],
    out_path: str,
    fig_w: float = 9,
) -> bool:
    """SLDS 風簡易ワイヤーフレームを PNG で出力する。"""
    if not HAS_MPL:
        return False

    # ── ボタンとフィールドを分離 ───────────────────────────────────────────
    buttons = [e for e in elements if e["type"] == "button"]
    fields  = [e for e in elements if e["type"] != "button"]

    # ── フィールド高さ計算 ─────────────────────────────────────────────────
    _FIELD_H = {
        "input": 0.38, "picklist": 0.38, "textarea": 0.7,
        "table": 1.2, "record_form": 0.38,
    }
    _LABEL_H   = 0.28   # ラベル行の高さ
    _GAP       = 0.12   # フィールド間の余白
    _CARD_PAD  = 0.30   # カード内の上下左右余白
    _HEADER_H  = 0.60

    # 2カラム判定
    use_two_col = len(fields) > 8
    if use_two_col:
        mid = (len(fields) + 1) // 2
        col_left  = fields[:mid]
        col_right = fields[mid:]
    else:
        col_left  = fields
        col_right = []

    def _col_height(col: list[dict]) -> float:
        h = 0.0
        for f in col:
            h += _LABEL_H + _FIELD_H.get(f["type"], 0.38) + _GAP
        return h

    body_h = max(_col_height(col_left), _col_height(col_right)) if col_right else _col_height(col_left)
    fig_h  = _HEADER_H + body_h + _CARD_PAD * 2 + 0.3  # 0.3 = 外枠余白

    # ── Figure / Axes ──────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(fig_w, max(fig_h, 2.0)))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)  # Y軸反転（上→下）
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor(_SLDS_GRAY)

    # ── ヘッダーバー ───────────────────────────────────────────────────────
    ax.add_patch(FancyBboxPatch(
        (0.2, 0.15), fig_w - 0.4, _HEADER_H,
        boxstyle="round,pad=0.05",
        facecolor=_SLDS_BRAND, edgecolor="none",
    ))
    ax.text(0.55, 0.15 + _HEADER_H / 2, title,
            ha="left", va="center", color="white",
            **_fpkw(11.0, bold=True))

    # ヘッダー内ボタン（右寄せ）
    btn_x = fig_w - 0.5
    for btn in reversed(buttons):
        lbl = btn["label"]
        bw = max(len(lbl) * 0.18 + 0.3, 0.8)
        bx = btn_x - bw
        by = 0.15 + (_HEADER_H - 0.32) / 2
        is_brand = btn.get("subtype") in ("brand", "destructive")
        ax.add_patch(FancyBboxPatch(
            (bx, by), bw, 0.32,
            boxstyle="round,pad=0.05",
            facecolor=_SLDS_BRAND if is_brand else "white",
            edgecolor=_SLDS_BRAND,
            linewidth=1.0,
        ))
        ax.text(bx + bw / 2, by + 0.16, lbl,
                ha="center", va="center",
                color="white" if is_brand else _SLDS_BRAND,
                **_fpkw(8.0, bold=True))
        btn_x = bx - 0.15

    # ── カード（白背景） ──────────────────────────────────────────────────
    card_top  = _HEADER_H + 0.30
    card_left = 0.3
    card_w    = fig_w - 0.6
    card_h    = body_h + _CARD_PAD * 2
    ax.add_patch(FancyBboxPatch(
        (card_left, card_top), card_w, max(card_h, 0.5),
        boxstyle="round,pad=0.06",
        facecolor="white", edgecolor=_SLDS_BORDER, linewidth=0.8,
    ))

    # ── フィールド描画 ────────────────────────────────────────────────────
    def _draw_fields(col: list[dict], x_start: float, col_w: float, y_start: float):
        y = y_start
        for f in col:
            ftype = f["type"]
            label = f.get("label", "")
            req   = f.get("required", False)
            fh    = _FIELD_H.get(ftype, 0.38)
            fw    = col_w - 0.2  # フィールド幅

            # ラベル
            if req:
                ax.text(x_start, y, label,
                        ha="left", va="top", color="#3E3E3C",
                        **_fpkw(8.5, bold=True))
                ax.text(x_start + len(label) * 0.14 + 0.05, y, "*",
                        ha="left", va="top", color="red",
                        **_fpkw(9.0, bold=True))
            else:
                ax.text(x_start, y, label,
                        ha="left", va="top", color="#3E3E3C",
                        **_fpkw(8.5, bold=True))

            y += _LABEL_H

            # 入力ボックス
            if ftype == "table":
                _draw_table_placeholder(ax, x_start, y, fw, fh, label)
            else:
                ax.add_patch(FancyBboxPatch(
                    (x_start, y), fw, fh,
                    boxstyle="round,pad=0.03",
                    facecolor="white", edgecolor=_SLDS_BORDER, linewidth=0.8,
                ))
                if ftype == "picklist":
                    ax.text(x_start + fw - 0.2, y + fh / 2, "\u25bc",
                            ha="center", va="center", color="#706E6B",
                            **_fpkw(8.0))

            y += fh + _GAP

    def _draw_table_placeholder(ax, x: float, y: float, w: float, h: float, label: str):
        """データテーブルのプレースホルダーを描画。"""
        cols = ["No", "\u9805\u76ee1", "\u9805\u76ee2", "\u9805\u76ee3"]
        col_ws = [w * 0.1, w * 0.35, w * 0.3, w * 0.25]
        row_h = h / 3.0

        # 外枠
        ax.add_patch(plt.Rectangle(
            (x, y), w, h,
            facecolor="white", edgecolor=_SLDS_BORDER, linewidth=0.8,
        ))

        # ヘッダー行
        cx = x
        for ci, (col_label, cw) in enumerate(zip(cols, col_ws)):
            ax.add_patch(plt.Rectangle(
                (cx, y), cw, row_h,
                facecolor=_SLDS_GRAY, edgecolor=_SLDS_BORDER, linewidth=0.5,
            ))
            ax.text(cx + cw / 2, y + row_h / 2, col_label,
                    ha="center", va="center", color="#3E3E3C",
                    **_fpkw(7.0, bold=True))
            cx += cw

        # データ行（空）
        for ri in range(1, 3):
            ry = y + row_h * ri
            cx = x
            for cw in col_ws:
                ax.add_patch(plt.Rectangle(
                    (cx, ry), cw, row_h,
                    facecolor="white", edgecolor=_SLDS_BORDER, linewidth=0.3,
                ))
                cx += cw

    # カラム描画
    field_y_start = card_top + _CARD_PAD
    if use_two_col:
        half_w = (card_w - _CARD_PAD) / 2
        _draw_fields(col_left,  card_left + _CARD_PAD / 2, half_w, field_y_start)
        _draw_fields(col_right, card_left + half_w + _CARD_PAD / 2, half_w, field_y_start)
    else:
        _draw_fields(col_left, card_left + _CARD_PAD / 2, card_w - _CARD_PAD, field_y_start)

    # ── 保存 ──────────────────────────────────────────────────────────────
    plt.savefig(out_path, dpi=180, bbox_inches="tight", facecolor=_SLDS_GRAY)
    plt.close(fig)
    return True
