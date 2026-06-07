"""Five-strategy comparison radar chart."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_BODY = r"C:\Windows\Fonts\simsun.ttc"


def create_radar_chart(output_path: str):
    """Create radar chart comparing 5 strategies across 5 dimensions."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_val = FontProperties(fname=FONT_BODY, size=8)

    categories = ['趋势市收益', '震荡市防御', '回撤控制', '风控可控', '国内适配']
    N = len(categories)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    strategies = {
        '海龟原版': [9, 2, 5, 7, 4],
        'MA10斜率排名': [7, 4, 7, 8, 8],
        '双均线交叉':   [5, 2, 3, 2, 3],
        '海龟增强V2':   [9, 4, 7, 8, 7],
        '海龟增强V3':   [8, 6, 8, 8, 7],
    }
    colors = ['#8B0000', '#2E8B57', '#DAA520', '#1a3a5c', '#2d6da8']

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for i, (name, values) in enumerate(strategies.items()):
        values_plot = values + values[:1]
        ax.plot(angles, values_plot, 'o-', linewidth=2, color=colors[i], label=name)
        ax.fill(angles, values_plot, alpha=0.05, color=colors[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontproperties=FontProperties(fname=FONT_BODY, size=11))
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(['2', '4', '6', '8', '10'], fontproperties=font_val)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.15), prop=font_cn, fontsize=10)
    ax.set_title('五大策略综合能力雷达图', fontproperties=font_cn, fontsize=16, pad=25, fontweight='bold')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Radar chart saved to {output_path}")
