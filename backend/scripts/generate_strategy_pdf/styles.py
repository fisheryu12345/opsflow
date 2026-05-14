"""PDF styles - Chinese font registration and paragraph styles."""
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_DIR = r"C:\Windows\Fonts"

pdfmetrics.registerFont(TTFont("SimSun", f"{_FONT_DIR}\\simsun.ttc"))
pdfmetrics.registerFont(TTFont("SimHei", f"{_FONT_DIR}\\simhei.ttf"))
pdfmetrics.registerFont(TTFont("KaiTi", f"{_FONT_DIR}\\simkai.ttf"))
pdfmetrics.registerFont(TTFont("FangSong", f"{_FONT_DIR}\\simfang.ttf"))

pdfmetrics.registerFontFamily(
    "SimSun", normal="SimSun", bold="SimHei", italic="KaiTi", boldItalic="SimHei"
)

# Colors
COLOR_PRIMARY = HexColor("#1a3a5c")
COLOR_SECONDARY = HexColor("#2d6da8")
COLOR_ACCENT = HexColor("#e8a838")
COLOR_LIGHT_BG = HexColor("#f0f4f8")
COLOR_TABLE_HEADER = HexColor("#1a3a5c")
COLOR_TABLE_ALT = HexColor("#f5f7fa")
COLOR_CODE_BG = HexColor("#f4f4f4")
COLOR_DARK_TEXT = HexColor("#333333")

styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "FTTitle", fontName="SimHei", fontSize=22, textColor=COLOR_PRIMARY,
    spaceAfter=6*mm, alignment=1, leading=32
)

style_subtitle = ParagraphStyle(
    "FTSubTitle", fontName="SimSun", fontSize=12, textColor=HexColor("#666666"),
    alignment=1, spaceAfter=3*mm, leading=18
)

style_h1 = ParagraphStyle(
    "FTH1", fontName="SimHei", fontSize=16, textColor=COLOR_PRIMARY,
    spaceBefore=8*mm, spaceAfter=4*mm, leading=24,
)

style_h2 = ParagraphStyle(
    "FTH2", fontName="SimHei", fontSize=13, textColor=COLOR_SECONDARY,
    spaceBefore=5*mm, spaceAfter=3*mm, leading=20
)

style_h3 = ParagraphStyle(
    "FTH3", fontName="SimHei", fontSize=11, textColor=COLOR_PRIMARY,
    spaceBefore=3*mm, spaceAfter=2*mm, leading=16
)

style_body = ParagraphStyle(
    "FTBody", fontName="SimSun", fontSize=10, textColor=black,
    spaceAfter=2*mm, leading=16, alignment=4
)

style_small = ParagraphStyle(
    "FTSmall", fontName="SimSun", fontSize=8, textColor=grey,
    spaceAfter=1*mm, leading=12
)

style_bullet = ParagraphStyle(
    "FTBullet", fontName="SimSun", fontSize=10, textColor=black,
    spaceAfter=1*mm, leading=16, leftIndent=8*mm, bulletIndent=3*mm,
    bulletFontName="SimHei", bulletFontSize=10
)

style_code = ParagraphStyle(
    "FTCode", fontName="Courier New", fontSize=8, textColor=COLOR_DARK_TEXT,
    spaceAfter=2*mm, leading=12, leftIndent=4*mm, backColor=COLOR_CODE_BG
)

style_table_header = ParagraphStyle(
    "FTTableHeader", fontName="SimHei", fontSize=9, textColor=white,
    alignment=1, leading=14
)

style_table_cell = ParagraphStyle(
    "FTTableCell", fontName="SimSun", fontSize=9, textColor=black,
    alignment=1, leading=14
)

style_toc = ParagraphStyle(
    "FTTOC", fontName="SimSun", fontSize=11, textColor=COLOR_PRIMARY,
    spaceAfter=2*mm, leading=18
)

style_toc_sub = ParagraphStyle(
    "FTTOCSub", fontName="SimSun", fontSize=10, textColor=HexColor("#444444"),
    spaceAfter=1.5*mm, leading=16, leftIndent=20
)

style_cover_info = ParagraphStyle(
    "FTCoverInfo", fontName="SimSun", fontSize=10, textColor=HexColor("#888888"),
    alignment=1, spaceAfter=2*mm, leading=14
)
