# tools — 模块索引

> 上次自动更新: 2026-06-12

---

## `tools\generate_strategy_pdf/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Package init. |
| `content_loader.py` | Content loader - reads knowledge base markdown files. | `load_section()` — Load all markdown files from a section directory.<br>`extract_title()` — Extract first H1 or H2 from markdown.<br>`load_knowledge_base()` — Load all relevant sections from the knowledge base.<br>`md_to_paragraphs()` — Split markdown into paragraph blocks, stripping markdown syntax.<br>`extract_tables()` — Extract markdown tables as list of rows. |
| `generate_pdf.py` | FT Strategy PDF Generator — Main Entry Point. | `PDFGenerator` — Main PDF generator class. |
| `styles.py` |  | PDF styles - Chinese font registration and paragraph styles. |

## `tools\generate_strategy_pdf\charts/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Charts package. |
| `equity_curve.py` | Equity/drawdown curve simulation. | `create_equity_curve()` — Simulate equity curve with drawdown shading. |
| `flow_diagrams.py` | Flow diagrams using matplotlib patches (no graphviz needed). | `create_architecture_diagram()` — System architecture diagram.<br>`create_timeline_diagram()` — Daily trading timeline.<br>`create_signal_state_diagram()` — Signal state machine diagram.<br>`create_stop_loss_diagram()` — Stop loss dual-layer mechanism diagram.<br>`create_price_diagram()` — Pyramid add-on price diagram.<br>`create_performance_hierarchy()` — Three-layer performance hierarchy. |
| `heatmap.py` | Calendar heatmap of daily returns. | `create_heatmap()` — Generate calendar heatmap of daily returns. |
| `mapping_curve.py` | Trend factor mapping curve. | `create_mapping_curve()` — Plot trend_strength -> trend_factor and stop_multiplier. |
| `radar_chart.py` | Five-strategy comparison radar chart. | `create_radar_chart()` — Create radar chart comparing 5 strategies across 5 dimensions. |

## `tools\generate_strategy_pdf\sections/`

| 文件 | 用途 | 核心组件 |
|------|------|----------|
| `__init__.py` |  | Sections package. |
| `volume1.py` | Volume 1: Strategy Top-Level Design (Chapters 1-3). | `build_volume1()` — Build Volume 1: Executive Summary, Strategy Comparison, Selection Guide. |
| `volume2.py` | Volume 2: Strategy Logic Details (Chapters 4-8). | `build_volume2()` — Build Volume 2: V2 Flow, V3 Diff, Trend Factor, Stop Loss, Risk Analysis. |
| `volume3.py` | Volume 3: Implementation & Operations (Chapters 9-13 + Appendices). | `build_volume3()` — Build Volume 3: Features, Performance, K-line, Backtest, Appendices. |
