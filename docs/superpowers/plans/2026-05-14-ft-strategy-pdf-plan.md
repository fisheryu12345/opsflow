# FT 策略文档 PDF 生成 — 实现计划

> **For agentic workers:** 使用 superpowers:executing-plans 按任务逐步执行。

**目标：** 将 md/知识库 下的策略文档（02/03/04/09）组织为一份约 60-70 页的 FT 策略完整PDF，BCG 风格，含图表。

**架构：** 单 Python 脚本体系，reportlab 排版，matplotlib 生成所有图表。不使用 graphviz（系统未安装），改用 matplotlib patches 绘制流程图。

**Tech Stack:** Python 3.11+, reportlab, matplotlib, numpy, pandas

---

### Task 1: 项目骨架与内容加载器

**Files:**
- Create: `backend/scripts/generate_strategy_pdf/__init__.py`
- Create: `backend/scripts/generate_strategy_pdf/content_loader.py`
- Create: `backend/scripts/generate_strategy_pdf/styles.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p "c:/Users/dell/Desktop/Vue/backend/scripts/generate_strategy_pdf/charts" "c:/Users/dell/Desktop/Vue/backend/scripts/generate_strategy_pdf/sections" "c:/Users/dell/Desktop/Vue/backend/scripts/generate_strategy_pdf/output"
```

- [ ] **Step 2: 编写 content_loader.py**

功能：从 md/知识库/ 读取所有 .md 文件，提取标题和正文，返回结构化字典。

```python
"""Content loader - reads knowledge base markdown files."""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(r"c:\Users\dell\Desktop\Vue\md\知识库\未命名")

def load_section(section_dir: str) -> List[Dict]:
    """Load all markdown files from a section directory."""
    section_path = BASE_DIR / section_dir
    docs = []
    if not section_path.exists():
        return docs
    for f in sorted(section_path.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        title = extract_title(content)
        docs.append({"title": title, "file": f.name, "content": content, "path": str(f)})
    return docs

def extract_title(content: str) -> str:
    """Extract first H1 or H2 from markdown."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# ") or line.startswith("## "):
            return line.lstrip("#").strip()
    return ""

def load_knowledge_base() -> Dict[str, List[Dict]]:
    """Load all relevant sections from the knowledge base."""
    return {
        "02-软件功能说明": load_section("02-软件功能说明"),
        "03-策略说明": load_section("03-策略说明"),
        "04-策略设计文档": load_section("04-策略设计文档"),
        "09-回测逻辑": load_section("09-回测逻辑"),
    }

def md_to_paragraphs(content: str) -> List[str]:
    """Split markdown into paragraph blocks, stripping markdown syntax."""
    paragraphs = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Remove heading markers
        text = re.sub(r'^#{1,6}\s+', '', stripped)
        # Remove bold/italic markers
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        # Remove code block markers
        if text.startswith("```"):
            continue
        # Remove table separators
        if re.match(r'^[\s\|:-]+$', text):
            continue
        paragraphs.append(text)
    return paragraphs

def extract_tables(content: str) -> List[List[List[str]]]:
    """Extract markdown tables as list of rows."""
    tables = []
    lines = content.split("\n")
    in_table = False
    current_table = []
    for line in lines:
        if line.strip().startswith("|") and line.strip().endswith("|"):
            if not in_table:
                in_table = True
                current_table = []
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            current_table.append(cells)
        else:
            if in_table and len(current_table) > 1:
                # Skip separator row (2nd row with ---)
                if len(current_table) >= 2:
                    header = current_table[0]
                    data_rows = [r for r in current_table[2:] if r]
                    if header and data_rows:
                        tables.append([header] + data_rows)
            in_table = False
            current_table = []
    if in_table and len(current_table) > 1:
        if len(current_table) >= 2:
            header = current_table[0]
            data_rows = [r for r in current_table[2:] if r]
            if header and data_rows:
                tables.append([header] + data_rows)
    return tables
```

- [ ] **Step 3: 编写 styles.py**

定义 reportlab 样式，注册中文字体。

```python
"""PDF styles - Chinese font registration and paragraph styles."""
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Chinese fonts
_FONT_DIR = r"C:\Windows\Fonts"

pdfmetrics.registerFont(TTFont("SimSun", f"{_FONT_DIR}\\simsun.ttc"))
pdfmetrics.registerFont(TTFont("SimHei", f"{_FONT_DIR}\\simhei.ttf"))
pdfmetrics.registerFont(TTFont("KaiTi", f"{_FONT_DIR}\\simkai.ttf"))
pdfmetrics.registerFont(TTFont("FangSong", f"{_FONT_DIR}\\simfang.ttf"))

pdfmetrics.registerFontFamily(
    "SimSun", normal="SimSun", bold="SimHei", italic="KaiTi", boldItalic="SimHei"
)

# Colors
COLOR_PRIMARY = HexColor("#1a3a5c")     # Dark navy
COLOR_SECONDARY = HexColor("#2d6da8")   # Medium blue
COLOR_ACCENT = HexColor("#e8a838")      # Gold accent
COLOR_LIGHT_BG = HexColor("#f0f4f8")    # Light blue-grey
COLOR_TABLE_HEADER = HexColor("#1a3a5c")
COLOR_TABLE_ALT = HexColor("#f5f7fa")
COLOR_CODE_BG = HexColor("#f4f4f4")

# Styles
styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "FTTitle", fontName="SimHei", fontSize=22, textColor=COLOR_PRIMARY,
    spaceAfter=6*mm, alignment=1, leading=32
)

style_h1 = ParagraphStyle(
    "FTH1", fontName="SimHei", fontSize=16, textColor=COLOR_PRIMARY,
    spaceBefore=8*mm, spaceAfter=4*mm, leading=24,
    borderWidth=0, borderPadding=4
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
    spaceAfter=2*mm, leading=16, alignment=4  # justified
)

style_small = ParagraphStyle(
    "FTSmall", fontName="SimSun", fontSize=8, textColor=grey,
    spaceAfter=1*mm, leading=12
)

style_bullet = ParagraphStyle(
    "FTBullet", fontName="SimSun", fontSize=10, textColor=black,
    spaceAfter=1*mm, leading=16, leftIndent=8*mm, bulletIndent=3*mm
)

style_code = ParagraphStyle(
    "FTCode", fontName="Courier New", fontSize=8, textColor=HexColor("#333333"),
    spaceAfter=2*mm, leading=12, leftIndent=4*mm,
    backColor=COLOR_CODE_BG
)

style_table_header = ParagraphStyle(
    "FTTableHeader", fontName="SimHei", fontSize=9, textColor=white,
    alignment=1, leading=14
)

style_table_cell = ParagraphStyle(
    "FTTableCell", fontName="SimSun", fontSize=9, textColor=black,
    alignment=1, leading=14
)
```

---

### Task 2: 图表生成模块

**Files:**
- Create: `backend/scripts/generate_strategy_pdf/charts/__init__.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/radar_chart.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/mapping_curve.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/equity_curve.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/heatmap.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/price_diagram.py`
- Create: `backend/scripts/generate_strategy_pdf/charts/flow_diagrams.py`

- [ ] **Step 1: 雷达图**

```python
"""Five-strategy comparison radar chart."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
import os

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

def create_radar_chart(output_path: str):
    """Create radar chart comparing 5 strategies across 5 dimensions."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_cn_small = FontProperties(fname=os.path.join(os.path.dirname(FONT_PATH), "simsun.ttc"))

    categories = ['趋势市收益', '震荡市防御', '回撤控制', '风控可控', '国内适配']
    N = len(categories)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    strategies = {
        '海龟原版': [9, 2, 5, 7, 4],
        'MA10斜率': [7, 4, 7, 8, 8],
        '双均线':   [5, 2, 3, 2, 3],
        '海龟V2':   [9, 4, 7, 8, 7],
        '海龟V3':   [8, 6, 8, 8, 7],
    }
    colors = ['#8B0000', '#2E8B57', '#DAA520', '#1a3a5c', '#2d6da8']

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for i, (name, values) in enumerate(strategies.items()):
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, color=colors[i], label=name)
        ax.fill(angles, values, alpha=0.05, color=colors[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontproperties=font_cn_small, fontsize=11)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=8)
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), prop=font_cn, fontsize=10)
    ax.set_title('五大策略综合能力雷达图', fontproperties=font_cn, fontsize=16, pad=20, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Radar chart saved to {output_path}")
```

- [ ] **Step 2: 趋势因子映射曲线**

```python
"""Trend factor mapping curve."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

def create_mapping_curve(output_path: str):
    """Plot trend_strength → trend_factor and stop_multiplier."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    gap_limit = 0.03
    factor_max = 0.5
    base_stop = 2.0

    gaps = np.linspace(0, 0.05, 100)
    strengths = np.minimum(gaps / gap_limit, 1.0)
    factors = np.round(strengths * factor_max, 3)
    multipliers = base_stop * (1 + factors)

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(gaps * 100, factors, 'b-', linewidth=2.5, label='trend_factor')
    ax1.set_xlabel('均线间距 (%)', fontproperties=font_body, fontsize=11)
    ax1.set_ylabel('trend_factor', color='b', fontproperties=font_body, fontsize=11)
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_ylim(0, 0.6)

    ax2 = ax1.twinx()
    ax2.plot(gaps * 100, multipliers, 'r--', linewidth=2.5, label='止损倍数 (ATR)')
    ax2.set_ylabel('止损倍数 (ATR)', color='r', fontproperties=font_body, fontsize=11)
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(1.5, 3.5)

    ax1.axvline(x=3.0, color='gray', linestyle=':', alpha=0.5)
    ax1.annotate('封顶 3%', xy=(3, 0.5), xytext=(3.5, 0.45),
                fontproperties=font_body, fontsize=9, color='gray')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', prop=font_body, fontsize=10)

    ax1.set_title('趋势因子与止损倍数映射曲线', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
```

- [ ] **Step 3: 回撤曲线**

```python
"""Equity/ drawdown curve."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

def create_equity_curve(output_path: str):
    """Simulate equity curve with drawdown shading."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    np.random.seed(42)
    days = 250
    returns = np.random.normal(0.001, 0.015, days)
    equity = 1000000 * np.cumprod(1 + returns)
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak * 100

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [3, 1]})

    ax1.plot(equity, color='#1a3a5c', linewidth=1.5)
    ax1.fill_between(range(days), equity, peak, alpha=0.15, color='#c0392b')
    ax1.set_ylabel('账户权益 (¥)', fontproperties=font_body, fontsize=10)
    ax1.set_title('账户资金曲线与回撤', fontproperties=font_cn, fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    ax2.fill_between(range(days), 0, drawdown, color='#c0392b', alpha=0.5)
    ax2.set_ylabel('回撤 (%)', fontproperties=font_body, fontsize=10)
    ax2.set_xlabel('交易日', fontproperties=font_body, fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
```

- [ ] **Step 4: 日历热力图**

```python
"""Calendar heatmap of daily returns."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

def create_heatmap(output_path: str):
    """Generate calendar heatmap of daily returns."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    np.random.seed(123)
    dates = pd.date_range('2025-01-01', '2025-12-31', freq='B')
    returns = np.random.normal(0.001, 0.015, len(dates))

    df = pd.DataFrame({'date': dates, 'return': returns})
    df['year'] = df['date'].year
    df['month'] = df['date'].month
    df['day'] = df['date'].day

    pivot = df.pivot_table(values='return', index='day', columns='month', aggfunc='mean')
    pivot = pivot * 100  # to percentage

    colors_custom = [(0, 0.3, 0), (1, 1, 1), (0.5, 0, 0)]
    cmap = LinearSegmentedColormap.from_list('custom', colors_custom, N=256)

    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.imshow(pivot.values, cmap=cmap, aspect='auto', vmin=-1, vmax=1)

    ax.set_xticks(range(12))
    ax.set_xticklabels(['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'],
                       fontproperties=font_body, fontsize=9)
    ax.set_yticks(range(1, 32, 5))
    ax.set_yticklabels(range(1, 32, 5), fontsize=7)
    ax.set_xlabel('月份', fontproperties=font_body, fontsize=10)
    ax.set_ylabel('日', fontproperties=font_body, fontsize=10)
    ax.set_title('日收益率日历热力图（模拟示例）', fontproperties=font_cn, fontsize=13, fontweight='bold')

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label('日收益率 (%)', fontproperties=font_body, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
```

- [ ] **Step 5: 流程图（matplotlib patches）**

```python
"""Flow diagrams using matplotlib patches (no graphviz needed)."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties
import numpy as np

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"

def create_architecture_diagram(output_path: str):
    """System architecture using matplotlib patches + arrows."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # Draw boxes
    def draw_box(x, y, w, h, text, color='#1a3a5c', fc='#e8f0fe'):
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                       facecolor=fc, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, fontproperties=font_cn, fontsize=9,
               ha='center', va='center', color=color)

    def draw_arrow(x1, y1, x2, y2, color='gray'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

    # Layer 1: Frontend
    draw_box(1, 6.5, 8, 1, '前端 Vue3\n信号监控 / 持仓管理 / 绩效看板 / 合约配置')
    # Layer 2: Django Backend
    draw_box(0.5, 4, 4, 1.8, 'APScheduler\n开盘 09:02\n收盘 15:02\n临收盘 14:55')
    draw_box(5, 4, 4, 1.8, 'Django REST Framework\nViewSets / CRUD / WebSocket\n邮件服务')
    # Layer 3: TqSDK
    draw_box(3, 2.5, 4, 1, 'TqSDK (天勤)\n行情数据 / 交易执行')
    # Layer 4: Exchange
    draw_box(3, 0.5, 4, 1, '国内期货交易所\nSHFE / DCE / CZCE / CFFEX / INE')

    # Arrows
    draw_arrow(5, 6.5, 5, 5.8)
    draw_arrow(2.5, 5.8, 2.5, 4)
    draw_arrow(5, 5.8, 5, 4)
    draw_arrow(5, 4, 5, 3.5)
    draw_arrow(5, 2.5, 5, 1.5)

    ax.set_title('FT 量化期货交易系统 — 系统架构图', fontproperties=font_cn, fontsize=15, fontweight='bold', pad=10)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

def create_timeline_diagram(output_path: str):
    """Daily trading timeline."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # Timeline axis
    ax.plot([1, 23], [2, 2], 'k-', linewidth=2, color='#333')

    # Time points
    points = [
        (9, 2, '09:02\n开盘任务', '#2d6da8'),
        (14, 55, '14:55\n临收盘止损', '#c0392b'),
        (15, 2, '15:02\n收盘计算', '#1a3a5c'),
        (21, 2, '21:02\n夜盘开盘\n(同09:02)', '#2d6da8'),
    ]

    for h, m, label, color in points:
        x = h + m/60
        ax.plot(x, 2, 'o', color=color, markersize=12, zorder=5)
        ax.annotate(label, xy=(x, 2), xytext=(x, 2.8),
                   fontproperties=font_cn, fontsize=9, color=color,
                   ha='center', va='bottom', fontweight='bold')
        # Vertical line
        ax.plot([x, x], [0.5, 2], ':', color=color, alpha=0.4)

    ax.set_title('每日交易时间线', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

def create_signal_state_diagram(output_path: str):
    """Signal state machine."""
    font_cn = FontProperties(fname=FONT_PATH)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def draw_state(x, y, text, color='#1a3a5c', fc='#e8f0fe'):
        rect = mpatches.FancyBboxPatch((x-1, y-0.4), 2, 0.8, boxstyle="round,pad=0.1",
                                       facecolor=fc, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y, text, fontproperties=font_cn, fontsize=10,
               ha='center', va='center', color=color, fontweight='bold')

    def draw_arrow(x1, y1, x2, y2, label=''):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2+0.2, label, fontproperties=font_cn,
                   fontsize=8, ha='center', va='bottom', color='#555')

    draw_state(5, 5, 'PENDING', '#e67e22', '#fef5e7')
    draw_state(5, 3.5, 'EXECUTING', '#2d6da8', '#e8f0fe')
    draw_state(2, 1.5, 'SUCCESS', '#27ae60', '#e8f8e8')
    draw_state(5, 1.5, 'FAILED', '#c0392b', '#fde8e8')
    draw_state(8, 1.5, 'CANCELLED', '#95a5a6', '#f4f4f4')

    draw_arrow(5, 4.6, 5, 3.9, '开盘任务 pickup')
    draw_arrow(5, 3.1, 2, 1.9, '成交成功')
    draw_arrow(5, 3.1, 5, 1.9, '成交失败')
    draw_arrow(5, 3.1, 8, 1.9, '条件不满足')
    draw_arrow(2, 1.1, 2, 0.2, '')
    # Cross-day
    ax.text(2, 0.2, '← 跨日保留 PENDING', fontproperties=font_cn, fontsize=8, color='#888')

    ax.set_title('信号状态流转图', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

def create_stop_loss_diagram(output_path: str):
    """Stop loss dual-layer mechanism diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def draw_box(x, y, w, h, text, color='#1a3a5c', fc='#e8f0fe', fs=9):
        rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                       facecolor=fc, edgecolor=color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, fontproperties=font_cn, fontsize=fs,
               ha='center', va='center', color=color)

    def draw_arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', color='#555', lw=1.5))

    # Layer 1: Dynamic stop loss
    draw_box(1, 4, 8, 1.2,
             '第一层: 动态跟踪止损\n多头: highest_close - 2×(1+factor)×ATR   |   空头: lowest_close + 2×(1+factor)×ATR\n趋势自适应: factor=0→震荡(2.0ATR)  ~  factor=0.5→强趋势(3.0ATR)',
             '#2d6da8', '#e8f0fe', 8)

    # Layer 2: Breakeven
    draw_box(1, 2.2, 8, 1.2,
             '第二层: 保本兜底\n触发条件: 盈利 > 2.5×ATR → protect_cost_enabled=True (单向开关，永不关闭)\n保本价: 多头=成本价+tick×2  |  空头=成本价-tick×2',
             '#27ae60', '#e8f8e8', 8)

    # Decision
    draw_box(2.5, 0.5, 5, 1.2,
             '最终止损价\n多头: max(动态止损, 保本价)\n空头: min(动态止损, 保本价)',
             '#1a3a5c', '#f0f4f8', 9)

    draw_arrow(5, 4, 5, 3.4)
    draw_arrow(5, 2.2, 5, 1.7)

    ax.set_title('止损双层机制示意图', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

def create_price_diagram(output_path: str):
    """Pyramid add-on price diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=r"C:\Windows\Fonts\simsun.ttc")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 6)
    ax.set_ylim(4960, 5100)
    ax.set_xlabel('', fontproperties=font_body)
    ax.set_ylabel('价格', fontproperties=font_body, fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    prices = [5000, 5020, 5040]
    labels = ['开仓点 P₀=5000\n唐奇安突破→ENTRY', '+1 Unit\n涨超0.5×ATR\n(price≥5020)', '+2 Unit直接满仓\n涨超1.0×ATR\n(price≥5040)']
    colors = ['#1a3a5c', '#2d6da8', '#e8a838']

    for i, (p, l, c) in enumerate(zip(prices, labels, colors)):
        x = i * 2 + 1
        ax.plot(x, p, 'o', color=c, markersize=15, zorder=5)
        ax.annotate(l, xy=(x, p), xytext=(x + 0.8, p + 5 if i % 2 == 0 else p - 15),
                   fontproperties=font_cn, fontsize=9, color=c,
                   ha='center', va='bottom',
                   arrowprops=dict(arrowstyle='->', color=c, lw=1))

    ax.axhline(y=5000, color='#1a3a5c', linestyle='--', alpha=0.3)
    ax.axhline(y=5020, color='#2d6da8', linestyle='--', alpha=0.3)
    ax.axhline(y=5040, color='#e8a838', linestyle='--', alpha=0.3)

    ax.annotate('ATR = 40', xy=(2, 5040), xytext=(3.5, 5060),
               fontproperties=font_body, fontsize=10, ha='center',
               bbox=dict(boxstyle='round', facecolor='#f0f4f8', alpha=0.8))

    ax.set_title('金字塔加仓价格坐标图（多头示例）', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
```

- [ ] **Step 6: 生成所有图表**

```bash
cd "c:/Users/dell/Desktop/Vue" && python -c "
from backend.scripts.generate_strategy_pdf.charts.radar_chart import create_radar_chart
from backend.scripts.generate_strategy_pdf.charts.mapping_curve import create_mapping_curve
from backend.scripts.generate_strategy_pdf.charts.equity_curve import create_equity_curve
from backend.scripts.generate_strategy_pdf.charts.heatmap import create_heatmap
from backend.scripts.generate_strategy_pdf.charts.flow_diagrams import (
    create_architecture_diagram, create_timeline_diagram,
    create_signal_state_diagram, create_stop_loss_diagram,
    create_price_diagram
)
import os
out = 'backend/scripts/generate_strategy_pdf/charts'
os.makedirs(out, exist_ok=True)

# Suppress font warnings
import logging
logging.getLogger('matplotlib').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.ERROR)

create_radar_chart(f'{out}/radar.png')
create_mapping_curve(f'{out}/mapping_curve.png')
create_equity_curve(f'{out}/equity_curve.png')
create_heatmap(f'{out}/heatmap.png')
create_architecture_diagram(f'{out}/architecture.png')
create_timeline_diagram(f'{out}/timeline.png')
create_signal_state_diagram(f'{out}/signal_state.png')
create_stop_loss_diagram(f'{out}/stop_loss.png')
create_price_diagram(f'{out}/price_diagram.png')
print('All charts generated successfully!')
" 2>&1
```

---

### Task 3: 主 PDF 生成脚本

**Files:**
- Create: `backend/scripts/generate_strategy_pdf/generate_pdf.py`
- Create: `backend/scripts/generate_strategy_pdf/sections/__init__.py`
- Create: `backend/scripts/generate_strategy_pdf/sections/volume1.py`
- Create: `backend/scripts/generate_strategy_pdf/sections/volume2.py`
- Create: `backend/scripts/generate_strategy_pdf/sections/volume3.py`

This is the largest task. Each volume file builds a list of reportlab Flowables (Paragraphs, Tables, Images, PageBreaks).

- [ ] **Step 1: 编写 volume1.py** — 第1-3章（约18页）

包括：执行摘要、核心参数表、架构图、时间线、五大策略对比表、雷达图、评分表、互补矩阵、选择指南

- [ ] **Step 2: 编写 volume2.py** — 第4-8章（约30页）

包括：V2全流程、V3差异、趋势因子公式+映射曲线、止损系统+双层图、信号状态图、风险矩阵

- [ ] **Step 3: 编写 volume3.py** — 第9-13章+附录（约20页）

包括：7项功能说明、三层绩效体系表、回撤曲线图、热力图、回测差异表、参数速查、操作手册、术语表

- [ ] **Step 4: 编写 generate_pdf.py 主入口**

```python
"""FT Strategy PDF Generator — Main Entry Point."""
import os
import sys
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image, ListFlowable, ListItem, KeepTogether
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from generate_strategy_pdf.styles import styles as sty
from generate_strategy_pdf.sections.volume1 import build_volume1
from generate_strategy_pdf.sections.volume2 import build_volume2
from generate_strategy_pdf.sections.volume3 import build_volume3

CHART_DIR = "charts"

class PDFGenerator:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            topMargin=20*mm,
            bottomMargin=20*mm,
            leftMargin=20*mm,
            rightMargin=20*mm,
        )
        self.story = []

    def build(self):
        # Cover page
        self._add_cover()
        # TOC
        self._add_toc()
        # Volumes
        build_volume1(self)
        build_volume2(self)
        build_volume3(self)
        # Build
        self.doc.build(self.story)

    def _add_cover(self):
        from reportlab.platypus import Spacer
        self.story.append(Spacer(1, 60*mm))
        self.story.append(Paragraph("FT 量化期货交易系统", sty['style_title']))
        self.story.append(Paragraph("完整策略文档", sty['style_title']))
        self.story.append(Spacer(1, 15*mm))
        self.story.append(Paragraph("Futures Trading Quantitative Strategy System", 
                        ParagraphStyle("SubTitle", fontName="SimSun", fontSize=12, 
                                      textColor=HexColor("#666666"), alignment=1)))
        self.story.append(Spacer(1, 30*mm))
        self.story.append(Paragraph("V2 / V3 — 海龟增强策略", sty['style_h2']))
        self.story.append(Paragraph("2026-05-14", sty['style_body']))
        self.story.append(PageBreak())

    def _add_toc(self):
        self.story.append(Paragraph("目 录", sty['style_h1']))
        toc_items = [
            "第一卷  策略顶层设计",
            "    第1章  执行摘要",
            "    第2章  五大策略全景对比",
            "    第3章  策略选择指南",
            "第二卷  策略逻辑详解",
            "    第4章  海龟增强V2交易全流程",
            "    第5章  海龟增强V3差异说明",
            "    第6章  趋势因子指标体系",
            "    第7章  止损系统设计",
            "    第8章  实盘风险分析",
            "第三卷  功能实现与运维",
            "    第9章  交易管理功能",
            "    第10章  绩效看板",
            "    第11章  K线分析",
            "    第12章  日志监控",
            "    第13章  回测系统",
            "附录A  关键参数速查表",
            "附录B  实盘操作手册",
            "附录C  术语表",
        ]
        for item in toc_items:
            indent = 0 if item.startswith("第") or item.startswith("附") else 20
            self.story.append(Paragraph(item, 
                ParagraphStyle("TOC", fontName="SimSun", fontSize=11, 
                             leftIndent=indent, spaceAfter=2*mm)))
        self.story.append(PageBreak())

    def add_heading1(self, text):
        self.story.append(Paragraph(text, sty['style_h1']))
        self.story.append(Spacer(1, 2*mm))

    def add_heading2(self, text):
        self.story.append(Paragraph(text, sty['style_h2']))
        self.story.append(Spacer(1, 1*mm))

    def add_heading3(self, text):
        self.story.append(Paragraph(text, sty['style_h3']))

    def add_body(self, text):
        self.story.append(Paragraph(text, sty['style_body']))

    def add_image(self, path, width=160*mm):
        full_path = os.path.join(os.path.dirname(__file__), CHART_DIR, path)
        if os.path.exists(full_path):
            self.story.append(Spacer(1, 3*mm))
            self.story.append(Image(full_path, width=width, height=width*0.6))
            self.story.append(Spacer(1, 3*mm))

    def add_table(self, data, col_widths=None):
        """Add a styled table."""
        from reportlab.lib import colors
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor("#1a3a5c")),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor("#ffffff")),
            ('FONTNAME', (0, 0), (-1, 0), "SimHei"),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), "SimSun"),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f5f7fa")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ])
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(table_style)
        self.story.append(Spacer(1, 2*mm))
        self.story.append(t)
        self.story.append(Spacer(1, 3*mm))


if __name__ == "__main__":
    output = os.path.join(os.path.dirname(__file__), "output", "FT策略文档-完整版.pdf")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    gen = PDFGenerator(output)
    gen.build()
    print(f"PDF generated: {output}")
```

---

### Task 4: 生成 PDF

- [ ] **Step 1: 先验证所有图表可生成**

```bash
cd "c:/Users/dell/Desktop/Vue" && python -c "
from backend.scripts.generate_strategy_pdf.charts import *
import logging
logging.getLogger('matplotlib').setLevel(logging.ERROR)
# Run chart generation
from backend.scripts.generate_strategy_pdf.charts.radar_chart import create_radar_chart
from backend.scripts.generate_strategy_pdf.charts.mapping_curve import create_mapping_curve
from backend.scripts.generate_strategy_pdf.charts.equity_curve import create_equity_curve
from backend.scripts.generate_strategy_pdf.charts.heatmap import create_heatmap
from backend.scripts.generate_strategy_pdf.charts.flow_diagrams import create_architecture_diagram, create_timeline_diagram, create_signal_state_diagram, create_stop_loss_diagram, create_price_diagram
from backend.scripts.generate_strategy_pdf.charts.flow_diagrams import create_architecture_diagram, create_timeline_diagram, create_signal_state_diagram, create_stop_loss_diagram, create_price_diagram
out = 'backend/scripts/generate_strategy_pdf/charts'
create_radar_chart(f'{out}/radar.png')
create_mapping_curve(f'{out}/mapping_curve.png')
create_equity_curve(f'{out}/equity_curve.png')
create_heatmap(f'{out}/heatmap.png')
create_architecture_diagram(f'{out}/architecture.png')
create_timeline_diagram(f'{out}/timeline.png')
create_signal_state_diagram(f'{out}/signal_state.png')
create_stop_loss_diagram(f'{out}/stop_loss.png')
create_price_diagram(f'{out}/price_diagram.png')
print('All charts OK')
" 2>&1
```

- [ ] **Step 2: 运行完整 PDF 生成**

```bash
cd "c:/Users/dell/Desktop/Vue" && python backend/scripts/generate_strategy_pdf/generate_pdf.py 2>&1
```

- [ ] **Step 3: 验证 PDF 输出**

```bash
cd "c:/Users/dell/Desktop/Vue" && python -c "
from pypdf import PdfReader
r = PdfReader('backend/scripts/generate_strategy_pdf/output/FT策略文档-完整版.pdf')
print(f'Pages: {len(r.pages)}')
print(f'Title: {r.metadata.title}')
# Print first few chars of each page
for i, p in enumerate(r.pages[:5]):
    text = p.extract_text()[:100]
    print(f'Page {i+1}: {text[:60]}...')
" 2>&1
```

---

### Task 5: 最终调整

- [ ] **Step 1: 检查 PDF 页面完整性和渲染问题**

```bash
cd "c:/Users/dell/Desktop/Vue" && python -c "
from pypdf import PdfReader
r = PdfReader('backend/scripts/generate_strategy_pdf/output/FT策略文档-完整版.pdf')
print(f'Total pages: {len(r.pages)}')
print(f'File size: {__import__(\"os\").path.getsize(\"backend/scripts/generate_strategy_pdf/output/FT策略文档-完整版.pdf\") / 1024:.0f} KB')
" 2>&1
```

- [ ] **Step 2: 修复报告中的任何渲染问题，重新生成**
- [ ] **Step 3: 输出最终 PDF 路径**
