"""Calendar heatmap of daily returns."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap

FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"
FONT_BODY = r"C:\Windows\Fonts\simsun.ttc"


def create_heatmap(output_path: str):
    """Generate calendar heatmap of daily returns."""
    font_cn = FontProperties(fname=FONT_PATH)
    font_body = FontProperties(fname=FONT_BODY)

    np.random.seed(123)
    dates = pd.date_range('2025-01-01', '2025-12-31', freq='B')
    returns = np.random.normal(0.05, 0.5, len(dates))

    df = pd.DataFrame({'date': dates, 'return': returns})
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day

    pivot = df.pivot_table(values='return', index='day', columns='month', aggfunc='mean')

    cmap = LinearSegmentedColormap.from_list(
        'custom', [(0, 0.3, 0), (1, 1, 1), (0.5, 0, 0)], N=256
    )

    fig, ax = plt.subplots(figsize=(12, 4.5))
    im = ax.imshow(pivot.values, cmap=cmap, aspect='auto', vmin=-1, vmax=1)

    ax.set_xticks(range(12))
    ax.set_xticklabels(['1月', '2月', '3月', '4月', '5月', '6月',
                        '7月', '8月', '9月', '10月', '11月', '12月'],
                       fontproperties=font_body, fontsize=9)
    ax.set_yticks(range(0, 31, 5))
    ax.set_yticklabels(range(1, 32, 5), fontsize=7)
    ax.set_xlabel('月份', fontproperties=font_body, fontsize=10)
    ax.set_ylabel('日', fontproperties=font_body, fontsize=10)
    ax.set_title('日收益率日历热力图（模拟示例）', fontproperties=font_cn, fontsize=13, fontweight='bold')

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label('日收益率 (%)', fontproperties=font_body, fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()
    print(f"Heatmap saved to {output_path}")
