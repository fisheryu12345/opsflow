"""Flow diagrams using matplotlib patches (no graphviz needed)."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_BODY = r"C:\Windows\Fonts\simsun.ttc"


def create_architecture_diagram(output_path: str):
    """System architecture diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')

    def draw_box(x, y, w, h, text, color='#1a3a5c', fc='#e8f0fe', font_size=9):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=fc, edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, fontproperties=font_cn, fontsize=font_size,
                ha='center', va='center', color=color)

    def draw_arrow(x1, y1, x2, y2, color='#666666'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

    # Layer 1: Frontend
    draw_box(1, 6.5, 8, 1.0,
             '前端 Vue3  |  信号监控 / 持仓管理 / 绩效看板 / 合约配置', '#1a3a5c', '#e8f0fe', 9)
    # Layer 2: Django Backend - Scheduler
    draw_box(0.5, 4.2, 4, 1.8,
             'APScheduler 定时任务\n\n开盘 09:02  |  收盘 15:02\n临收盘止损 14:55', '#2d6da8', '#e8f0fe', 8)
    # Layer 2: Django Backend - API
    draw_box(5.5, 4.2, 4, 1.8,
             'Django REST Framework\n\nViewSets / CRUD / WebSocket\n邮件服务 / 三层绩效', '#2d6da8', '#e8f0fe', 8)
    # Layer 3: TqSDK
    draw_box(3, 2.5, 4, 1.0,
             'TqSDK (天勤量化)\n行情数据获取 / TargetPosTask 交易执行', '#e8a838', '#fef8e8', 8)
    # Layer 4: Exchange
    draw_box(3, 0.5, 4, 1.0,
             '国内期货交易所\nSHFE / DCE / CZCE / CFFEX / INE', '#8B0000', '#fde8e8', 8)

    # Data flow arrows
    draw_arrow(5, 6.5, 5, 6.0)  # Frontend -> API
    ax.text(5.2, 6.2, 'REST API', fontproperties=font_body, fontsize=7, color='#666',
            va='center')

    draw_arrow(2.5, 6.0, 2.5, 4.2)  # Frontend -> Scheduler (signals view)
    ax.text(2.7, 5.0, '信号/持仓', fontproperties=font_body, fontsize=7, color='#666',
            rotation=90, va='center')

    draw_arrow(5, 4.2, 5, 3.5)  # Django -> TqSDK
    ax.text(5.2, 3.8, '行情查询', fontproperties=font_body, fontsize=7, color='#666',
            va='center')

    draw_arrow(5, 2.5, 5, 1.5)  # TqSDK -> Exchange
    ax.text(5.2, 2.0, '交易指令', fontproperties=font_body, fontsize=7, color='#666',
            va='center')

    # Redis label
    draw_box(7.5, 3.0, 2.0, 0.6, 'Redis\n分布式锁', '#555555', '#f4f4f4', 7)
    draw_arrow(7.5, 3.3, 5.5, 4.2, '#aaa')

    ax.set_title('FT 量化期货交易系统 — 系统架构图', fontproperties=font_cn,
                 fontsize=15, fontweight='bold', pad=15)
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Architecture diagram saved to {output_path}")


def create_timeline_diagram(output_path: str):
    """Daily trading timeline."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(0, 24)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # Horizontal timeline
    ax.plot([1, 23], [2, 2], 'k-', linewidth=2, color='#333')

    points = [
        (9 + 2 / 60, '09:02 开盘任务', '#2d6da8',
         '执行信号队列\n开仓 / 止损 / 移仓 / 加仓'),
        (14 + 55 / 60, '14:55 临收盘止损', '#c0392b',
         '紧急风控\n实时重算止损\n市价平仓'),
        (15 + 2 / 60, '15:02 收盘计算', '#1a3a5c',
         '技术指标计算\n信号生成\n绩效更新'),
        (21 + 2 / 60, '21:02 夜盘开盘', '#2d6da8',
         '同 09:02 流程\n执行夜盘信号'),
    ]

    for x, label, color, desc in points:
        ax.plot(x, 2, 'o', color=color, markersize=14, zorder=5)
        ax.annotate(label, xy=(x, 2), xytext=(x, 2.8),
                    fontproperties=font_cn, fontsize=9, color=color,
                    ha='center', va='bottom', fontweight='bold')
        ax.annotate(desc, xy=(x, 2), xytext=(x, 0.5),
                    fontproperties=font_body, fontsize=7, color='#555',
                    ha='center', va='bottom')
        ax.plot([x, x], [0.5, 2], ':', color=color, alpha=0.3)

    ax.set_title('每日交易时间线', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Timeline diagram saved to {output_path}")


def create_signal_state_diagram(output_path: str):
    """Signal state machine diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def draw_state(x, y, text, color='#1a3a5c', fc='#e8f0fe', w=2.2, h=0.8):
        rect = mpatches.FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.1",
            facecolor=fc, edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x, y, text, fontproperties=font_cn, fontsize=10,
                ha='center', va='center', color=color, fontweight='bold')

    def draw_arrow(x1, y1, x2, y2, label='', color='#555'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
        if label:
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mid_x, mid_y + 0.25, label, fontproperties=font_body,
                    fontsize=8, ha='center', va='bottom', color='#555')

    draw_state(5, 5, 'PENDING\n待执行', '#e67e22', '#fef5e7')
    draw_state(5, 3.3, 'EXECUTING\n执行中', '#2d6da8', '#e8f0fe')
    draw_state(1.5, 1.2, 'SUCCESS\n成功', '#27ae60', '#e8f8e8')
    draw_state(5, 1.2, 'FAILED\n失败', '#c0392b', '#fde8e8')
    draw_state(8.5, 1.2, 'CANCELLED\n取消', '#95a5a6', '#f4f4f4')

    draw_arrow(5, 4.6, 5, 3.7, '开盘 pickup')
    draw_arrow(5, 2.9, 1.5, 1.6, '成交成功')
    draw_arrow(5, 2.9, 5, 1.6, '成交失败')
    draw_arrow(5, 2.9, 8.5, 1.6, '条件不满足')

    # Cross-day arrow
    ax.annotate('← 跨日保留 PENDING', xy=(5, 5), xytext=(1, 5.5),
                fontproperties=font_body, fontsize=8, color='#888',
                ha='center', va='center',
                arrowprops=dict(arrowstyle='->', color='#aaa', lw=1, ls='--'))

    ax.set_title('信号状态流转图', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Signal state diagram saved to {output_path}")


def create_stop_loss_diagram(output_path: str):
    """Stop loss dual-layer mechanism diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def draw_box(x, y, w, h, text, color='#1a3a5c', fc='#e8f0fe', fs=8):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=fc, edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, fontproperties=font_cn, fontsize=fs,
                ha='center', va='center', color=color)

    def draw_arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#555', lw=1.5))

    draw_box(1, 4.2, 8, 1.2,
             '第一层: 动态跟踪止损\n'
             '多头: highest_close - 2 x (1+factor) x ATR\n'
             '空头: lowest_close + 2 x (1+factor) x ATR\n'
             '趋势自适应: factor=0(2.0ATR) ~ factor=0.5(3.0ATR)',
             '#2d6da8', '#e8f0fe', 8)

    draw_box(1, 2.2, 8, 1.2,
             '第二层: 保本兜底\n'
             '触发: 盈利 > 2.5 x ATR -> protect_cost_enabled=True (单向永不关闭)\n'
             '保本价: 多头=成本价+tick x 1  |  空头=成本价-tick x 1',
             '#27ae60', '#e8f8e8', 8)

    draw_box(2.5, 0.5, 5, 1.2,
             '最终止损价\n'
             '多头: max(动态止损, 保本价)\n'
             '空头: min(动态止损, 保本价)',
             '#1a3a5c', '#f0f4f8', 9)

    draw_arrow(5, 4.2, 5, 3.4)
    draw_arrow(5, 2.2, 5, 1.7)

    ax.set_title('止损双层机制示意图', fontproperties=font_cn, fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Stop loss diagram saved to {output_path}")


def create_price_diagram(output_path: str):
    """Pyramid add-on price diagram."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(0, 6)
    ax.set_ylim(4960, 5080)
    ax.set_ylabel('价格', fontproperties=font_body, fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    prices = [5000, 5020, 5040]
    labels = [
        '开仓点 P0=5000\n唐奇安突破 -> ENTRY\n1 Unit',
        '+1 Unit\n涨超 0.5×ATR\nprice >= 5020\n总 Unit = 2',
        '+2 Unit 直接满仓\n涨超 1.0×ATR\nprice >= 5040\n总 Unit = 3',
    ]
    colors = ['#1a3a5c', '#2d6da8', '#e8a838']

    for i, (p, l, c) in enumerate(zip(prices, labels, colors)):
        x = i * 2 + 1
        ax.plot(x, p, 'o', color=c, markersize=15, zorder=5)
        ax.annotate(l, xy=(x, p), xytext=(x + 0.8, p + 8),
                    fontproperties=font_cn, fontsize=8, color=c,
                    ha='center', va='bottom',
                    arrowprops=dict(arrowstyle='->', color=c, lw=1.2))

    ax.axhline(y=5000, color='#1a3a5c', linestyle='--', alpha=0.3)
    ax.axhline(y=5020, color='#2d6da8', linestyle='--', alpha=0.3)
    ax.axhline(y=5040, color='#e8a838', linestyle='--', alpha=0.3)

    ax.annotate('ATR = 40', xy=(4, 5020), xytext=(4.5, 5060),
                fontproperties=font_body, fontsize=10, ha='center',
                bbox=dict(boxstyle='round', facecolor='#f0f4f8', alpha=0.8))

    ax.set_title('金字塔加仓价格坐标图（多头示例）', fontproperties=font_cn,
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Price diagram saved to {output_path}")


def create_performance_hierarchy(output_path: str):
    """Three-layer performance hierarchy."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')

    def draw_box(x, y, w, h, text, color='#1a3a5c', fc='#e8f0fe', fs=8):
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.1",
            facecolor=fc, edgecolor=color, linewidth=2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, fontproperties=font_cn, fontsize=fs,
                ha='center', va='center', color=color)

    def draw_up_arrow(x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', color='#888', lw=1.5))

    # L3 - Top
    draw_box(3, 4.5, 4, 0.8,
             'L3: AccountPerformanceSummary\n累计收益 / 最大回撤 / 卡玛比率 / 连续盈亏',
             '#1a3a5c', '#e8f0fe', 8)

    # L2 - Middle
    draw_box(1, 2.5, 8, 1.2,
             'L2: RollingPerformanceMetrics\n'
             '夏普 / 索提诺 / 波动率 / 胜率 / 盈亏比\n'
             '窗口: 20 / 60 / 120 / 250 交易日',
             '#2d6da8', '#e8f0fe', 8)

    # L1 - Bottom
    draw_box(1, 0.5, 8, 1.2,
             'L1: DailyEquitySnapshot (每日快照)\n'
             '权益 / 可用资金 / 浮动盈亏 / 保证金 / 风险度 / 日收益率',
             '#e8a838', '#fef8e8', 8)

    draw_up_arrow(5, 1.7, 5, 2.5)
    draw_up_arrow(5, 3.7, 5, 4.5)

    ax.set_title('三层绩效体系 — 数据血缘关系', fontproperties=font_cn,
                 fontsize=14, fontweight='bold')
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Performance hierarchy saved to {output_path}")
