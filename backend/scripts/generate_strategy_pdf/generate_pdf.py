"""FT Strategy PDF Generator — Main Entry Point."""
import os
import sys

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor

# Add scripts directory to path for imports
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_SCRIPT_DIR)  # backend/scripts/
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from generate_strategy_pdf.styles import (
    styles, style_title, style_subtitle, style_h1, style_h2, style_h3,
    style_body, style_toc, style_toc_sub, style_cover_info, style_small,
    COLOR_PRIMARY, COLOR_TABLE_HEADER, COLOR_TABLE_ALT, HexColor
)
from generate_strategy_pdf.sections.volume1 import build_volume1
from generate_strategy_pdf.sections.volume2 import build_volume2
from generate_strategy_pdf.sections.volume3 import build_volume3

CHART_DIR = os.path.join(_SCRIPT_DIR, "charts")


class PDFGenerator:
    """Main PDF generator class."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            topMargin=22*mm,
            bottomMargin=20*mm,
            leftMargin=22*mm,
            rightMargin=22*mm,
            title="FT量化期货交易系统 — 完整策略文档",
            author="FT Quant Trading System",
        )
        self.story = []

    def build(self):
        """Assemble and generate the PDF."""
        self._add_cover()
        self._add_toc()
        build_volume1(self)
        build_volume2(self)
        build_volume3(self)
        self.doc.build(self.story)
        print(f"PDF generated: {self.output_path}")

    def _add_cover(self):
        self.story.append(Spacer(1, 50*mm))
        self.story.append(Paragraph("FT 量化期货交易系统", style_title))
        self.story.append(Spacer(1, 5*mm))
        self.story.append(Paragraph("完 整 策 略 文 档", ParagraphStyle(
            "CoverSub", fontName="SimHei", fontSize=18, textColor=COLOR_PRIMARY,
            alignment=1, leading=26, spaceAfter=15*mm
        )))
        self.story.append(Spacer(1, 10*mm))
        self.story.append(Paragraph(
            "Futures Trading Quantitative Strategy System", style_subtitle
        ))
        self.story.append(Spacer(1, 20*mm))
        self.story.append(Paragraph("海龟增强 V2 / V3", ParagraphStyle(
            "CoverV", fontName="SimSun", fontSize=13, textColor=HexColor("#2d6da8"),
            alignment=1, leading=18, spaceAfter=5*mm
        )))
        self.story.append(Spacer(1, 30*mm))
        self.story.append(Paragraph("2026-05-14", style_cover_info))
        self.story.append(Paragraph("基于 md/知识库/ 整理", style_cover_info))
        self.story.append(PageBreak())

    def _add_toc(self):
        self.story.append(Paragraph("目  录", style_h1))
        self.story.append(Spacer(1, 3*mm))

        toc = [
            (True, "第一卷  策略顶层设计"),
            (False, "第1章  执行摘要"),
            (False, "第2章  五大策略全景对比"),
            (False, "第3章  策略选择指南"),
            (True, "第二卷  策略逻辑详解"),
            (False, "第4章  海龟增强V2交易全流程"),
            (False, "第5章  海龟增强V3差异说明"),
            (False, "第6章  趋势因子指标体系"),
            (False, "第7章  止损系统设计"),
            (False, "第8章  实盘风险分析"),
            (True, "第三卷  功能实现与运维"),
            (False, "第9章  交易管理功能"),
            (False, "第10章  绩效看板"),
            (False, "第11章  K线分析"),
            (False, "第12章  日志监控"),
            (False, "第13章  回测系统"),
            (False, "附录A  关键参数速查表"),
            (False, "附录B  实盘操作手册"),
            (False, "附录C  术语表"),
        ]
        for is_vol, text in toc:
            if is_vol:
                self.story.append(Paragraph(text, style_toc))
            else:
                self.story.append(Paragraph(text, style_toc_sub))
        self.story.append(PageBreak())

    def add_heading1(self, text):
        self.story.append(Paragraph(text, style_h1))
        self.story.append(Spacer(1, 2*mm))

    def add_heading2(self, text):
        self.story.append(Paragraph(text, style_h2))
        self.story.append(Spacer(1, 1*mm))

    def add_heading3(self, text):
        self.story.append(Paragraph(text, style_h3))

    def add_body(self, text):
        lines = text.split("\n")
        for line in lines:
            if line.strip():
                self.story.append(Paragraph(line, style_body))

    def add_image(self, path, width=160*mm):
        full_path = os.path.join(CHART_DIR, path)
        if os.path.exists(full_path):
            self.story.append(Spacer(1, 2*mm))
            img = Image(full_path, width=width, height=width * 0.6)
            self.story.append(img)
            self.story.append(Spacer(1, 2*mm))

    def add_table(self, data, col_widths=None):
        """Add a styled table with header row."""
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_TABLE_HEADER),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
            ('FONTNAME', (0, 0), (-1, 0), "SimHei"),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), "SimSun"),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f5f7fa")]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(style)
        self.story.append(Spacer(1, 1*mm))
        self.story.append(t)
        self.story.append(Spacer(1, 2*mm))


if __name__ == "__main__":
    output = os.path.join(_SCRIPT_DIR, "output", "FT策略文档-完整版.pdf")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    gen = PDFGenerator(output)
    gen.build()
