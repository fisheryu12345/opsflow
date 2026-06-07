"""Trend factor mapping curve."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_BODY = r"C:\Windows\Fonts\simsun.ttc"


def create_mapping_curve(output_path: str):
    """Plot trend_strength -> trend_factor and stop_multiplier."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    gap_limit = 0.03
    factor_max = 0.5
    base_stop = 2.0

    gaps = np.linspace(0, 0.05, 100)
    strengths = np.minimum(gaps / gap_limit, 1.0)
    factors = np.round(strengths * factor_max, 3)
    multipliers = base_stop * (1 + factors)

    fig, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(gaps * 100, factors, 'b-', linewidth=2.5, label='trend_factor (左轴)')
    ax1.set_xlabel('均线间距 (%)', fontproperties=font_body, fontsize=11)
    ax1.set_ylabel('trend_factor', color='b', fontproperties=font_body, fontsize=11)
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_ylim(0, 0.6)

    ax2 = ax1.twinx()
    ax2.plot(gaps * 100, multipliers, 'r--', linewidth=2.5, label='止损倍数 ATR (右轴)')
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
    ax1.set_xlim(0, 5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Mapping curve saved to {output_path}")
