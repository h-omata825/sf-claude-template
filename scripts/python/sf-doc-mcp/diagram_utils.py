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
