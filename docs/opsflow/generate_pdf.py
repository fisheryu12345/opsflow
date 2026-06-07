#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpsFlow Document → PDF Generator
Generates high-quality PDFs from OpsFlow markdown documentation with Chinese font support.

Usage:
    python generate_pdf.py                     # Generate ALL PDFs
    python generate_pdf.py --list              # List available documents
    python generate_pdf.py --file 01-architecture.md  # Generate single PDF
    python generate_pdf.py --file 07-bk_sops_opsflow.md --force  # Regenerate
"""

import os, re, sys, json, math, textwrap
from fpdf import FPDF

# ── Paths ──
DOC_DIR = os.path.dirname(os.path.abspath(__file__))
SIMHEI = 'c:/Windows/Fonts/simhei.ttf'
SIMSUN = 'c:/Windows/Fonts/simsun.ttc'

DOC_FILES = {
    '01-architecture.md': {
        'title': 'OpsFlow 系统架构设计',
        'desc': '系统架构 — 分层设计 + 执行流程 + 关键决策',
        'orientation': 'L',  # Landscape
    },
    '02-code-structure.md': {
        'title': 'OpsFlow 代码结构',
        'desc': '代码结构 — 目录树 + 模型关系 + API 端点 + 模块依赖',
        'orientation': 'L',
    },
    '03-core-engine.md': {
        'title': 'OpsFlow 核心引擎',
        'desc': '从模板到执行 — 完整流程详解',
        'orientation': 'P',  # Portrait
    },
    '04-frontend.md': {
        'title': 'OpsFlow 前端设计',
        'desc': '前端设计 — 页面结构 + X6 节点 + Stencil + 数据流',
        'orientation': 'L',
    },
    '05-feature-status.md': {
        'title': 'OpsFlow 功能状态',
        'desc': '功能状态 — 已完成/待实现 + Pipeline 格式 + 状态机',
        'orientation': 'L',
    },
    '06-deployment-notes.md': {
        'title': 'OpsFlow 部署注意事项',
        'desc': '生成环境部署注意事项 — 对项目外部文件的修改清单',
        'orientation': 'P',
    },
    '07-bk_sops_opsflow.md': {
        'title': 'OpsFlow vs bk_sops 全方位对比分析',
        'desc': '14维度130+子项 — 蓝鲸标准运维 vs OpsFlow AI-First 编排平台',
        'orientation': 'L',
        'comparison': True,  # Use table-heavy rendering
    },
    '08-模型表关系说明.md': {
        'title': 'OpsFlow 模型表关系说明',
        'desc': '15 个数据模型详解 — 字段表 + 约束 + FK 关系 + ER 图',
        'orientation': 'L',
    },
    '09-核心流程详解.md': {
        'title': 'OpsFlow 核心流程详解',
        'desc': 'FlowEngine/PipelineBuilder/PluginService/信号/Celery/超时/回滚/Webhook 全流程源码级解析',
        'orientation': 'P',
    },
}


class DocPDF(FPDF):
    """PDF generator for standard OpsFlow documentation (non-comparison)."""

    def __init__(self, orientation='L'):
        super().__init__(orientation, 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font('CHei', '', SIMHEI)
        self.add_font('CSun', '', SIMSUN)
        self._page_count = 0
        self._in_code_block = False

    def header(self):
        if self.page_no() > 1:
            self.set_font('CSun', '', 7)
            self.set_text_color(130, 130, 130)
            w = 287 if self.cur_orientation == 'L' else 190
            self.cell(0, 5, f'OpsFlow Documentation  |  {self.doc_title}', new_x="LMARGIN", new_y="NEXT", align='L')
            self.line(10, 12, w + 10, 12)
            self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('CSun', '', 7)
        self.set_text_color(153, 153, 153)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def cover_page(self, title, subtitle='', date_str=''):
        self.add_page()
        w = self.w - 20
        self.ln(40)
        # Title block
        self.set_fill_color(30, 64, 128)
        self.rect(20, 55, w - 20, 50, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('CHei', '', 26)
        self.set_y(63)
        self.multi_cell(w - 20, 14, title, align='C')
        if subtitle:
            self.set_font('CSun', '', 12)
            self.ln(4)
            self.cell(0, 8, subtitle, new_x="LMARGIN", new_y="NEXT", align='C')
        if date_str:
            self.set_font('CSun', '', 10)
            self.set_y(88)
            self.cell(0, 8, date_str, new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_text_color(80, 80, 80)
        self.set_y(130)
        self.set_font('CSun', '', 10)
        self.cell(0, 7, f'Generated: 2026-06-03  |  Source: backend/opsflow/doc/', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(30)

    def render_markdown(self, md_text, doc_title=''):
        """Render markdown text into PDF pages."""
        self.doc_title = doc_title
        lines = md_text.split('\n')
        i = 0
        self._in_code_block = False
        code_buffer = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # ── Code block toggle ──
            if stripped.startswith('```'):
                if not self._in_code_block:
                    self._in_code_block = True
                    code_buffer = []
                else:
                    self._render_code_block(code_buffer)
                    code_buffer = []
                    self._in_code_block = False
                i += 1
                continue

            if self._in_code_block:
                code_buffer.append(line.rstrip())
                i += 1
                continue

            # ── Skip empty decorative lines ──
            if stripped == '':
                if i > 0 and lines[i-1].strip() == '':
                    i += 1
                    continue
                self.ln(2)
                i += 1
                continue

            # ── Horizontal rule ──
            if stripped.startswith('---') or stripped.startswith('***'):
                self.ln(2)
                w = self.w - 40
                y = self.get_y()
                self.set_draw_color(200, 200, 200)
                self.line(20, y, 20 + w, y)
                self.ln(4)
                i += 1
                continue

            # ── Headings ──
            if stripped.startswith('## '):
                self._page_check(12)
                self.set_font('CHei', '', 14)
                self.set_text_color(30, 64, 128)
                self.set_fill_color(235, 240, 248)
                txt = stripped[3:]
                self.cell(0, 9, f'  {txt}', new_x="LMARGIN", new_y="NEXT", fill=True)
                self.ln(3)
                i += 1
                continue

            if stripped.startswith('### '):
                self._page_check(10)
                self.set_font('CHei', '', 11)
                self.set_text_color(41, 82, 138)
                txt = stripped[4:]
                self.cell(0, 7, txt, new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
                i += 1
                continue

            if stripped.startswith('#### '):
                self._page_check(8)
                self.set_font('CHei', '', 10)
                self.set_text_color(60, 60, 60)
                txt = stripped[5:]
                self.cell(0, 6, txt, new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
                i += 1
                continue

            if stripped.startswith('# ') and not self.page_no() > 1:
                # Already rendered cover page
                i += 1
                continue

            if stripped.startswith('# '):
                self._page_check(10)
                self.set_font('CHei', '', 13)
                self.set_text_color(30, 64, 128)
                txt = stripped[2:]
                self.cell(0, 8, txt, new_x="LMARGIN", new_y="NEXT")
                self.ln(2)
                i += 1
                continue

            # ── Table lines ──
            if '|' in stripped and stripped.startswith('|'):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                self._render_table_from_md(table_lines)
                self.ln(2)
                continue

            # ── Bullet / Ordered list ──
            if stripped.startswith('- ') or stripped.startswith('* '):
                self._page_check(6)
                self.set_font('CSun', '', 9)
                self.set_text_color(51, 51, 51)
                indent = 5
                txt = stripped[2:]
                # Handle inline code in bullets
                txt = re.sub(r'`([^`]+)`', r'[\1]', txt)
                bullet_char = '•'  # bullet character
                x0 = self.get_x()
                self.set_x(x0 + indent)
                self.multi_cell(self.w - 40 - indent, 5.5, f'{bullet_char} {txt}')
                self.set_x(x0)
                i += 1
                continue

            if re.match(r'^\d+[.)]\s', stripped):
                self._page_check(6)
                self.set_font('CSun', '', 9)
                self.set_text_color(51, 51, 51)
                txt = re.sub(r'`([^`]+)`', r'[\1]', stripped)
                self.multi_cell(self.w - 40, 5.5, txt)
                i += 1
                continue

            # ── Quote ──
            if stripped.startswith('> '):
                quote_lines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    quote_lines.append(lines[i].strip()[2:])
                    i += 1
                self._page_check(6)
                self.set_fill_color(245, 247, 250)
                self.set_draw_color(200, 210, 230)
                txt = ' '.join(quote_lines)
                txt = re.sub(r'`([^`]+)`', r'[\1]', txt)
                y0 = self.get_y()
                self.set_font('CSun', '', 8.5)
                self.set_text_color(80, 80, 80)
                self.set_x(18)
                self.multi_cell(self.w - 36, 5, txt, border=1, fill=True)
                self.set_x(10)
                self.ln(2)
                continue

            # ── Regular paragraph ──
            self._page_check(6)
            self.set_font('CSun', '', 9)
            self.set_text_color(51, 51, 51)
            txt = re.sub(r'`([^`]+)`', r'[\1]', stripped)
            self.multi_cell(self.w - 40, 5.5, txt)
            i += 1

    def _page_check(self, needed_mm=6):
        if self.get_y() > 275 - needed_mm:
            self.add_page()

    def _has_non_ascii(self, text):
        """Check if text contains any non-ASCII character (Chinese, box drawing, etc.)"""
        return any(ord(c) > 127 for c in text)

    def _render_code_block(self, code_lines):
        if not code_lines:
            return
        self._page_check(10)
        self.set_fill_color(245, 247, 250)
        self.set_draw_color(210, 215, 225)
        self.set_text_color(40, 40, 40)

        # Use CSun font for code with non-ASCII, Courier for pure ASCII
        has_non_ascii = any(self._has_non_ascii(l) for l in code_lines)
        code_font = 'CSun' if has_non_ascii else 'Courier'
        code_size = 6.5 if has_non_ascii else 7
        self.set_font(code_font, '', code_size)

        line_h = 4
        code_h = len(code_lines) * line_h + 6
        if self.get_y() + code_h > 275:
            self.add_page()
            self.set_fill_color(245, 247, 250)
            self.set_draw_color(210, 215, 225)
            self.set_font(code_font, '', code_size)
            self.set_text_color(40, 40, 40)

        y0 = self.get_y()
        x_margin = 12
        max_w = self.w - 24
        for cl in code_lines:
            self.set_x(x_margin)
            display = cl if cl else ' '
            w = self.get_string_width(display)
            if w > max_w:
                # Truncate with ellipsis
                while self.get_string_width(display + '…') > max_w and len(display) > 4:
                    display = display[:-1]
                display += '…'
            self.cell(max_w, line_h, display, align='L')
            self.ln()
        y1 = self.get_y()
        self.set_draw_color(210, 215, 225)
        self.rect(x_margin - 2, y0 - 1, max_w + 4, y1 - y0 + 1, 'D')
        self.ln(3)

    def _render_table_from_md(self, table_lines):
        """Parse and render a markdown table."""
        if len(table_lines) < 2:
            return
        # Parse headers
        headers = [h.strip() for h in table_lines[0].split('|')[1:-1]]
        # Parse data rows (skip separator line)
        data = []
        for line in table_lines[2:]:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                data.append(cells)

        if not headers or not data:
            return

        self._page_check(12)
        n_cols = len(headers)
        avail_w = self.w - 30
        col_w = max(20, avail_w // n_cols - 2)

        def draw_header():
            self.set_font('CHei', '', 7.5)
            self.set_fill_color(41, 82, 138)
            self.set_text_color(255, 255, 255)
            for h in headers:
                self.cell(col_w, 7, f' {h}', border=1, align='C', fill=True)
            self.ln()

        draw_header()
        self.set_font('CSun', '', 7)
        fill = False
        for row in data:
            if fill:
                self.set_fill_color(240, 244, 250)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(51, 51, 51)

            # Estimate row height
            max_lines = 1
            for i, cell in enumerate(row):
                est = max(1, math.ceil(len(cell) / max(1, col_w // 2.5)))
                if est > max_lines:
                    max_lines = est
            row_h = max(6, max_lines * 4.5)

            if self.get_y() + row_h > 275:
                self.add_page()
                draw_header()
                self.set_font('CSun', '', 7)
                if fill:
                    self.set_fill_color(240, 244, 250)
                else:
                    self.set_fill_color(255, 255, 255)
                self.set_text_color(51, 51, 51)

            x0 = self.get_x()
            y0 = self.get_y()
            for i, cell in enumerate(row):
                x = x0 + i * col_w
                self.set_xy(x, y0)
                self.rect(x, y0, col_w, row_h, 'F')
                self.rect(x, y0, col_w, row_h, 'D')
                self.set_xy(x + 1, y0 + 0.5)
                self.multi_cell(col_w - 2, 4.5, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill


class ComparisonPDF(DocPDF):
    """Specialized PDF for the bk_sops comparison document (heavy tables)."""

    def render_markdown(self, md_text, doc_title=''):
        self.doc_title = doc_title
        lines = md_text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped == '':
                self.ln(1)
                i += 1
                continue
            if stripped.startswith('```'):
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    i += 1
                i += 1
                continue

            # Section title
            if stripped.startswith('## ') and '对比' in stripped:
                self._page_check(12)
                self.set_font('CHei', '', 14)
                self.set_fill_color(30, 64, 128)
                self.set_text_color(255, 255, 255)
                txt = stripped[3:]
                self.cell(0, 10, f'  {txt}', new_x="LMARGIN", new_y="NEXT", fill=True)
                self.ln(3)
                i += 1
                continue

            if stripped.startswith('## '):
                self._page_check(10)
                self.set_font('CHei', '', 12)
                self.set_text_color(30, 64, 128)
                self.set_fill_color(235, 240, 248)
                txt = stripped[3:]
                self.cell(0, 9, f'  {txt}', new_x="LMARGIN", new_y="NEXT", fill=True)
                self.ln(2)
                i += 1
                continue

            if stripped.startswith('### '):
                self._page_check(8)
                self.set_font('CHei', '', 10)
                self.set_text_color(41, 82, 138)
                txt = stripped[4:]
                self.cell(0, 7, txt, new_x="LMARGIN", new_y="NEXT")
                self.ln(1)
                i += 1
                continue

            if stripped.startswith('#'):
                i += 1
                continue

            # Tables
            if '|' in stripped and stripped.startswith('|'):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                self._render_big_table(table_lines)
                self.ln(2)
                continue

            # Bullet / list
            if stripped.startswith('- ') or stripped.startswith('* '):
                self._page_check(6)
                self.set_font('CSun', '', 9)
                self.set_text_color(51, 51, 51)
                txt = re.sub(r'`([^`]+)`', r'[\1]', stripped[2:])
                self.multi_cell(self.w - 40, 5, f'  {txt}')
                i += 1
                continue

            if re.match(r'^\d+[.)]\s', stripped):
                self._page_check(6)
                self.set_font('CSun', '', 9)
                self.set_text_color(51, 51, 51)
                txt = re.sub(r'`([^`]+)`', r'[\1]', stripped)
                self.multi_cell(self.w - 40, 5, txt)
                i += 1
                continue

            # Regular paragraph
            self._page_check(6)
            self.set_font('CSun', '', 9)
            self.set_text_color(51, 51, 51)
            txt = re.sub(r'`([^`]+)`', r'[\1]', stripped)
            self.multi_cell(self.w - 40, 5, txt)
            i += 1

    def _render_big_table(self, table_lines):
        """Render table for comparison doc."""
        if len(table_lines) < 2:
            return
        headers = [h.strip() for h in table_lines[0].split('|')[1:-1]]
        data = []
        for line in table_lines[2:]:
            cells = [c.strip() for c in line.split('|')[1:-1]]
            if cells:
                data.append(cells)
        if not headers or not data:
            return

        self._page_check(12)
        n_cols = len(headers)
        avail_w = self.w - 30
        # For 3-4 column tables, use proportional widths
        if n_cols <= 3:
            col_w = [avail_w * 0.25, avail_w * 0.40, avail_w * 0.35] if n_cols == 3 else [avail_w // n_cols] * n_cols
        elif n_cols == 4:
            col_w = [avail_w * 0.12, avail_w * 0.32, avail_w * 0.32, avail_w * 0.24]
        else:
            col_w = [avail_w / n_cols] * n_cols

        def draw_header():
            self.set_font('CHei', '', 7.5)
            self.set_fill_color(41, 82, 138)
            self.set_text_color(255, 255, 255)
            for i, h in enumerate(headers):
                self.cell(col_w[i], 7, f' {h}', border=1, align='C', fill=True)
            self.ln()

        draw_header()
        self.set_font('CSun', '', 7)
        fill = False
        for row in data:
            if fill:
                self.set_fill_color(240, 244, 250)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(51, 51, 51)

            # Estimate row height
            max_lines = 1
            for i, cell in enumerate(row):
                cw = col_w[i] - 2
                est = max(1, math.ceil(len(cell) / max(1, cw // 2.5)))
                if est > max_lines:
                    max_lines = est
            row_h = max(6, max_lines * 4.5)

            if self.get_y() + row_h > 275:
                self.add_page()
                draw_header()
                self.set_font('CSun', '', 7)
                if fill:
                    self.set_fill_color(240, 244, 250)
                else:
                    self.set_fill_color(255, 255, 255)
                self.set_text_color(51, 51, 51)

            x0 = self.get_x()
            y0 = self.get_y()
            for i, cell in enumerate(row):
                x = x0 + sum(col_w[:i])
                self.set_xy(x, y0)
                self.rect(x, y0, col_w[i], row_h, 'F')
                self.rect(x, y0, col_w[i], row_h, 'D')
                self.set_xy(x + 1, y0 + 0.5)
                self.multi_cell(col_w[i] - 2, 4.5, cell)
            self.set_xy(x0, y0 + row_h)
            fill = not fill


# ══════════════════════════════════════════════════
#  Generation Functions
# ══════════════════════════════════════════════════

def generate_doc_pdf(filename, force=False):
    """Generate PDF from a standard doc markdown file."""
    md_path = os.path.join(DOC_DIR, filename)
    info = DOC_FILES.get(filename)
    if not info:
        print(f'  [SKIP] Unknown doc: {filename}')
        return False

    pdf_path = md_path.replace('.md', '.pdf')
    if os.path.exists(pdf_path) and not force:
        print(f'  [EXISTS] {pdf_path}')
        return True

    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    is_comparison = info.get('comparison', False)
    pdf_cls = ComparisonPDF if is_comparison else DocPDF
    pdf = pdf_cls(orientation=info['orientation'])

    # Cover page
    pdf.cover_page(info['title'], info['desc'], '2026-06-03')

    # Render content
    pdf.render_markdown(md_text, info['title'])

    pdf.output(pdf_path)
    pages = pdf.page_no()
    print(f'  [OK] {pdf_path} ({pages} pages)')
    return True


def generate_all():
    """Generate PDFs for all registered doc files."""
    print(f'\n=== OpsFlow Document PDF Generator ===')
    print(f'Source: {DOC_DIR}')
    print(f'Documents: {len(DOC_FILES)}\n')

    ok = fail = skip = 0
    for fname in sorted(DOC_FILES.keys()):
        md_path = os.path.join(DOC_DIR, fname)
        if not os.path.exists(md_path):
            print(f'  [MISSING] {md_path}')
            skip += 1
            continue
        print(f'  Processing: {fname}...')
        try:
            if generate_doc_pdf(fname, force=True):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f'  [ERROR] {fname}: {e}')
            fail += 1

    print(f'\n=== Summary: {ok} OK, {fail} Failed, {skip} Skipped ===')
    return ok, fail, skip


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate OpsFlow doc PDFs')
    parser.add_argument('--file', '-f', help='Generate specific file (e.g. 01-architecture.md)')
    parser.add_argument('--force', action='store_true', help='Force regenerate even if PDF exists')
    parser.add_argument('--list', action='store_true', help='List available documents')
    args = parser.parse_args()

    if args.list:
        print('\nAvailable documents:')
        for fname, info in sorted(DOC_FILES.items()):
            md_path = os.path.join(DOC_DIR, fname)
            exists = '[x]' if os.path.exists(md_path) else '[ ]'
            pdf_path = md_path.replace('.md', '.pdf')
            pdf_exists = '[PDF]' if os.path.exists(pdf_path) else '[   ]'
            print(f'  {exists} {pdf_exists} {fname} — {info["desc"]}')
        print()
    elif args.file:
        if args.file not in DOC_FILES:
            print(f'Unknown file: {args.file}')
            print(f'Available: {", ".join(DOC_FILES.keys())}')
            sys.exit(1)
        generate_doc_pdf(args.file, force=args.force)
    else:
        generate_all()
