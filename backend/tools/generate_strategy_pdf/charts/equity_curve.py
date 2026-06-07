"""Equity/drawdown curve simulation."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_BODY = r"C:\Windows\Fonts\simsun.ttc"


def create_equity_curve(output_path: str):
    """Simulate equity curve with drawdown shading."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    np.random.seed(42)
    days = 250
    # More realistic equity curve with trends
    t = np.arange(days)
    trend = np.cumsum(np.random.normal(0.0005, 0.008, days))
    noise = np.random.normal(0, 0.005, days)
    returns = trend * 0.3 + noise * 0.7 + 0.001
    equity = 1000000 * np.cumprod(1 + returns / 100)
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
    ax2.set_ylim(bottom=min(drawdown) * 1.2, top=0)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Equity curve saved to {output_path}")
