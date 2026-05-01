#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ER図 PNG 生成モジュール（matplotlib ベース）

flowchart_utils.py と同じアーキテクチャ:
  generate_er_image(boxes, arrows, out_path, title) を呼ぶだけで PNG が生成される。

座標系: generate_data_model.py の layout 関数と同じ inch 単位 (PowerPoint 座標系)
  - x: 0〜13.333"  (左→右)
  - y: 0〜7.5"     (上→下)

呼び出し側は boxes/arrows を generate_pptx.py の "er" layout と同じ JSON 形式で渡す。
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
    from matplotlib.patches import FancyBboxPatch
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── 日本語フォント ────────────────────────────────────────────────────────────
_JP_REG  = os.environ.get("JAPANESE_FONT_PATH",      "C:/Windows/Fonts/YuGothR.ttc")
_JP_BOLD = os.environ.get("JAPANESE_FONT_PATH_BOLD", "C:/Windows/Fonts/YuGothB.ttc")


def _fpkw(size: float = 8.0, bold: bool = False) -> dict:
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
# generate_pptx.py の _ER_HDR_COLORS と一致させる
STYLE_COLORS: dict[str, dict] = {
    "primary":   {"hdr": "#1E3A5F", "hdr_fg": "#FFFFFF",
                  "body": "#EBF0F8", "border": "#1E3A5F", "alt": "#D6E4F0"},
    "accent":    {"hdr": "#E86C00", "hdr_fg": "#FFFFFF",
                  "body": "#FFF2E8", "border": "#E86C00", "alt": "#FFE0B2"},
    "secondary": {"hdr": "#2C6FAC", "hdr_fg": "#FFFFFF",
                  "body": "#E8F4FF", "border": "#2C6FAC", "alt": "#C9E4F5"},
    "light":     {"hdr": "#6B6B6B", "hdr_fg": "#FFFFFF",
                  "body": "#F8F8F8", "border": "#AAAAAA", "alt": "#EBEBEB"},
    "ref":       {"hdr": "#AAAAAA", "hdr_fg": "#FFFFFF",
                  "body": "#FFFFFF", "border": "#AAAAAA", "alt": "#F5F5F5"},
}

_OWD_BADGE: dict[str, tuple] = {
    "private":            ("#FFDDDD", "#8B0000"),
    "非公開":             ("#FFDDDD", "#8B0000"),
    "read write":         ("#DDFFDD", "#006600"),
    "readwrite":          ("#DDFFDD", "#006600"),
    "public read write":  ("#DDFFDD", "#006600"),
    "read only":          ("#FFFFC8", "#806000"),
    "readonly":           ("#FFFFC8", "#806000"),
    "public read only":   ("#FFFFC8", "#806000"),
    "controlledbyparent": ("#DDEEFFE"[:-1], "#004080"),
    "cbp":                ("#DDEEFF", "#004080"),
    "親管理":             ("#DDEEFF", "#004080"),
}

# ── レイアウト定数 ─────────────────────────────────────────────────────────────
SLIDE_W  = 13.333
SLIDE_H  = 7.5
TITLE_H  = 1.10      # タイトルバーの高さ
HDR_H    = 0.62      # ボックスヘッダーの高さ
FIELD_H  = 0.32      # フィールド行の高さ
DPI      = 220

# リレーション記号の定数
ARROW_MD_COLOR = "#CC2200"   # 主従: 赤
ARROW_LU_COLOR = "#2C6FAC"   # 参照: 青
DIAMOND_LEN    = 0.26        # 菱形の全長（ボックス端→先端）
DIAMOND_SPREAD = 0.078       # 菱形の幅の半分
CIRCLE_R       = 0.075       # オプション丸の半径
BAR_HALF       = 0.090       # バーの半幅
CF_LEN         = 0.155       # クロウフット: apex までの距離
CF_SPREAD      = 0.090       # クロウフット: 扇の広がり
CF_EXTRA       = 0.155       # クロウフット先に追加する記号のオフセット

# 辺ごとの「ボックス外向き方向ベクトル」
SIDE_DIR: dict[str, tuple] = {
    "right":  ( 1,  0),
    "left":   (-1,  0),
    "bottom": ( 0,  1),
    "top":    ( 0, -1),
}


def _hex(s: str) -> tuple:
    """#RRGGBB → (r, g, b) [0, 1]"""
    s = s.lstrip("#")
    return tuple(int(s[i:i+2], 16) / 255 for i in (0, 2, 4))


def _owd_short(owd: str) -> str:
    if not owd:
        return ""
    low = owd.lower()
    if "controlledbyparent" in low or "cbp" in low or "親管理" in owd:
        return "CbP"
    if "private" in low or "非公開" in owd:
        return "Priv"
    if "read" in low and "write" in low:
        return "R/W"
    if "read" in low:
        return "R/O"
    return owd[:8]


def _owd_badge_colors(owd: str) -> tuple[Optional[str], Optional[str]]:
    if not owd:
        return None, None
    low = owd.lower()
    for key, (bg, fg) in _OWD_BADGE.items():
        if key in low:
            return bg, fg
    return "#E0E0E0", "#404040"


# ── ボックス描画 ──────────────────────────────────────────────────────────────

def _draw_box(ax, box: dict) -> dict:
    """ER ボックスを描画し、辺の中心座標などを返す。

    Returns:
        dict: x, y, w, h, top, bottom, left, right の辺中点
    """
    x, y, w, h = box["x"], box["y"], box["w"], box["h"]
    sc       = STYLE_COLORS.get(box.get("style", "primary"), STYLE_COLORS["light"])
    is_ref   = bool(box.get("ref_only", False))
    fields   = [] if is_ref else [f for f in box.get("fields", []) if f.get("is_fk")]

    # 1. 外枠 FancyBboxPatch（ボディ背景 + 角丸ボーダー用）
    pad = 0.04
    outer = FancyBboxPatch(
        (x + pad, y + pad), w - 2 * pad, h - 2 * pad,
        boxstyle=f"round,pad={pad}",
        linewidth=1.4,
        linestyle=(0, (4, 2)) if is_ref else "-",
        edgecolor=_hex(sc["border"]),
        facecolor=_hex(sc["body"]),
        zorder=2,
    )
    ax.add_patch(outer)

    # 2. ヘッダー背景（outer を clip_path に使って角丸を継承）
    hdr_rect = mpatches.Rectangle(
        (x, y), w, HDR_H,
        linewidth=0, edgecolor="none",
        facecolor=_hex(sc["hdr"]),
        zorder=3,
    )
    hdr_rect.set_clip_path(outer)
    ax.add_patch(hdr_rect)

    # 3. 区切り線
    ax.plot([x, x + w], [y + HDR_H, y + HDR_H],
            color=_hex(sc["border"]), linewidth=0.7, zorder=4, solid_capstyle="butt")

    # 4. OWD バッジ（ヘッダー右端に小さく）
    owd       = box.get("owd", "")
    owd_label = _owd_short(owd)
    badge_w   = 0.0
    if owd_label and not is_ref:
        bg_col, fg_col = _owd_badge_colors(owd)
        badge_w  = max(len(owd_label) * 0.065 + 0.12, 0.30)
        badge_h  = 0.20
        bx_      = x + w - badge_w - 0.08
        by_      = y + (HDR_H - badge_h) / 2
        badge = FancyBboxPatch(
            (bx_ + 0.01, by_ + 0.01), badge_w - 0.02, badge_h - 0.02,
            boxstyle="round,pad=0.01",
            linewidth=0, edgecolor="none",
            facecolor=_hex(bg_col),
            zorder=5,
        )
        badge.set_clip_path(outer)
        ax.add_patch(badge)
        ax.text(bx_ + badge_w / 2, by_ + badge_h / 2, owd_label,
                ha="center", va="center", color=_hex(fg_col),
                zorder=6, clip_on=True, **_fpkw(6.5, bold=True))

    # 5. ヘッダーテキスト（ラベル / API名 の2行）
    text_right = x + w - (badge_w + 0.12 if badge_w else 0.10)
    label  = box.get("label", box.get("api_name", ""))
    api    = box.get("api_name", "")
    tx     = x + 0.11
    if label and label != api:
        ax.text(tx, y + HDR_H * 0.35, label,
                ha="left", va="center", color=_hex(sc["hdr_fg"]),
                clip_on=True, zorder=5,
                **_fpkw(9.5, bold=True))
        ax.text(tx, y + HDR_H * 0.72, api,
                ha="left", va="center",
                color=(*_hex(sc["hdr_fg"]), 0.75),
                clip_on=True, zorder=5, **_fpkw(7.0))
    else:
        ax.text(tx, y + HDR_H / 2, label or api,
                ha="left", va="center", color=_hex(sc["hdr_fg"]),
                clip_on=True, zorder=5, **_fpkw(9.5, bold=True))

    # 6. フィールド行（FK のみ）
    for i, fld in enumerate(fields):
        fy = y + HDR_H + i * FIELD_H
        if fy + FIELD_H > y + h + 0.01:
            break

        # 交互背景
        if i % 2 == 1:
            row_bg = mpatches.Rectangle(
                (x, fy), w, FIELD_H,
                linewidth=0, facecolor=_hex(sc["alt"]), zorder=2,
            )
            row_bg.set_clip_path(outer)
            ax.add_patch(row_bg)

        # FK アイコン（小菱形）
        ix, iy = x + 0.12, fy + FIELD_H / 2
        ds = 0.052
        icon_pts = [(ix, iy - ds), (ix + ds * 1.5, iy),
                    (ix, iy + ds), (ix - ds * 1.5, iy)]
        fk_color = ARROW_MD_COLOR if fld.get("type") == "master_detail" else ARROW_LU_COLOR
        ax.add_patch(mpatches.Polygon(
            icon_pts, closed=True,
            facecolor=_hex(fk_color), edgecolor="none", zorder=4,
        ))

        fname = fld.get("label") or fld.get("api_name", "")
        ax.text(x + 0.24, fy + FIELD_H / 2, fname,
                ha="left", va="center", color="#1E1E1E",
                clip_on=True, zorder=4, **_fpkw(8.0, bold=True))

        ftype_lbl = {"master_detail": "MD"}.get(fld.get("type", ""), "ref")
        ax.text(x + w - 0.10, fy + FIELD_H / 2, ftype_lbl,
                ha="right", va="center", color=_hex(fk_color),
                clip_on=True, zorder=4, **_fpkw(6.5, bold=True))

    # フィールドなし（ref_only でない場合のみ）
    if not fields and not is_ref:
        ax.text(x + w / 2, y + HDR_H + 0.16, "（FK なし）",
                ha="center", va="top", color="#AAAAAA",
                clip_on=True, zorder=4, **_fpkw(7.0))

    # 7. レコード数（下端右）
    rc = box.get("record_count", "")
    if rc and not is_ref:
        rc_text = rc if ("件" in rc or "レコード" in rc) else f"{rc}件"
        ax.text(x + w - 0.10, y + h - 0.07, rc_text,
                ha="right", va="bottom", color="#888888",
                clip_on=True, zorder=4, **_fpkw(6.5))

    cx, cy = x + w / 2, y + h / 2
    return {
        "x": x, "y": y, "w": w, "h": h,
        "top":    (cx, y),
        "bottom": (cx, y + h),
        "left":   (x, cy),
        "right":  (x + w, cy),
    }


# ── リレーション矢印 ──────────────────────────────────────────────────────────

def _get_pt(edge: dict, side: str, frac: float = 0.5) -> tuple:
    x, y, w, h = edge["x"], edge["y"], edge["w"], edge["h"]
    if side == "top":    return (x + w * frac, y)
    if side == "bottom": return (x + w * frac, y + h)
    if side == "left":   return (x,     y + h * frac)
    if side == "right":  return (x + w, y + h * frac)
    return (x + w / 2, y + h / 2)


def _auto_sides(from_e: dict, to_e: dict) -> tuple[str, str]:
    """2ボックスの相対位置からデフォルト接続辺を決定する。"""
    fx = from_e["x"] + from_e["w"] / 2
    fy = from_e["y"] + from_e["h"] / 2
    tx = to_e["x"]   + to_e["w"] / 2
    ty = to_e["y"]   + to_e["h"] / 2
    dx, dy = tx - fx, ty - fy
    if abs(dx) >= abs(dy):
        return ("right" if dx > 0 else "left", "left" if dx > 0 else "right")
    else:
        return ("bottom" if dy > 0 else "top", "top" if dy > 0 else "bottom")


def _draw_diamond_marker(ax, px: float, py: float, side: str, color: str) -> tuple:
    """親側に菱形（◆）を描画し、線の開始点（菱形の先端）を返す。"""
    dx, dy = SIDE_DIR[side]
    # 垂直方向（菱形の幅方向）
    px_d = -dy   # perpendicular: (-dy, dx) rotated 90°
    py_d = dx

    half = DIAMOND_LEN / 2
    tip  = (px + dx * DIAMOND_LEN, py + dy * DIAMOND_LEN)
    mid  = (px + dx * half,        py + dy * half)
    pl   = (mid[0] + px_d * DIAMOND_SPREAD, mid[1] + py_d * DIAMOND_SPREAD)
    pr   = (mid[0] - px_d * DIAMOND_SPREAD, mid[1] - py_d * DIAMOND_SPREAD)

    diamond = mpatches.Polygon(
        [(px, py), pl, tip, pr], closed=True,
        facecolor=_hex(color), edgecolor=_hex(color),
        linewidth=0.8, zorder=7,
    )
    ax.add_patch(diamond)
    return tip


def _draw_one_opt_marker(ax, px: float, py: float, side: str, color: str) -> tuple:
    """親側（参照 Lookup）に ○| マーカーを描画し、線の開始点を返す。
    ボックス端から: バー → 丸 の順（外側が丸）"""
    dx, dy = SIDE_DIR[side]
    c  = _hex(color)
    lw = 1.3

    # バー（ボックスに近い側）
    bar_off = 0.08
    bx, by = px + dx * bar_off, py + dy * bar_off
    if dx != 0:  # 水平線 → 垂直バー
        ax.plot([bx, bx], [by - BAR_HALF, by + BAR_HALF],
                color=c, linewidth=lw + 0.4, zorder=7, solid_capstyle="butt")
    else:        # 垂直線 → 水平バー
        ax.plot([bx - BAR_HALF, bx + BAR_HALF], [by, by],
                color=c, linewidth=lw + 0.4, zorder=7, solid_capstyle="butt")

    # 丸（外側）
    circ_off = bar_off + 0.14
    cx_, cy_ = px + dx * circ_off, py + dy * circ_off
    ax.add_patch(mpatches.Circle(
        (cx_, cy_), CIRCLE_R,
        facecolor="white", edgecolor=c, linewidth=lw, zorder=7,
    ))
    return (px + dx * (circ_off + CIRCLE_R + 0.02),
            py + dy * (circ_off + CIRCLE_R + 0.02))


def _draw_crow_foot(ax, px: float, py: float, side: str,
                    color: str, optional: bool) -> tuple:
    """子側にクロウフット記号を描画し、線の終点（記号の外端）を返す。

    optional=True  → ○|< （参照子側: 0以上）
    optional=False → |<  （主従子側: 1以上）
    """
    dx, dy = SIDE_DIR[side]
    c  = _hex(color)
    lw = 1.3

    # クロウフット: apex から box_edge へ 3 本の扇形線
    # apex は box_edge から CF_LEN 離れた位置（外側）
    ax_ = px + dx * CF_LEN
    ay_ = py + dy * CF_LEN
    if dx != 0:  # 水平
        fan = [(px, py - CF_SPREAD), (px, py), (px, py + CF_SPREAD)]
    else:        # 垂直
        fan = [(px - CF_SPREAD, py), (px, py), (px + CF_SPREAD, py)]

    for fp in fan:
        ax.plot([ax_, fp[0]], [ay_, fp[1]],
                color=c, linewidth=lw, zorder=7, solid_capstyle="round")

    # バー（| ）: CF_LEN + CF_EXTRA の位置
    bar_off = CF_LEN + CF_EXTRA
    bx, by  = px + dx * bar_off, py + dy * bar_off
    if dx != 0:
        ax.plot([bx, bx], [by - BAR_HALF, by + BAR_HALF],
                color=c, linewidth=lw + 0.4, zorder=7, solid_capstyle="butt")
    else:
        ax.plot([bx - BAR_HALF, bx + BAR_HALF], [by, by],
                color=c, linewidth=lw + 0.4, zorder=7, solid_capstyle="butt")

    if optional:
        # 丸（○）: バーのさらに外側
        circ_off = bar_off + 0.14
        cx_, cy_ = px + dx * circ_off, py + dy * circ_off
        ax.add_patch(mpatches.Circle(
            (cx_, cy_), CIRCLE_R,
            facecolor="white", edgecolor=c, linewidth=lw, zorder=7,
        ))
        return (px + dx * (circ_off + CIRCLE_R + 0.02),
                py + dy * (circ_off + CIRCLE_R + 0.02))
    else:
        return (px + dx * (bar_off + 0.04),
                py + dy * (bar_off + 0.04))


def _clear_mid_x(x1: float, y1: float, x2: float, y2: float,
                  mid_x: float, box_edges: dict,
                  skip_ids: set = None) -> float:
    """垂直セグメント(mid_x, y1..y2)がボックスと重なる場合、mid_x をボックス外へシフトする。
    skip_ids: 始終端ボックスのIDセット（除外対象）。
    """
    skip_ids = skip_ids or set()
    y_lo = min(y1, y2) + 0.02
    y_hi = max(y1, y2) - 0.02
    x_lo = min(x1, x2)
    x_hi = max(x1, x2)
    margin = 0.04

    for _pass in range(3):  # mid_x を移動した後も再チェック（最大3回）
        blocking = []
        for bid, be in box_edges.items():
            if bid in skip_ids:
                continue
            bx, by, bw, bh = be["x"], be["y"], be["w"], be["h"]
            if (bx < mid_x + margin and bx + bw > mid_x - margin and
                    by < y_hi and by + bh > y_lo):
                blocking.append(be)
        if not blocking:
            break
        right_edge = max(be["x"] + be["w"] for be in blocking)
        left_edge  = min(be["x"] for be in blocking)
        # 右に出す余地 vs 左に出す余地（スライド範囲内）
        gap_right = x_hi - right_edge
        gap_left  = left_edge - x_lo
        if gap_right >= gap_left and right_edge + 0.12 <= x_hi:
            mid_x = right_edge + 0.10
        elif left_edge - 0.12 >= x_lo:
            mid_x = left_edge - 0.10
        else:
            break  # どちらにも余地がない場合は諦める
    return mid_x


def _clear_mid_y(x1: float, y1: float, x2: float, y2: float,
                  mid_y: float, box_edges: dict,
                  skip_ids: set = None) -> float:
    """水平セグメント(x1..x2, mid_y)がボックスと重なる場合、mid_y をボックス外へシフトする。
    skip_ids: 始終端ボックスのIDセット（除外対象）。
    """
    skip_ids = skip_ids or set()
    x_lo = min(x1, x2) + 0.02
    x_hi = max(x1, x2) - 0.02
    y_lo = min(y1, y2)
    y_hi = max(y1, y2)
    margin = 0.04

    for _pass in range(3):
        blocking = []
        for bid, be in box_edges.items():
            if bid in skip_ids:
                continue
            bx, by, bw, bh = be["x"], be["y"], be["w"], be["h"]
            if (by < mid_y + margin and by + bh > mid_y - margin and
                    bx < x_hi and bx + bw > x_lo):
                blocking.append(be)
        if not blocking:
            break
        top_edge = min(be["y"] for be in blocking)
        bot_edge = max(be["y"] + be["h"] for be in blocking)
        gap_above = top_edge - y_lo
        gap_below = y_hi - bot_edge
        if gap_above >= gap_below and top_edge - 0.12 >= y_lo:
            mid_y = top_edge - 0.10
        elif bot_edge + 0.12 <= y_hi:
            mid_y = bot_edge + 0.10
        else:
            break
    return mid_y


def _route_line(
    p1: tuple, side1: str,
    p2: tuple, side2: str,
    box_edges: dict = None,
    skip_ids: set = None,
) -> list:
    """2点間の直角折れ線経路を計算する（z字形またはL字形）。
    box_edges が渡された場合、中間セグメントがボックスを避けるよう mid_x/mid_y を調整する。
    skip_ids: 始終端ボックスのIDセット（回避対象から除外）。
    """
    x1, y1 = p1
    x2, y2 = p2

    if side1 in ("left", "right"):
        # 水平出発: 中間X で折れる（垂直セグメントを回避）
        mid_x = (x1 + x2) / 2
        if box_edges:
            mid_x = _clear_mid_x(x1, y1, x2, y2, mid_x, box_edges, skip_ids=skip_ids)
        return [(x1, y1), (mid_x, y1), (mid_x, y2), (x2, y2)]
    else:
        # 垂直出発: 中間Y で折れる（水平セグメントを回避）
        mid_y = (y1 + y2) / 2
        if box_edges:
            mid_y = _clear_mid_y(x1, y1, x2, y2, mid_y, box_edges, skip_ids=skip_ids)
        return [(x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)]


def _draw_arrow(ax, edges: dict, arrow: dict, box_edges: dict = None) -> None:
    """1本のリレーション矢印を描画する。"""
    from_id = arrow.get("from", "")
    to_id   = arrow.get("to",   "")
    if from_id not in edges or to_id not in edges:
        return

    is_md     = arrow.get("arrow_style") == "master_detail"
    color     = ARROW_MD_COLOR if is_md else ARROW_LU_COLOR
    line_lw   = 1.8 if is_md else 1.2
    line_ls   = "-" if is_md else (0, (5, 3))

    from_e = edges[from_id]
    to_e   = edges[to_id]

    # 辺の決定（JSON で明示されていれば尊重）
    side_from = arrow.get("side_from") or "_auto"
    side_to   = arrow.get("side_to")   or "_auto"
    if "_auto" in (side_from, side_to):
        sf, st = _auto_sides(from_e, to_e)
        if side_from == "_auto": side_from = sf
        if side_to   == "_auto": side_to   = st

    frac_from = float(arrow.get("side_from_frac", 0.5))
    frac_to   = float(arrow.get("side_to_frac",   0.5))

    p_from = _get_pt(from_e, side_from, frac_from)
    p_to   = _get_pt(to_e,   side_to,   frac_to)

    # ── 親側マーカー ──
    if is_md:
        line_start = _draw_diamond_marker(ax, p_from[0], p_from[1], side_from, color)
    else:
        line_start = _draw_one_opt_marker(ax, p_from[0], p_from[1], side_from, color)

    # ── 子側マーカー ──
    child_optional = not is_md   # MD 子は必須(|<), Lookup 子は任意(○|<)
    line_end = _draw_crow_foot(ax, p_to[0], p_to[1], side_to, color, child_optional)

    # ── 接続線 ──（始終端ボックスは回避対象から除外）
    skip_ids = {from_id, to_id}
    pts = _route_line(line_start, side_from, line_end, side_to, box_edges=box_edges, skip_ids=skip_ids)
    xs  = [p[0] for p in pts]
    ys  = [p[1] for p in pts]
    ax.plot(xs, ys, color=_hex(color), linewidth=line_lw, linestyle=line_ls,
            zorder=5, solid_capstyle="round", solid_joinstyle="round",
            dash_capstyle="round")

    # ── ラベル（FK フィールド名）──
    label = arrow.get("label", "")
    if label and len(label) <= 30:
        n  = len(pts)
        mi = n // 2
        mx = (pts[mi - 1][0] + pts[mi][0]) / 2
        my = (pts[mi - 1][1] + pts[mi][1]) / 2
        ax.text(mx, my, label,
                ha="center", va="center", color=_hex(color),
                bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=0.85),
                zorder=8, **_fpkw(5.5))


# ── メイン生成関数 ────────────────────────────────────────────────────────────

def generate_er_image(
    boxes:    list,
    arrows:   list,
    out_path: str,
    title:    str = "",
    slide_w:  float = SLIDE_W,
    slide_h:  float = SLIDE_H,
) -> bool:
    """ER図を PNG ファイルとして出力する。

    Args:
        boxes:    ER ボックスのリスト（generate_data_model.py の JSON 形式）
        arrows:   リレーション矢印のリスト
        out_path: 出力先 PNG パス
        title:    スライドタイトル文字列
        slide_w:  スライド幅（inch）
        slide_h:  スライド高さ（inch）
    Returns:
        True=成功 / False=matplotlib 未インストール
    """
    if not HAS_MPL:
        return False

    fig, ax = plt.subplots(figsize=(slide_w, slide_h), dpi=DPI)
    ax.set_xlim(0, slide_w)
    ax.set_ylim(slide_h, 0)   # Y 軸反転: 上が 0 (PowerPoint 座標系)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # ── タイトルバー ──
    title_bar = mpatches.Rectangle(
        (0, 0), slide_w, TITLE_H,
        linewidth=0, facecolor=_hex("#1E3A5F"), zorder=1,
    )
    ax.add_patch(title_bar)
    if title:
        ax.text(0.55, TITLE_H / 2, title,
                ha="left", va="center", color="white",
                zorder=2, **_fpkw(16.0, bold=True))

    # ── ボックス描画 ──
    edges: dict[str, dict] = {}
    for box in boxes:
        edge = _draw_box(ax, box)
        edges[box["id"]] = edge

    # ── 矢印描画（ボックスの上に重ねる）──
    for arrow in arrows:
        _draw_arrow(ax, edges, arrow, box_edges=edges)

    fig.savefig(out_path, dpi=DPI, bbox_inches=None,
                facecolor="white", pad_inches=0)
    plt.close(fig)
    return True


def generate_er_legend_image(out_path: str,
                              slide_w: float = SLIDE_W,
                              slide_h: float = SLIDE_H) -> bool:
    """ER図 凡例スライドを PNG で出力する。"""
    if not HAS_MPL:
        return False

    fig, ax = plt.subplots(figsize=(slide_w, slide_h), dpi=DPI)
    ax.set_xlim(0, slide_w)
    ax.set_ylim(slide_h, 0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # タイトルバー
    ax.add_patch(mpatches.Rectangle(
        (0, 0), slide_w, TITLE_H,
        linewidth=0, facecolor=_hex("#1E3A5F"), zorder=1,
    ))
    ax.text(0.55, TITLE_H / 2, "ER図 凡例",
            ha="left", va="center", color="white", zorder=2, **_fpkw(16.0, bold=True))

    y = TITLE_H + 0.38

    def section(text, y_pos):
        ax.text(0.55, y_pos, text, ha="left", va="top",
                color=_hex("#1E3A5F"), zorder=2, **_fpkw(12.5, bold=True))

    def desc(text, y_pos, indent=2.6):
        ax.text(indent, y_pos + 0.17, text, ha="left", va="center",
                color=_hex("#2D2D2D"), zorder=2, **_fpkw(10.5))

    # ── リレーション種別 ──
    section("【リレーション種別】", y); y += 0.38

    # MD サンプル線
    lx1, lx2, ly = 0.6, 3.2, y + 0.15
    tip = _draw_diamond_marker(ax, lx1, ly, "right", ARROW_MD_COLOR)
    _draw_crow_foot(ax, lx2, ly, "left", ARROW_MD_COLOR, optional=False)
    ax.plot([tip[0], lx2 + CF_LEN + CF_EXTRA + 0.10], [ly, ly],
            color=_hex(ARROW_MD_COLOR), linewidth=1.8, zorder=5)
    desc("主従（Master-Detail）: 実線・赤   ◆ が親（Master）側   |< が子（必須多）", y)
    y += 0.45

    # Lookup サンプル線
    ly = y + 0.15
    line_s = _draw_one_opt_marker(ax, lx1, ly, "right", ARROW_LU_COLOR)
    _draw_crow_foot(ax, lx2, ly, "left", ARROW_LU_COLOR, optional=True)
    ax.plot([line_s[0], lx2 + CF_LEN + CF_EXTRA + CIRCLE_R + 0.14], [ly, ly],
            color=_hex(ARROW_LU_COLOR), linewidth=1.2, linestyle=(0, (5, 3)), zorder=5)
    desc("参照（Lookup）: 破線・青   ○| が親（任意1）   ○|< が子（任意多）", y)
    y += 0.55

    # ── ボックスカラー ──
    section("【ボックスカラー凡例】", y); y += 0.38

    colors_info = [
        ("primary",   "TX系（トランザクション）オブジェクト"),
        ("accent",    "マスタ系オブジェクト"),
        ("secondary", "標準オブジェクト（外部参照）"),
        ("light",     "補助・制御 / ログ系オブジェクト"),
        ("ref",       "ref_only（破線枠）: TX から参照される外部オブジェクト"),
    ]
    for style_key, desc_text in colors_info:
        sc = STYLE_COLORS.get(style_key, STYLE_COLORS["light"])
        swatch = FancyBboxPatch(
            (0.65, y + 0.04), 0.38, 0.22,
            boxstyle="round,pad=0.02",
            linewidth=1.0,
            linestyle=(0, (4, 2)) if style_key == "ref" else "-",
            edgecolor=_hex(sc["border"]),
            facecolor=_hex(sc["hdr"]),
            zorder=2,
        )
        ax.add_patch(swatch)
        ax.text(1.20, y + 0.15, desc_text, ha="left", va="center",
                color=_hex("#2D2D2D"), zorder=2, **_fpkw(9.5))
        y += 0.30

    y += 0.25

    # ── 記号説明 ──
    section("【記号説明】", y); y += 0.38

    symbol_rows = [
        ("◆",   "主従の親側（Master）"),
        ("○|",  "参照の親側（任意 1）"),
        ("|<",  "主従の子側（必須 多）"),
        ("○|<", "参照の子側（任意 多）"),
    ]
    for sym, sym_desc in symbol_rows:
        ax.text(1.0, y + 0.14, sym, ha="center", va="center",
                color=_hex("#1E3A5F"), zorder=2, **_fpkw(11.0, bold=True))
        ax.text(1.7, y + 0.14, sym_desc, ha="left", va="center",
                color=_hex("#2D2D2D"), zorder=2, **_fpkw(9.5))
        y += 0.28

    fig.savefig(out_path, dpi=DPI, bbox_inches=None,
                facecolor="white", pad_inches=0)
    plt.close(fig)
    return True
