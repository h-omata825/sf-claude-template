# -*- coding: utf-8 -*-
"""システム概要書を docs/ の Markdown から PDF 生成する CLI エントリーポイント"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from fpdf import FPDF

# ── 定数 ──
FONT_DIR = Path(__file__).parent / "fonts"
PAGE_W = 210  # A4 mm
PAGE_H = 297
MARGIN = 15
CONTENT_W = PAGE_W - MARGIN * 2


# ── ユーティリティ ──
def _read_if_exists(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _parse_md_table(text: str) -> list[list[str]]:
    """Markdown テーブルを 2D リストに変換"""
    rows = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        # セパレータ行を除外
        if all(re.match(r"^[-:]+$", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _extract_sections(md: str) -> list[tuple[int, str, str]]:
    """Markdown を (level, title, body) のリストに分割"""
    sections = []
    current_level = 0
    current_title = ""
    current_body = []

    for line in md.splitlines():
        m = re.match(r"^(#{1,4})\s+(.+)", line)
        if m:
            if current_title:
                sections.append((current_level, current_title, "\n".join(current_body).strip()))
            current_level = len(m.group(1))
            current_title = m.group(2)
            current_body = []
        else:
            current_body.append(line)

    if current_title:
        sections.append((current_level, current_title, "\n".join(current_body).strip()))

    return sections


# ── PDF 生成クラス ──
class OverviewPDF(FPDF):
    """システム概要書 PDF"""

    def __init__(self, system_name: str = "", company_name: str = ""):
        super().__init__()
        self._system_name = system_name
        self._company_name = company_name
        self._setup_fonts()

    def _setup_fonts(self):
        """日本語フォント設定（Windows 標準フォントを使用）"""
        # Windows のフォントパスを探す
        win_font = Path("C:/Windows/Fonts")
        # BIZ UDP ゴシック / 游ゴシック / MS ゴシック の順に探す
        font_candidates = [
            ("BIZUDPGothic", "BIZUDPGothic-Regular.ttf", "BIZUDPGothic-Bold.ttf"),
            ("YuGothic", "YuGothM.ttc", "YuGothB.ttc"),
            ("MSGothic", "msgothic.ttc", "msgothic.ttc"),
        ]
        self._font_name = "Helvetica"  # fallback
        for name, regular, bold in font_candidates:
            regular_path = win_font / regular
            bold_path = win_font / bold
            if regular_path.exists():
                try:
                    self.add_font(name, "", str(regular_path), )
                    self.add_font(name, "B", str(bold_path), )
                    self._font_name = name
                    break
                except Exception:
                    continue

    def header(self):
        """ヘッダー（表紙以外）"""
        if self.page_no() <= 1:
            return
        self.set_font(self._font_name, "", 7)
        self.set_text_color(128, 128, 128)
        title = f"{self._system_name} — システム概要書" if self._system_name else "システム概要書"
        self.cell(0, 5, title, align="L")
        self.ln(8)

    def footer(self):
        """フッター"""
        self.set_y(-15)
        self.set_font(self._font_name, "", 7)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f"— {self.page_no()} —", align="C")

    def add_cover(self, author: str, version: str):
        """表紙"""
        self.add_page()
        self.ln(60)

        # タイトル
        self.set_font(self._font_name, "B", 28)
        self.set_text_color(30, 30, 30)
        self.cell(0, 15, "システム概要書", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

        if self._system_name:
            self.set_font(self._font_name, "", 16)
            self.set_text_color(80, 80, 80)
            self.cell(0, 10, self._system_name, align="C", new_x="LMARGIN", new_y="NEXT")
            self.ln(10)

        # メタ情報
        self.ln(30)
        self.set_font(self._font_name, "", 11)
        self.set_text_color(60, 60, 60)
        meta = [
            ("バージョン", version),
            ("作成日", str(date.today())),
            ("作成者", author),
        ]
        if self._company_name:
            meta.insert(0, ("会社名", self._company_name))

        for label, value in meta:
            self.cell(CONTENT_W / 2, 8, label, align="R")
            self.set_font(self._font_name, "B", 11)
            self.cell(CONTENT_W / 2, 8, f"  {value}", align="L", new_x="LMARGIN", new_y="NEXT")
            self.set_font(self._font_name, "", 11)

    def add_heading(self, level: int, text: str):
        """見出し"""
        sizes = {1: 18, 2: 14, 3: 11, 4: 10}
        size = sizes.get(level, 10)
        self.ln(4 if level >= 3 else 8)
        self.set_font(self._font_name, "B", size)
        self.set_text_color(30, 30, 30)

        if level <= 2:
            # 下線付き
            self.cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")
            y = self.get_y()
            self.set_draw_color(180, 180, 180)
            self.line(MARGIN, y, PAGE_W - MARGIN, y)
            self.ln(3)
        else:
            self.cell(0, size * 0.5, text, new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

    def add_paragraph(self, text: str):
        """本文段落"""
        self.set_font(self._font_name, "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(CONTENT_W, 5, text)
        self.ln(2)

    def add_bullet(self, text: str):
        """箇条書き"""
        self.set_font(self._font_name, "", 9)
        self.set_text_color(40, 40, 40)
        self.cell(5, 5, "・")
        self.multi_cell(CONTENT_W - 5, 5, text)

    def add_table(self, rows: list[list[str]]):
        """テーブル描画"""
        if not rows:
            return

        n_cols = len(rows[0])
        # 列幅を内容の長さに基づいて計算
        col_widths = self._calc_col_widths(rows, n_cols)

        self.set_font(self._font_name, "", 8)

        for i, row in enumerate(rows):
            is_header = (i == 0)
            if is_header:
                self.set_font(self._font_name, "B", 8)
                self.set_fill_color(60, 60, 80)
                self.set_text_color(255, 255, 255)
            else:
                self.set_font(self._font_name, "", 8)
                if i % 2 == 0:
                    self.set_fill_color(245, 245, 250)
                else:
                    self.set_fill_color(255, 255, 255)
                self.set_text_color(40, 40, 40)

            # ページまたぎチェック
            if self.get_y() + 7 > PAGE_H - 20:
                self.add_page()

            for j, cell in enumerate(row):
                w = col_widths[j] if j < len(col_widths) else 30
                self.cell(w, 6, cell[:50], border=1, fill=True)
            self.ln()

        self.ln(3)

    def _calc_col_widths(self, rows: list[list[str]], n_cols: int) -> list[float]:
        """列幅を内容に基づいて計算"""
        max_lens = [0] * n_cols
        for row in rows:
            for j, cell in enumerate(row):
                if j < n_cols:
                    # 日本語は2文字分
                    length = sum(2 if ord(c) > 127 else 1 for c in cell)
                    max_lens[j] = max(max_lens[j], length)

        total = sum(max_lens) or 1
        return [max(CONTENT_W * (ml / total), 15) for ml in max_lens]

    def add_md_section(self, body: str):
        """Markdown 本文をパース・描画"""
        in_table = False
        table_lines = []

        for line in body.splitlines():
            stripped = line.strip()

            # 空行
            if not stripped:
                if in_table:
                    self.add_table(_parse_md_table("\n".join(table_lines)))
                    table_lines = []
                    in_table = False
                continue

            # テーブル
            if stripped.startswith("|"):
                in_table = True
                table_lines.append(stripped)
                continue

            if in_table:
                self.add_table(_parse_md_table("\n".join(table_lines)))
                table_lines = []
                in_table = False

            # Mermaid / コードブロックはスキップ
            if stripped.startswith("```"):
                continue

            # 箇条書き
            if stripped.startswith("- ") or stripped.startswith("* "):
                self.add_bullet(stripped[2:])
                continue

            # メタ行（**作成日**: ... 等）はスキップ
            if stripped.startswith("**作成日"):
                continue

            # 水平線
            if stripped.startswith("---"):
                continue

            # 通常テキスト
            self.add_paragraph(stripped)

        # 残りのテーブル
        if in_table and table_lines:
            self.add_table(_parse_md_table("\n".join(table_lines)))


# ── メイン ──
def main():
    parser = argparse.ArgumentParser(description="システム概要書 PDF を生成")
    parser.add_argument("--docs-dir", required=True, help="docs/ ディレクトリのパス")
    parser.add_argument("--output-dir", required=True, help="出力先フォルダパス")
    parser.add_argument("--author", default="Claude Code", help="作成者名")
    parser.add_argument("--version", default="1.0", help="バージョン")
    args = parser.parse_args()

    docs = Path(args.docs_dir)
    org_profile = _read_if_exists(docs / "overview" / "org-profile.md")
    requirements = _read_if_exists(docs / "requirements" / "requirements.md")

    if not org_profile:
        print("[エラー] docs/overview/org-profile.md が見つかりません。", file=sys.stderr)
        print("先に /sf-memory で組織情報を収集してください。", file=sys.stderr)
        sys.exit(1)

    # org-profile から会社名・システム名を抽出
    company_name = ""
    system_name = ""
    for line in org_profile.splitlines():
        if "会社名" in line and "|" in line:
            parts = [c.strip() for c in line.split("|")]
            if len(parts) >= 3:
                company_name = parts[2]
                break
    for line in org_profile.splitlines():
        if "Salesforce利用目的" in line and "|" in line:
            parts = [c.strip() for c in line.split("|")]
            if len(parts) >= 3:
                system_name = parts[2]
                break

    # PDF 生成
    pdf = OverviewPDF(system_name=system_name, company_name=company_name)
    pdf.set_auto_page_break(auto=True, margin=20)

    # 表紙
    pdf.add_cover(author=args.author, version=args.version)

    # 組織プロフィール
    sections = _extract_sections(org_profile)
    for level, title, body in sections:
        pdf.add_page() if level == 1 else None
        pdf.add_heading(level, title)
        if body:
            pdf.add_md_section(body)

    # 要件定義（あれば）
    if requirements:
        req_sections = _extract_sections(requirements)
        for level, title, body in req_sections:
            if level == 1:
                pdf.add_page()
            pdf.add_heading(level, title)
            if body:
                pdf.add_md_section(body)

    # 出力
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"システム概要書_v{args.version}.pdf"
    pdf.output(str(output_path))
    print(f"\n完了: {output_path}")


if __name__ == "__main__":
    main()
