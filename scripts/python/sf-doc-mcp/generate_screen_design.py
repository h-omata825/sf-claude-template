"""
画面設計書.xlsx を1画面分生成する（テンプレート読込方式）。

LWC / 画面フロー / Visualforce 共用。JSON の構造で UC・パラメータセクションを
動的に決定するため、画面種別ごとに適した切り口で記述できる。

5シート構成:
  1. 改版履歴       : メタ + 初版自動投入
  2. 画面概要       : メタ2段 + 目的/概要/主要機能(箇条書)/前提/画面遷移/画面イメージ(簡易WF)
  3. 画面項目定義   : 項目テーブル
  4. 処理詳細       : JSON の usecases[] をUCブロックとして順次描画
  5. パラメーター定義: JSON の param_sections[] をセクションとして順次描画

Usage:
  python generate_screen_design.py \
    --input     screen_design.json \
    --template  "C:/.../画面設計書テンプレート.xlsx" \
    --output-dir "C:/.../出力ルート"
"""
from __future__ import annotations
import argparse
import json
import sys
import tempfile
from datetime import date as _date
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.utils.units import pixels_to_EMU

from meta_store import read_meta, write_meta
from version_manager import increment_version
import design_revision as dr

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib.patches import FancyBboxPatch, Rectangle
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

import os as _os
_JP_FONT_PATH = "C:/Windows/Fonts/YuGothR.ttc"
JP_FONT_PROP = None
if _os.path.exists(_JP_FONT_PATH) and HAS_MPL:
    JP_FONT_PROP = fm.FontProperties(fname=_JP_FONT_PATH)

from flowchart_utils import generate_flowchart

# ── 色 ──────────────────────────────────────────────────────────
C_HDR_BLUE   = "2E75B6"
C_BAND_BLUE  = "0070C0"
C_SUB_BAND   = "5B9BD5"
C_LABEL_BG   = "D9E1F2"
C_STEP_BG    = "E2EFDA"
C_FONT_D     = "000000"
C_FONT_GRAY  = "595959"
C_FONT_W     = "FFFFFF"

THIN = Side(style="thin",   color="8B9DC3")
MED  = Side(style="medium", color="1F3864")

TYPE_FOLDER = {
    "LWC":          "lwc",
    "画面フロー":    "flow",
    "Flow":         "flow",
    "Visualforce":  "visualforce",
    "Aura":         "aura",
    "その他":        "other",
}

# ── テンプレートと一致させる定数 ────────────────────────────────
# 改版履歴
REV_META_ROW       = 3
REV_META_PROJECT_V = (7, 18)
REV_META_DATE_V    = (23, 31)
REV_DATA_ROW_START = 6
REV_COLS = {
    "項番":     (2,  3),
    "版数":     (4,  5),
    "変更箇所": (6, 11),
    "変更内容": (12, 17),
    "変更理由": (18, 23),
    "変更日":   (24, 26),
    "変更者":   (27, 29),
    "備考":     (30, 31),
}

# 画面概要
OV_META_ROW_1 = 3
OV_META_ROW_2 = 4
OV_META_1_V = {
    "project_name": (6, 14),
    "system_name":  (18, 22),
    "name":         (26, 31),
}
OV_META_2_V = {
    "api_name": (6, 14),
    "author":   (18, 20),
    "date":     (24, 26),
    "version":  (29, 31),
}
OV_SECTION_DATA_ROW = {
    "purpose":       7,
    "overview":      10,
    # "features" は箇条書き（bullet list）でデータ行13に書く
    "prerequisites": 16,
    "transition":    19,
}
OV_FEATURES_ROW = 13
OV_IMG_DATA_START = 22   # 画面イメージ画像貼付行の先頭

# 画面項目定義
IT_DATA_ROW_START = 5
IT_COLS = {
    "no":          (2,  3),
    "label":       (4,  8),
    "api_name":    (9,  14),
    "ui_type":     (15, 17),
    "type":        (18, 20),
    "required":    (21, 22),
    "default":     (23, 25),
    "validation":  (26, 28),
    "note":        (29, 31),
}

# 処理詳細（動的UCブロック）— 機能設計書と同じ「左:表 / 右:フロー図」構成
LG_CONTENT_START_ROW = 3
# 左半分（ステップ詳細テーブル）
LG_LEFT_NO     = (2,  3)
LG_LEFT_TITLE  = (4,  7)
LG_LEFT_DETAIL = (8,  16)
LG_LEFT_END    = 16
# 右半分（フロー図の貼付領域）
LG_FLOW_CS     = 18
LG_FLOW_CE     = 31

# パラメーター定義（動的セクションブロック）
PM_CONTENT_START_ROW = 3
PM_COLS = {
    "no":       (2,  3),
    "key":      (4,  10),
    "type":     (11, 14),
    "required": (15, 16),
    "desc":     (17, 25),
    "default":  (26, 28),
    "note":     (29, 31),
}

GRID_LEFT  = 2
GRID_RIGHT = 31


# ── ヘルパー ───────────────────────────────────────────────────
def _fnt(bold=False, color=C_FONT_D, size=10, italic=False):
    return Font(name="游ゴシック", bold=bold, color=color,
                size=size, italic=italic)
def _aln(h="left", v="center", wrap=True):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)
def _fill(c): return PatternFill("solid", fgColor=c)
def B_all(): return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

def W(ws, row, col, value="", bold=False, fg=C_FONT_D, bg=None,
      h="left", v="center", wrap=True, size=10, italic=False, border=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font = _fnt(bold=bold, color=fg, size=size, italic=italic)
    c.alignment = _aln(h=h, v=v, wrap=wrap)
    if bg: c.fill = _fill(bg)
    if border: c.border = border
    return c

def MW(ws, row, cs, ce, value="", border=None, bg=None,
       bold=False, fg=C_FONT_D, h="left", v="center",
       wrap=True, size=10, italic=False):
    if border:
        for c in range(cs, ce + 1):
            ws.cell(row=row, column=c).border = border
    if bg:
        for c in range(cs, ce + 1):
            ws.cell(row=row, column=c).fill = _fill(bg)
    ws.merge_cells(start_row=row, start_column=cs, end_row=row, end_column=ce)
    cell = ws.cell(row=row, column=cs, value=value)
    cell.font = _fnt(bold=bold, color=fg, size=size, italic=italic)
    cell.alignment = _aln(h=h, v=v, wrap=wrap)
    if bg: cell.fill = _fill(bg)
    if border: cell.border = border
    return cell

def set_h(ws, row, h):
    ws.row_dimensions[row].height = h


# ── ワイヤーフレーム生成 ──────────────────────────────────────
def _fpkw():
    return {"fontproperties": JP_FONT_PROP} if JP_FONT_PROP else {}

def generate_wireframe(screen_name: str, items: list, out_path: str) -> bool:
    """画面項目定義から簡易ワイヤーフレームPNGを生成する。"""
    if not HAS_MPL or not items:
        return False

    # 表示対象: items を UI種別ごとに並べる
    # UI種別: 表示のみ / テキスト入力 / 選択 / ボタン / チェックボックス / ...
    item_list = items[:20]  # 最大20項目
    n = len(item_list)

    fig_w = 5.0
    fig_h = max(4.0, 1.2 + n * 0.55)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w); ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    # 外枠（画面風）
    frame = FancyBboxPatch(
        (0.15, 0.15), fig_w - 0.3, fig_h - 0.3,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor="#FAFBFD", edgecolor="#444444", linewidth=1.2)
    ax.add_patch(frame)

    # タイトルバー
    title_h = 0.45
    title_bar = Rectangle(
        (0.2, fig_h - 0.2 - title_h), fig_w - 0.4, title_h,
        facecolor="#1F3864", edgecolor="#1F3864")
    ax.add_patch(title_bar)
    ax.text(fig_w / 2, fig_h - 0.2 - title_h / 2, screen_name,
            ha="center", va="center", color="white",
            fontsize=10, weight="bold", **_fpkw())

    # 項目を縦に並べる
    label_col_x = 0.35
    field_col_x = fig_w * 0.40
    row_h = 0.48
    y = fig_h - 0.25 - title_h - 0.2

    for it in item_list:
        label = it.get("label", "")
        ui_type = it.get("ui_type", "")
        required = it.get("required", False)

        # ラベル
        mark = "* " if required else "  "
        ax.text(label_col_x, y - row_h / 2, mark + label,
                ha="left", va="center", fontsize=8.5,
                color="#333333", **_fpkw())

        # フィールド枠（UI種別で形を変える）
        fw = fig_w * 0.52
        fh = 0.32
        fx = field_col_x
        fy = y - row_h / 2 - fh / 2

        if "ボタン" in ui_type or "button" in ui_type.lower():
            btn_w = 1.2
            btn = FancyBboxPatch(
                (fx, fy), btn_w, fh,
                boxstyle="round,pad=0.01,rounding_size=0.05",
                facecolor="#0070C0", edgecolor="#004F86")
            ax.add_patch(btn)
            ax.text(fx + btn_w / 2, y - row_h / 2, label,
                    ha="center", va="center", fontsize=8,
                    color="white", **_fpkw())
            # ボタンの場合はラベル列は消す（上で描いたものをマスクするため再描画しない）
            ax.text(label_col_x, y - row_h / 2, "",
                    ha="left", va="center")
        elif "選択" in ui_type or "combo" in ui_type.lower() or "picklist" in ui_type.lower():
            ax.add_patch(Rectangle((fx, fy), fw, fh,
                        facecolor="white", edgecolor="#888888"))
            # 右端に▼
            ax.text(fx + fw - 0.12, y - row_h / 2, "▼",
                    ha="center", va="center", fontsize=7, color="#555555")
            ax.text(fx + 0.08, y - row_h / 2, "（選択）",
                    ha="left", va="center", fontsize=7,
                    color="#AAAAAA", **_fpkw())
        elif "ラジオ" in ui_type or "radio" in ui_type.lower():
            ax.text(fx + 0.08, y - row_h / 2, "○ はい    ○ いいえ",
                    ha="left", va="center", fontsize=8,
                    color="#555555", **_fpkw())
        elif "チェック" in ui_type or "check" in ui_type.lower():
            ax.add_patch(Rectangle((fx, fy + fh/2 - 0.08), 0.18, 0.18,
                        facecolor="white", edgecolor="#555555"))
            ax.text(fx + 0.28, y - row_h / 2, "有効にする",
                    ha="left", va="center", fontsize=8,
                    color="#555555", **_fpkw())
        elif "表示" in ui_type or "display" in ui_type.lower() or "text" in ui_type.lower() and "入力" not in ui_type:
            ax.text(fx + 0.08, y - row_h / 2, "（表示値）",
                    ha="left", va="center", fontsize=8,
                    color="#666666", style="italic", **_fpkw())
        else:
            # 入力欄（デフォルト）
            ax.add_patch(Rectangle((fx, fy), fw, fh,
                        facecolor="white", edgecolor="#888888"))
            placeholder = ui_type or "（入力）"
            ax.text(fx + 0.08, y - row_h / 2, placeholder,
                    ha="left", va="center", fontsize=7,
                    color="#AAAAAA", **_fpkw())

        y -= row_h
        if y < 0.4:
            break

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


# ── 埋め込み ───────────────────────────────────────────────────
def fill_revision(ws, data, history: list[dict]):
    vs, ve = REV_META_PROJECT_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("project_name", ""))
    vs, ve = REV_META_DATE_V
    ws.cell(row=REV_META_ROW, column=vs, value=data.get("date", ""))

    dr.fill_revision_table(ws, history, REV_COLS, REV_DATA_ROW_START)


def fill_overview(ws, data, wireframe_path=None, changed_fields: set = None):
    changed_fields = changed_fields or set()
    for key, (cs, ce) in OV_META_1_V.items():
        ws.cell(row=OV_META_ROW_1, column=cs, value=data.get(key, ""))
    for key, (cs, ce) in OV_META_2_V.items():
        ws.cell(row=OV_META_ROW_2, column=cs, value=data.get(key, ""))

    # テキスト系セクション
    for key, r in OV_SECTION_DATA_ROW.items():
        cell = ws.cell(row=r, column=2, value=data.get(key, ""))
        if key in changed_fields:
            dr.apply_red(cell, size=10)

    # 主要機能（箇条書き）
    features = data.get("features", [])
    if features:
        bullet_text = "\n".join(f"・{f}" for f in features)
        cell = ws.cell(row=OV_FEATURES_ROW, column=2, value=bullet_text)
        if "features" in changed_fields:
            dr.apply_red(cell, size=10)

    # 画面イメージ（ワイヤーフレーム）
    if wireframe_path and Path(wireframe_path).exists():
        try:
            img = XLImage(wireframe_path)
            img.anchor = f"{get_column_letter(GRID_LEFT)}{OV_IMG_DATA_START}"
            ratio = img.height / img.width if img.width else 1.2
            img.width = 620
            img.height = min(int(620 * ratio), 900)
            ws.add_image(img)
        except Exception as e:
            W(ws, OV_IMG_DATA_START, GRID_LEFT,
              f"[ワイヤーフレーム挿入失敗: {e}]",
              italic=True, fg="888888")


def fill_items(ws, data, changed_item_nos: set = None):
    changed_item_nos = changed_item_nos or set()
    items = data.get("items", [])
    r = IT_DATA_ROW_START
    for i, it in enumerate(items):
        no = it.get("no", str(i + 1))
        is_changed = no in changed_item_nos
        cells = []
        cells.append(ws.cell(row=r, column=IT_COLS["no"][0],         value=no))
        cells.append(ws.cell(row=r, column=IT_COLS["label"][0],      value=it.get("label", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["api_name"][0],   value=it.get("api_name", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["ui_type"][0],    value=it.get("ui_type", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["type"][0],       value=it.get("type", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["required"][0],
                             value="○" if it.get("required") else ""))
        cells.append(ws.cell(row=r, column=IT_COLS["default"][0],    value=it.get("default", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["validation"][0], value=it.get("validation", "")))
        cells.append(ws.cell(row=r, column=IT_COLS["note"][0],       value=it.get("note", "")))
        if is_changed:
            for c in cells:
                dr.apply_red(c)
        long_text = (it.get("validation", "") or "") + " " + (it.get("note", "") or "")
        set_h(ws, r, max(24, min(80, len(long_text) // 25 * 14 + 24)))
        r += 1


def _step_title(step, index):
    t = step.get("title")
    if t:
        return t
    target = step.get("target", "")
    api = step.get("api_call", "")
    if target and api and api != "-":
        return f"{target} → {api}"
    return target or api or f"ステップ{index + 1}"


def _step_detail_text(step):
    parts = []
    detail = step.get("detail", "") or ""
    if detail:
        parts.append(detail)
    api = step.get("api_call", "") or ""
    if api and api != "-":
        parts.append(f"【API/アクション】{api}")
    result = step.get("result", "") or ""
    if result and result != "-":
        parts.append(f"【結果】{result}")
    note = step.get("note", "") or ""
    if note and note != "-":
        parts.append(f"【備考】{note}")
    return "\n".join(parts)


def fill_logic(ws, data, tmp_dir, changed_uc_titles: set = None):
    """usecases[] を「左:表 / 右:フロー図」の UC ブロックとして描画。"""
    changed_uc_titles = changed_uc_titles or set()
    usecases = data.get("usecases", [])
    r = LG_CONTENT_START_ROW
    for uc_idx, uc in enumerate(usecases):
        title = uc.get("title", "")
        is_changed = title in changed_uc_titles

        # UC 帯（全幅）
        set_h(ws, r, 26)
        uc_cell = MW(ws, r, GRID_LEFT, GRID_RIGHT, title,
           bold=True, fg=C_FONT_W, bg=C_SUB_BAND, size=11, border=B_all())
        if is_changed:
            dr.apply_red(uc_cell, bold=True, size=11)
        r += 1

        # トリガー行（全幅）
        trigger = uc.get("trigger", "")
        if trigger:
            set_h(ws, r, 24)
            MW(ws, r, 2, 4, "トリガー",
               bold=True, bg=C_LABEL_BG, border=B_all(), h="center")
            MW(ws, r, 5, 31, trigger, border=B_all())
            r += 1

        # 左側テーブルヘッダ
        table_header_row = r
        set_h(ws, r, 26)
        MW(ws, r, *LG_LEFT_NO,     "No",
           bold=True, bg=C_HDR_BLUE, fg=C_FONT_W, h="center", border=B_all())
        MW(ws, r, *LG_LEFT_TITLE,  "ステップ",
           bold=True, bg=C_HDR_BLUE, fg=C_FONT_W, h="center", border=B_all())
        MW(ws, r, *LG_LEFT_DETAIL, "処理内容",
           bold=True, bg=C_HDR_BLUE, fg=C_FONT_W, h="center", border=B_all())
        r += 1

        steps = uc.get("steps", [])
        if not steps:
            set_h(ws, r, 26)
            MW(ws, r, LG_LEFT_NO[0], LG_LEFT_END, "（ステップ未登録）",
               fg=C_FONT_GRAY, italic=True, border=B_all(), h="center")
            r += 1
        else:
            for i, step in enumerate(steps):
                st_title = _step_title(step, i)
                detail_text = _step_detail_text(step)
                # タイトル行の高さを文字数から動的計算（LG_LEFT_TITLE=col4-7, 4列×4.2unit≈9文字/行）
                TITLE_CPL = 9
                t_lines = max(1, -(-len(st_title) // TITLE_CPL))
                set_h(ws, r, max(22, t_lines * 18 + 4))
                MW(ws, r, *LG_LEFT_NO,     step.get("no", str(i + 1)),
                   bold=True, bg=C_STEP_BG, border=B_all(), h="center")
                MW(ws, r, *LG_LEFT_TITLE,  st_title,
                   bold=True, bg=C_STEP_BG, border=B_all())
                MW(ws, r, *LG_LEFT_DETAIL, "",
                   bg=C_STEP_BG, border=B_all())
                r += 1
                if detail_text:
                    est_lines = max(2, len(detail_text) // 32
                                    + detail_text.count("\n") + 1)
                    set_h(ws, r, max(40, est_lines * 15))
                    MW(ws, r, *LG_LEFT_NO,     "", border=B_all())
                    MW(ws, r, LG_LEFT_TITLE[0], LG_LEFT_END, detail_text,
                       border=B_all(), v="top", wrap=True)
                    r += 1

        # 右側: フロー図（flow_steps 優先、なければ steps から生成）
        flow_steps = uc.get("flow_steps")
        if flow_steps is None:
            flow_steps = [
                {"no": s.get("no", str(i + 1)),
                 "title": _step_title(s, i),
                 "node_type": s.get("node_type", "process"),
                 "branch": s.get("branch"),
                 "calls": s.get("calls"),
                 "object_ref": s.get("object_ref"),
                 "main_label": s.get("main_label")}
                for i, s in enumerate(steps)
            ]

        flow_path = Path(tmp_dir) / f"flow_uc{uc_idx + 1}.png"
        ok = False
        if flow_steps:
            try:
                ok = generate_flowchart(
                    flow_steps, str(flow_path),
                    fig_w=4.6, add_start_end=True, wrap_limit=14,
                )
            except Exception:
                ok = False

        img_h = 0
        if ok and flow_path.exists():
            try:
                img = XLImage(str(flow_path))
                aspect = img.height / img.width if img.width else 1.5
                img_w = 440
                img_h = int(img_w * aspect)   # 高さキャップなし・縦横比維持
                img.width = img_w
                img.height = img_h
                # 気持ち下にオフセット（テーブルヘッダ直上にくっつかないように）
                marker = AnchorMarker(
                    col=LG_FLOW_CS - 1, colOff=0,
                    row=table_header_row - 1, rowOff=pixels_to_EMU(18))
                size = XDRPositiveSize2D(
                    cx=pixels_to_EMU(img_w), cy=pixels_to_EMU(img_h))
                img.anchor = OneCellAnchor(_from=marker, ext=size)
                ws.add_image(img)
            except Exception as e:
                W(ws, table_header_row, LG_FLOW_CS,
                  f"[フロー図挿入失敗: {e}]", italic=True, fg="888888")

        # 画像が次UCへ貫通しないよう、テーブル累積高さが画像高さ未満なら
        # 罫線なしの空行でスペースを確保する
        if img_h > 0:
            need_px = img_h + 24  # 18pxオフセット + 余裕6px
            cum_pt = 0.0
            for rr in range(table_header_row, r):
                h = ws.row_dimensions[rr].height
                cum_pt += (h if h else 15)
            cum_px = cum_pt * 4.0 / 3.0
            if cum_px < need_px:
                deficit_pt = (need_px - cum_px) * 3.0 / 4.0
                spacer_rows = int(deficit_pt // 15) + 1
                for _ in range(spacer_rows):
                    set_h(ws, r, 15)
                    r += 1

        # UC 間スペーサー
        set_h(ws, r, 12)
        r += 1


def fill_params(ws, data, changed_params_map: dict = None,
                changed_section_titles: set = None):
    """param_sections[] を順番に描画。

    changed_params_map: {section_title: set(item_key,...)} 変更のあった項目
    changed_section_titles: セクション自体が追加/変更されたタイトル集合
    """
    changed_params_map    = changed_params_map or {}
    changed_section_titles = changed_section_titles or set()
    sections = data.get("param_sections", [])
    r = PM_CONTENT_START_ROW
    for sec in sections:
        title = sec.get("title", "")
        set_h(ws, r, 26)
        sec_cell = MW(ws, r, GRID_LEFT, GRID_RIGHT, title,
           bold=True, fg=C_FONT_W, bg=C_BAND_BLUE, size=11, border=B_all())
        if title in changed_section_titles:
            dr.apply_red(sec_cell, bold=True, size=11)
        r += 1

        headers = {
            "no": "No", "key": "Key / 名称", "type": "型", "required": "必須",
            "desc": "説明", "default": "デフォルト", "note": "備考",
        }
        set_h(ws, r, 26)
        for k, label in headers.items():
            cs, ce = PM_COLS[k]
            MW(ws, r, cs, ce, label,
               bold=True, bg=C_HDR_BLUE, fg=C_FONT_W, h="center",
               border=B_all())
        r += 1

        items = sec.get("items", [])
        if not items:
            set_h(ws, r, 24)
            MW(ws, r, GRID_LEFT, GRID_RIGHT, "（なし）",
               fg=C_FONT_GRAY, italic=True, border=B_all(),
               h="center")
            r += 1
        else:
            changed_keys = changed_params_map.get(title, set())
            for i, p in enumerate(items):
                desc = p.get("description", "") or ""
                set_h(ws, r, max(24, min(80, len(desc) // 30 * 14 + 24)))
                item_key = p.get("key", "")
                is_changed = item_key in changed_keys
                vals = {
                    "no":       p.get("no", str(i + 1)),
                    "key":      item_key,
                    "type":     p.get("type", ""),
                    "required": "○" if p.get("required") else "",
                    "desc":     desc,
                    "default":  p.get("default", ""),
                    "note":     p.get("note", ""),
                }
                row_cells = []
                for k, (cs, ce) in PM_COLS.items():
                    row_cells.append(MW(ws, r, cs, ce, vals[k], border=B_all(),
                                        v="top",
                                        h="center" if k in ("no", "required") else "left"))
                if is_changed:
                    for c in row_cells:
                        dr.apply_red(c)
                r += 1

        set_h(ws, r, 12)
        r += 1


SCALAR_FIELDS   = ["purpose", "overview", "features",
                   "prerequisites", "transition"]
SECTION_SHEETS  = {"items":          "画面項目定義",
                   "usecases":       "処理詳細",
                   "param_sections": "パラメーター定義",
                   "param_items":    "パラメーター定義"}


def _flatten_param_items(sections: list) -> list[dict]:
    """param_sections[].items[] を 複合キー "section::key" でフラット化。"""
    out = []
    for sec in sections or []:
        stitle = sec.get("title", "")
        for it in (sec.get("items") or []):
            out.append({
                "_key": f"{stitle}::{it.get('key', '')}",
                "_section": stitle,
                "_item_key": it.get("key", ""),
                **{k: v for k, v in it.items() if k not in ("_key", "_section", "_item_key")},
            })
    return out


def _compute_diffs(prev_data: dict | None, new_data: dict) -> dict:
    if prev_data is None:
        return {"scalars": [], "lists": {}}
    return {
        "scalars": dr.diff_scalars(prev_data, new_data, SCALAR_FIELDS),
        "lists": {
            "items":    dr.diff_list(prev_data.get("items", []),
                                     new_data.get("items", []), "no"),
            "usecases": dr.diff_list(prev_data.get("usecases", []),
                                     new_data.get("usecases", []), "title"),
            "param_sections": dr.diff_list(prev_data.get("param_sections", []),
                                           new_data.get("param_sections", []), "title"),
            "param_items":    dr.diff_list(
                _flatten_param_items(prev_data.get("param_sections", [])),
                _flatten_param_items(new_data.get("param_sections", [])),
                "_key"),
        },
    }


def _build_changed_params_map(diffs: dict) -> dict[str, set]:
    """変更のあった param_items の "section::key" を section→{key,...} に変換。"""
    changed = dr.changed_ids(diffs, "param_items")
    out: dict[str, set] = {}
    for ck in changed:
        if "::" in ck:
            sec, ikey = ck.split("::", 1)
            out.setdefault(sec, set()).add(ikey)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      required=True)
    parser.add_argument("--template",   required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-file", default="",
                        help="更新時: 既存の画面設計書xlsxパス")
    parser.add_argument("--version-increment", default="minor",
                        choices=["minor", "major"])
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    today  = _date.today().strftime("%Y-%m-%d")
    author = data.get("author", "")

    # ── 出力先を先に確定（既存ファイル自動検出に使用） ──────────────
    feat_id   = data.get("id", "F-000")
    name      = data.get("name", "画面")
    type_key  = data.get("type", "その他")
    subfolder = TYPE_FOLDER.get(type_key, "other")
    out_dir   = Path(args.output_dir) / subfolder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path  = out_dir / f"【{feat_id}】{name}.xlsx"

    # ── バージョン判定 ────────────────────────────────────────
    is_major    = (args.version_increment == "major")
    source_file = args.source_file.strip()

    # --source-file 未指定時: 同一IDの既存ファイルを自動検出
    if not source_file:
        existing = [f for f in out_dir.glob(f"【{feat_id}】*.xlsx")]
        if existing:
            source_file = str(existing[0])
            print(f"  [AUTO] 既存ファイルを検出: {existing[0].name}")

    prev_meta   = read_meta(source_file) if source_file else None
    prev_data   = prev_meta.get("data") if prev_meta else None

    if prev_meta:
        current_version = increment_version(
            prev_meta.get("version", "1.0"), args.version_increment)
        history    = prev_meta.get("history", [])
        is_initial = False
        print(f"更新モード: {prev_meta.get('version', '?')} → {current_version}"
              + (" (メジャー)" if is_major else ""))
    else:
        current_version = data.get("version") or "1.0"
        history    = []
        is_initial = True
        print(f"新規作成モード: v{current_version}")

    data["version"] = current_version

    diffs = _compute_diffs(prev_data, data)
    if prev_meta and not is_major and not dr.has_any_diff(diffs):
        print("差分なし: 既存ファイルと一致しているため更新をスキップしました")
        sys.exit(0)

    last_no = max((h["項番"] for h in history
                   if isinstance(h.get("項番"), int)), default=0)
    new_entries = dr.build_entries(
        current_version, diffs, author, today,
        start_no=last_no + 1, is_major=is_major, is_initial=is_initial,
        section_sheet_map=SECTION_SHEETS, scalar_sheet="画面概要",
    )
    history = history + new_entries

    # 変更識別子を抽出（赤字用）
    changed_scalars  = dr.changed_scalar_fields(diffs)
    changed_items    = dr.changed_ids(diffs, "items")
    changed_ucs      = dr.changed_ids(diffs, "usecases")
    changed_sections = dr.changed_ids(diffs, "param_sections")
    changed_params   = _build_changed_params_map(diffs)

    with tempfile.TemporaryDirectory(prefix="screen_design_") as tmp_dir:
        wf_path = str(Path(tmp_dir) / "wireframe.png")
        if not generate_wireframe(data.get("name", ""),
                                  data.get("items", []), wf_path):
            wf_path = None

        wb = load_workbook(args.template)
        fill_revision(wb["改版履歴"],         data, history)
        fill_overview(wb["画面概要"],         data, wireframe_path=wf_path,
                      changed_fields=set() if is_major else changed_scalars)
        fill_items   (wb["画面項目定義"],     data,
                      changed_item_nos=set() if is_major else changed_items)
        fill_logic   (wb["処理詳細"],         data, tmp_dir,
                      changed_uc_titles=set() if is_major else changed_ucs)
        fill_params  (wb["パラメーター定義"], data,
                      changed_params_map=({} if is_major else changed_params),
                      changed_section_titles=(set() if is_major else changed_sections))

        # _meta 保存（次回差分判定用）
        write_meta(wb, {
            "version": current_version,
            "date":    today,
            "author":  author,
            "data":    data,
            "history": history,
        })

        wb.save(out_path)
        print(f"画面設計書生成完了: v{current_version} → {out_path}")

        # 同一IDで別名の旧ファイルを削除（名称変更時の二重ファイル防止）
        for old_f in out_dir.glob(f"【{feat_id}】*.xlsx"):
            if old_f.resolve() != out_path.resolve():
                old_f.unlink()
                print(f"  [CLEANUP] 旧ファイルを削除: {old_f.name}")


if __name__ == "__main__":
    main()
