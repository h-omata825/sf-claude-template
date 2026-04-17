# scripts/python/sf-doc-mcp/generate_screen_mock.py
# -*- coding: utf-8 -*-
"""
LWC / Visualforce / Aura コンポーネントのソースコードを静的解析し、
Pillow でワイヤーフレーム PNG を生成する。

Usage:
  python generate_screen_mock.py --source path/to/component.html --output mock.png [--width 860]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag

from PIL import Image, ImageDraw, ImageFont

# ── SLDS 準拠カラー定数 (RGB タプル) ──────────────────────────────────
BG_PAGE       = (243, 242, 242)
BG_CARD       = (255, 255, 255)
BG_HDR_DARK   = (3, 45, 96)
BG_HDR_MID    = (0, 112, 210)
BG_SEC_HDR    = (232, 239, 249)
FG_DARK       = (62, 62, 60)
FG_WHITE      = (255, 255, 255)
FG_PLACEHOLDER = (160, 158, 157)
BORDER_COLOR  = (221, 219, 218)
BTN_BRAND     = (0, 112, 210)
BTN_DEST      = (194, 57, 52)
REQUIRED_RED  = (194, 57, 52)

# ── レイアウト定数 ────────────────────────────────────────────────────
CANVAS_WIDTH = 860
H_PAD  = 20   # カード内側 左右パディング
V_PAD  = 14   # 要素間の縦マージン
LABEL_H = 16

# 型エイリアス
Element = dict[str, Any]


# ── フォント ─────────────────────────────────────────────────────────
def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", size)
    except Exception:
        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw | None, text: str, font) -> float:
    """テキストの描画幅を返す（互換性対応）"""
    if draw is not None:
        try:
            return draw.textlength(text, font=font)
        except AttributeError:
            pass
    try:
        return font.getlength(text)
    except AttributeError:
        size = getattr(font, "size", 12)
        return len(text) * size * 0.6


# ══════════════════════════════════════════════════════════════════════
#  パーサー
# ══════════════════════════════════════════════════════════════════════

def _is_required(tag: Tag) -> bool:
    if not tag.has_attr("required"):
        return False
    val = tag.get("required")
    # html.parser はブール属性を "" で返す。"" は required=True を意味する
    return str(val).lower() not in ("false", "[false]")


def _label_from(tag: Tag) -> str:
    for attr in ("label", "field-name", "value", "name", "id", "title"):
        v = tag.get(attr, "")
        if v and not v.startswith("["):
            return v
    return tag.name


def _variant(tag: Tag) -> str:
    v = tag.get("variant", "neutral")
    if isinstance(v, str) and v.startswith("["):
        return "neutral"
    return v if v in ("brand", "neutral", "destructive") else "neutral"


# ── LWC パーサー ─────────────────────────────────────────────────────
def _parse_lwc(html: str) -> list[Element]:
    # 前処理: ={expr} → ="[expr]"
    html = re.sub(r'=\{([^}]+)\}', r'="[\1]"', html)
    soup = BeautifulSoup(html, "html.parser")
    return _walk_lwc(soup)


def _walk_lwc(node) -> list[Element]:
    elements: list[Element] = []
    children = node.children if hasattr(node, "children") else []
    for child in children:
        if not isinstance(child, Tag):
            continue
        name = child.name.lower() if child.name else ""
        el = _map_lwc_tag(child, name)
        if el is not None:
            if isinstance(el, list):
                elements.extend(el)
            else:
                elements.append(el)
    return elements


def _map_lwc_tag(tag: Tag, name: str) -> Element | list[Element] | None:
    # lightning-input
    if name == "lightning-input":
        t = tag.get("type", "text")
        if isinstance(t, str) and t.startswith("["):
            t = "text"
        t = t.lower()
        if t in ("checkbox", "toggle"):
            return {"type": "checkbox", "label": _label_from(tag)}
        if t in ("date", "datetime", "datetime-local"):
            return {"type": "date", "label": _label_from(tag), "required": _is_required(tag)}
        if t == "search":
            return {"type": "input", "label": _label_from(tag), "required": _is_required(tag), "ui_type": "search"}
        ui = "number" if t == "number" else "text"
        return {"type": "input", "label": _label_from(tag), "required": _is_required(tag), "ui_type": ui}

    if name == "lightning-textarea":
        return {"type": "textarea", "label": _label_from(tag), "required": _is_required(tag)}

    if name in ("lightning-combobox", "lightning-select"):
        return {"type": "select", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "lightning-lookup":
        return {"type": "lookup", "label": _label_from(tag), "required": _is_required(tag)}

    if name in ("lightning-datepicker", "lightning-datetimepicker"):
        return {"type": "date", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "lightning-button" or name == "lightning-button-icon":
        return {"type": "button", "label": _label_from(tag), "variant": _variant(tag)}

    if name == "lightning-button-group":
        kids = _walk_lwc(tag)
        return {"type": "button-group", "children": kids}

    if name == "lightning-layout":
        cols: list[list[Element]] = []
        for item in tag.find_all("lightning-layout-item", recursive=False):
            cols.append(_walk_lwc(item))
        if cols:
            return {"type": "grid", "cols": cols}
        return _walk_lwc(tag)

    if name == "lightning-card":
        title = tag.get("title") or tag.get("header") or "Card"
        if isinstance(title, str) and title.startswith("["):
            title = "Card"
        kids = _walk_lwc(tag)
        return {"type": "card", "title": title, "children": kids}

    if name in ("lightning-record-edit-form", "lightning-record-form", "lightning-record-view-form"):
        kids = _walk_lwc(tag)
        title = tag.get("object-api-name", "") or tag.get("record-id", "") or "RecordForm"
        if isinstance(title, str) and title.startswith("["):
            title = "RecordForm"
        return {"type": "section", "title": title, "children": kids}

    if name == "lightning-input-field":
        return {"type": "input", "label": tag.get("field-name", "Field"), "required": _is_required(tag), "ui_type": "text"}

    if name == "lightning-output-field":
        return {"type": "input", "label": tag.get("field-name", "Field"), "required": False, "ui_type": "text"}

    if name == "lightning-datatable":
        lbl = tag.get("key-field", "") or tag.get("data", "") or "DataTable"
        if isinstance(lbl, str) and lbl.startswith("["):
            lbl = "DataTable"
        return {"type": "table", "label": lbl}

    if name == "lightning-tabset":
        tabs = []
        for tab_tag in tag.find_all("lightning-tab", recursive=False):
            tab_label = tab_tag.get("label", "Tab")
            if isinstance(tab_label, str) and tab_label.startswith("["):
                tab_label = "Tab"
            tabs.append({"label": tab_label, "children": _walk_lwc(tab_tag)})
        return {"type": "tabset", "tabs": tabs}

    if name == "lightning-accordion":
        return _walk_lwc(tag)

    if name == "lightning-dual-listbox":
        return {"type": "dual-listbox", "label": _label_from(tag), "required": _is_required(tag)}

    if name.startswith("c-"):
        lbl = name.replace("c-", "").replace("-", " ").title()
        return {"type": "custom", "label": lbl}

    if name in ("template", "div", "section", "article", "span", "form",
                "lightning-layout-item", "slot", "header", "footer", "main"):
        return _walk_lwc(tag)

    # 未知のlightningタグ — 子を展開
    if name.startswith("lightning-"):
        return _walk_lwc(tag)

    # その他 — 子を展開
    return _walk_lwc(tag)


# ── VF パーサー ──────────────────────────────────────────────────────
def _parse_vf(html: str) -> list[Element]:
    soup = BeautifulSoup(html, "html.parser")
    return _walk_vf(soup)


def _walk_vf(node) -> list[Element]:
    elements: list[Element] = []
    children = node.children if hasattr(node, "children") else []
    for child in children:
        if not isinstance(child, Tag):
            continue
        name = child.name.lower() if child.name else ""
        el = _map_vf_tag(child, name)
        if el is not None:
            if isinstance(el, list):
                elements.extend(el)
            else:
                elements.append(el)
    return elements


def _map_vf_tag(tag: Tag, name: str) -> Element | list[Element] | None:
    if name == "apex:pageblock":
        title = tag.get("title", "PageBlock")
        kids = _walk_vf(tag)
        return {"type": "card", "title": title, "children": kids}

    if name == "apex:pageblocksection":
        title = tag.get("title", "Section")
        return {"type": "section-header", "label": title}

    if name in ("apex:inputfield", "apex:inputtext"):
        return {"type": "input", "label": _label_from(tag), "required": _is_required(tag), "ui_type": "text"}

    if name == "apex:inputtextarea":
        return {"type": "textarea", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "apex:selectlist":
        return {"type": "select", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "apex:inputcheckbox":
        return {"type": "checkbox", "label": _label_from(tag)}

    if name == "apex:commandbutton":
        lbl = tag.get("value", "Button")
        v = "brand" if lbl in ("保存", "Save") else "neutral"
        return {"type": "button", "label": lbl, "variant": v}

    if name == "apex:commandlink":
        lbl = tag.get("value") or tag.get("id") or "Link"
        return {"type": "button", "label": lbl, "variant": "neutral"}

    # 再帰
    return _walk_vf(tag)


# ── Aura パーサー ────────────────────────────────────────────────────
def _parse_aura(html: str) -> list[Element]:
    html = re.sub(r'=\{([^}]+)\}', r'="[\1]"', html)
    soup = BeautifulSoup(html, "html.parser")
    return _walk_aura(soup)


def _walk_aura(node) -> list[Element]:
    elements: list[Element] = []
    children = node.children if hasattr(node, "children") else []
    for child in children:
        if not isinstance(child, Tag):
            continue
        name = child.name.lower() if child.name else ""
        el = _map_aura_tag(child, name)
        if el is not None:
            if isinstance(el, list):
                elements.extend(el)
            else:
                elements.append(el)
    return elements


def _map_aura_tag(tag: Tag, name: str) -> Element | list[Element] | None:
    if name == "aura:component":
        return _walk_aura(tag)

    if name == "lightning:input":
        return {"type": "input", "label": _label_from(tag), "required": _is_required(tag), "ui_type": "text"}

    if name == "lightning:combobox":
        return {"type": "select", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "lightning:button":
        return {"type": "button", "label": _label_from(tag), "variant": _variant(tag)}

    if name == "ui:inputtext":
        return {"type": "input", "label": _label_from(tag), "required": _is_required(tag), "ui_type": "text"}

    if name == "ui:inputselect":
        return {"type": "select", "label": _label_from(tag), "required": _is_required(tag)}

    if name == "ui:button":
        return {"type": "button", "label": _label_from(tag), "variant": _variant(tag)}

    return _walk_aura(tag)


# ══════════════════════════════════════════════════════════════════════
#  Renderer
# ══════════════════════════════════════════════════════════════════════

class Renderer:
    def __init__(self, elements: list[Element], screen_name: str = ""):
        self.elements = elements
        self.screen_name = screen_name
        self.draw: ImageDraw.ImageDraw | None = None
        self._y = 0
        self._left = H_PAD
        self._right = CANVAS_WIDTH - H_PAD
        self.font_l = _load_font(14)
        self.font_m = _load_font(12)
        self.font_s = _load_font(11)
        self.font_xs = _load_font(10)

    # ── 公開API ──────────────────────────────────────────────────
    def measure(self) -> int:
        self.draw = None
        self._y = 0
        self._left = H_PAD
        self._right = CANVAS_WIDTH - H_PAD
        self._render_all()
        return self._y + 16

    def render(self) -> Image.Image:
        h = self.measure()
        img = Image.new("RGB", (CANVAS_WIDTH, max(h, 200)), BG_PAGE)
        self.draw = ImageDraw.Draw(img)
        self._y = 0
        self._left = H_PAD
        self._right = CANVAS_WIDTH - H_PAD
        self._render_all()
        return img

    # ── 内部描画 ─────────────────────────────────────────────────
    def _render_all(self):
        self._draw_page_header()
        for el in self.elements:
            self._render_element(el, self._left, self._right)

    def _render_element(self, el: Element, left: int, right: int):
        t = el.get("type", "")
        if t == "card":
            self._draw_card(el, left, right)
        elif t == "section":
            self._draw_section(el, left, right)
        elif t == "section-header":
            self._draw_section_header(el, left, right)
        elif t == "grid":
            self._draw_grid(el, left, right)
        elif t == "input":
            self._draw_input(el, left, right)
        elif t == "textarea":
            self._draw_textarea(el, left, right)
        elif t == "select":
            self._draw_select(el, left, right)
        elif t == "lookup":
            self._draw_lookup(el, left, right)
        elif t == "date":
            self._draw_date(el, left, right)
        elif t == "checkbox":
            self._draw_checkbox(el, left, right)
        elif t == "button":
            self._draw_button(el, left, right)
        elif t == "button-group":
            self._draw_button_group(el, left, right)
        elif t == "dual-listbox":
            self._draw_dual_listbox(el, left, right)
        elif t == "table":
            self._draw_table(el, left, right)
        elif t == "custom":
            self._draw_custom(el, left, right)
        elif t == "tabset":
            self._draw_tabset(el, left, right)

    # ── ページヘッダー ───────────────────────────────────────────
    def _draw_page_header(self):
        h = 44
        if self.draw:
            self.draw.rectangle([0, self._y, CANVAS_WIDTH, self._y + h], fill=BG_HDR_DARK)
            text = self.screen_name or "Screen"
            self.draw.text((H_PAD, self._y + 12), text, fill=FG_WHITE, font=self.font_l)
        self._y += h + V_PAD

    # ── カード ───────────────────────────────────────────────────
    def _draw_card(self, el: Element, left: int, right: int):
        # ヘッダー
        hdr_h = 36
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + hdr_h], fill=BG_HDR_MID)
            self.draw.text((left + 10, self._y + 8), el.get("title", "Card"), fill=FG_WHITE, font=self.font_m)
        self._y += hdr_h

        body_start = self._y
        inner_left = left + H_PAD
        inner_right = right - H_PAD

        # ドライランで子要素の高さを計測 → 白背景を先に描いてから子要素を重ねる
        saved_draw = self.draw
        saved_y = self._y
        self.draw = None
        self._y += 8
        for child in el.get("children", []):
            self._render_element(child, inner_left, inner_right)
        self._y += 8
        body_end = self._y

        self.draw = saved_draw
        self._y = body_start

        if self.draw:
            self.draw.rectangle([left, body_start, right, body_end], fill=BG_CARD, outline=BORDER_COLOR)

        self._y += 8
        for child in el.get("children", []):
            self._render_element(child, inner_left, inner_right)
        self._y += 8
        self._y += V_PAD

    def _draw_section(self, el: Element, left: int, right: int):
        title = el.get("title", "")
        if title:
            if self.draw:
                self.draw.text((left, self._y), title, fill=FG_DARK, font=self.font_s)
            self._y += LABEL_H + 4
        for child in el.get("children", []):
            self._render_element(child, left, right)

    def _draw_section_header(self, el: Element, left: int, right: int):
        h = 28
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h], fill=BG_SEC_HDR)
            self.draw.text((left + 8, self._y + 5), el.get("label", ""), fill=FG_DARK, font=self.font_s)
        self._y += h + V_PAD

    # ── グリッド ─────────────────────────────────────────────────
    def _draw_grid(self, el: Element, left: int, right: int):
        cols = el.get("cols", [])
        if not cols:
            return
        n = len(cols)
        gap = 10
        col_w = (right - left - gap * (n - 1)) // n
        saved_y = self._y
        max_y = self._y
        for i, col_elements in enumerate(cols):
            self._y = saved_y
            cl = left + i * (col_w + gap)
            cr = cl + col_w
            for child in col_elements:
                self._render_element(child, cl, cr)
            if self._y > max_y:
                max_y = self._y
        self._y = max_y

    # ── 入力フィールド ───────────────────────────────────────────
    def _draw_label(self, label: str, required: bool, left: int):
        if self.draw:
            self.draw.text((left, self._y), label, fill=FG_DARK, font=self.font_s)
            if required:
                tw = _text_width(self.draw, label, self.font_s)
                self.draw.text((left + tw + 2, self._y), "*", fill=REQUIRED_RED, font=self.font_s)
        self._y += LABEL_H

    def _draw_input(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 28
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h], fill=BG_CARD, outline=BORDER_COLOR)
        self._y += h + V_PAD

    def _draw_textarea(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 64
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h], fill=BG_CARD, outline=BORDER_COLOR)
        self._y += h + V_PAD

    def _draw_select(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 28
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h], fill=BG_CARD, outline=BORDER_COLOR)
            # ▼ indicator
            self.draw.text((right - 20, self._y + 5), "▼", fill=FG_PLACEHOLDER, font=self.font_xs)
        self._y += h + V_PAD

    def _draw_lookup(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 28
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h], fill=BG_CARD, outline=BORDER_COLOR)
            self.draw.text((right - 22, self._y + 4), "🔍", fill=FG_PLACEHOLDER, font=self.font_xs)
        self._y += h + V_PAD

    def _draw_date(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 28
        w = min(200, right - left)
        if self.draw:
            self.draw.rectangle([left, self._y, left + w, self._y + h], fill=BG_CARD, outline=BORDER_COLOR)
            self.draw.text((left + w - 22, self._y + 4), "📅", fill=FG_PLACEHOLDER, font=self.font_xs)
        self._y += h + V_PAD

    def _draw_checkbox(self, el: Element, left: int, right: int):
        h = 22
        box_sz = 14
        if self.draw:
            bx = left
            by = self._y + (h - box_sz) // 2
            self.draw.rectangle([bx, by, bx + box_sz, by + box_sz], fill=BG_CARD, outline=BORDER_COLOR)
            self.draw.text((left + box_sz + 6, self._y + 2), el.get("label", ""), fill=FG_DARK, font=self.font_s)
        self._y += h + V_PAD

    # ── ボタン ───────────────────────────────────────────────────
    def _draw_button(self, el: Element, left: int, right: int,
                     x_offset: int | None = None) -> int:
        """ボタンを描画して幅を返す"""
        h = 30
        label = el.get("label", "Button")
        variant = el.get("variant", "neutral")
        tw = _text_width(self.draw, label, self.font_s) + 24
        btn_w = max(int(tw), 70)
        bx = x_offset if x_offset is not None else left

        if self.draw:
            if variant == "brand":
                bg, fg = BTN_BRAND, FG_WHITE
            elif variant == "destructive":
                bg, fg = BTN_DEST, FG_WHITE
            else:
                bg, fg = BG_CARD, BTN_BRAND

            try:
                self.draw.rounded_rectangle([bx, self._y, bx + btn_w, self._y + h],
                                            radius=4, fill=bg, outline=BTN_BRAND)
            except AttributeError:
                self.draw.rectangle([bx, self._y, bx + btn_w, self._y + h],
                                    fill=bg, outline=BTN_BRAND)
            self.draw.text((bx + 12, self._y + 6), label, fill=fg, font=self.font_s)

        if x_offset is None:
            self._y += h + V_PAD
        return btn_w

    def _draw_button_group(self, el: Element, left: int, right: int):
        x = left
        h = 30
        for child in el.get("children", []):
            if child.get("type") == "button":
                w = self._draw_button(child, left, right, x_offset=x)
                x += w + 8
        self._y += h + V_PAD

    # ── デュアルリストボックス ───────────────────────────────────
    def _draw_dual_listbox(self, el: Element, left: int, right: int):
        self._draw_label(el.get("label", ""), el.get("required", False), left)
        h = 80
        mid = (left + right) // 2
        box_w = (right - left - 40) // 2
        if self.draw:
            # 左ボックス
            self.draw.rectangle([left, self._y, left + box_w, self._y + h],
                                fill=BG_CARD, outline=BORDER_COLOR)
            # 矢印
            self.draw.text((mid - 8, self._y + h // 2 - 8), "→", fill=FG_DARK, font=self.font_m)
            # 右ボックス
            self.draw.rectangle([right - box_w, self._y, right, self._y + h],
                                fill=BG_CARD, outline=BORDER_COLOR)
        self._y += h + V_PAD

    # ── テーブル ─────────────────────────────────────────────────
    def _draw_table(self, el: Element, left: int, right: int):
        h = 60
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h],
                                fill=(245, 245, 245), outline=BORDER_COLOR)
            lbl = f"[{el.get('label', 'Table')}]"
            self.draw.text((left + 10, self._y + 20), lbl, fill=FG_PLACEHOLDER, font=self.font_s)
        self._y += h + V_PAD

    # ── カスタムコンポーネント ───────────────────────────────────
    def _draw_custom(self, el: Element, left: int, right: int):
        h = 36
        if self.draw:
            self.draw.rectangle([left, self._y, right, self._y + h],
                                fill=(245, 245, 245), outline=BORDER_COLOR)
            lbl = f"<{el.get('label', 'Custom')}>"
            self.draw.text((left + 10, self._y + 8), lbl, fill=FG_PLACEHOLDER, font=self.font_s)
        self._y += h + V_PAD

    # ── タブセット ───────────────────────────────────────────────
    def _draw_tabset(self, el: Element, left: int, right: int):
        tabs = el.get("tabs", [])
        if not tabs:
            return
        tab_h = 32
        # タブバー
        x = left
        for i, tab in enumerate(tabs):
            label = tab.get("label", f"Tab {i+1}")
            tw = _text_width(self.draw, label, self.font_s) + 24
            tab_w = max(int(tw), 80)
            if self.draw:
                bg = BG_CARD if i == 0 else (230, 230, 230)
                self.draw.rectangle([x, self._y, x + tab_w, self._y + tab_h],
                                    fill=bg, outline=BORDER_COLOR)
                self.draw.text((x + 12, self._y + 7), label, fill=FG_DARK, font=self.font_s)
            x += tab_w
        self._y += tab_h + 4

        # 最初のタブの中身だけ描画
        if tabs[0].get("children"):
            for child in tabs[0]["children"]:
                self._render_element(child, left, right)
        self._y += V_PAD


# ══════════════════════════════════════════════════════════════════════
#  ファイル検索
# ══════════════════════════════════════════════════════════════════════

def find_source_file(project_dir: Path, api_name: str) -> Path | None:
    """
    LWC → lwc/{name}/{name}.html
    VF  → pages/{name}.page
    Aura → aura/{name}/{name}.cmp
    の順で探して最初に見つかったものを返す。
    """
    # LWC (camelCase → kebab-case 変換も試す)
    names_to_try = [api_name]
    kebab = re.sub(r'([a-z])([A-Z])', r'\1-\2', api_name).lower()
    if kebab != api_name.lower():
        names_to_try.append(kebab)

    for name in names_to_try:
        # LWC
        for lwc_dir in project_dir.rglob("lwc"):
            p = lwc_dir / name / f"{name}.html"
            if p.exists():
                return p
        # Aura
        for aura_dir in project_dir.rglob("aura"):
            p = aura_dir / name / f"{name}.cmp"
            if p.exists():
                return p

    # VF pages
    for pages_dir in project_dir.rglob("pages"):
        p = pages_dir / f"{api_name}.page"
        if p.exists():
            return p

    return None


# ══════════════════════════════════════════════════════════════════════
#  種別判定・生成
# ══════════════════════════════════════════════════════════════════════

def _detect_type(source_path: Path) -> str:
    """ファイル拡張子からコンポーネント種別を返す"""
    suffix = source_path.suffix.lower()
    if suffix == ".html":
        return "lwc"
    elif suffix == ".page":
        return "vf"
    elif suffix == ".cmp":
        return "aura"
    return "unknown"


def generate(source_path: Path, output_path: Path, width: int = 860) -> bool:
    """
    source_path の種別（LWC/VF/Aura）を自動判定してモックアップを生成。
    成功時 True、スキップ・失敗時 False を返す。
    output_path に PNG を保存する。
    """
    global CANVAS_WIDTH
    CANVAS_WIDTH = width

    if not source_path.exists():
        print(f"[SKIP] ファイルが見つかりません: {source_path}", file=sys.stderr)
        return False

    try:
        html = source_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"[ERROR] ファイル読み込み失敗: {e}", file=sys.stderr)
        return False

    if not html.strip():
        print(f"[SKIP] 空ファイル: {source_path}", file=sys.stderr)
        return False

    comp_type = _detect_type(source_path)

    if comp_type == "lwc":
        elements = _parse_lwc(html)
    elif comp_type == "vf":
        elements = _parse_vf(html)
    elif comp_type == "aura":
        elements = _parse_aura(html)
    else:
        print(f"[SKIP] 未対応の種別: {source_path.suffix}", file=sys.stderr)
        return False

    if not elements:
        print(f"[SKIP] UI要素が検出されませんでした: {source_path}", file=sys.stderr)
        return False

    screen_name = source_path.stem
    renderer = Renderer(elements, screen_name=screen_name)
    img = renderer.render()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    print(f"[OK] モックアップ生成: {output_path}")
    return True


# ══════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LWC/VF/Aura ワイヤーフレーム生成")
    parser.add_argument("--source", required=True, help="ソースファイルパス (.html/.page/.cmp)")
    parser.add_argument("--output", required=True, help="出力PNGパス")
    parser.add_argument("--width", type=int, default=860, help="キャンバス幅 (default: 860)")
    args = parser.parse_args()

    ok = generate(Path(args.source), Path(args.output), width=args.width)
    sys.exit(0 if ok else 1)
