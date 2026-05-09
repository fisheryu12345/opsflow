"""
历史数据加载工具 — 用于回测。

用法：
    from stock.backtest.data_loader import load_daily_data, build_daily_timeline

    df = load_daily_data("rb")                          # 自动加载最新主连 CSV
    timeline = build_daily_timeline("rb")                # 含 active_contract, is_rollover_date
"""
import os
import glob
import pandas as pd
import numpy as np
from stock.backtest.indicators import calculate_atr


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def list_available_data() -> list[dict]:
    """列出 data/ 目录下所有可用的已下载数据文件。"""
    records = []
    for fpath in sorted(glob.glob(os.path.join(DATA_DIR, "*_daily_*.csv"))):
        fname = os.path.basename(fpath)
        # 解析文件名: rb_main_daily_20190101_20260509.csv
        parts = fname.replace(".csv", "").split("_")
        size_kb = os.path.getsize(fpath) / 1024
        records.append({
            "file": fname,
            "path": fpath,
            "product": parts[0],
            "start": parts[3] if len(parts) >= 4 else "?",
            "end": parts[4] if len(parts) >= 5 else "?",
            "size_kb": f"{size_kb:.1f} KB",
        })
    return records


def load_daily_data(product: str, start: str = None, end: str = None) -> pd.DataFrame:
    """加载指定品种的日K线 CSV（主连续合约）。

    Args:
        product: 品种代码，如 'rb', 'hc', 'i'
        start:   起始日期，如 '2020-01-01' (None = 不限制)
        end:     截止日期，如 '2024-12-31' (None = 不限制)

    Returns:
        包含 datetime, open, high, low, close, volume, open_oi 的 DataFrame
    """
    pattern = os.path.join(DATA_DIR, f"{product}_main_daily_*.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"[ERROR] 未找到 {product} 的数据文件。\n"
            f"        请先运行: python -m stock.backtest.download_data"
        )

    # 加载最新的文件
    fpath = files[-1]
    print(f"[INFO] 加载主连数据: {os.path.basename(fpath)}")

    df = pd.read_csv(fpath, encoding='utf-8-sig')
    df['datetime'] = pd.to_datetime(df['datetime'])

    # 日期过滤
    if start:
        df = df[df['datetime'] >= pd.Timestamp(start)]
    if end:
        df = df[df['datetime'] <= pd.Timestamp(end)]

    df = df.sort_values('datetime').reset_index(drop=True)
    return df


def load_multiple(symbols: list[str], start: str = None, end: str = None) -> dict[str, pd.DataFrame]:
    """批量加载多个品种的数据。

    Returns:
        {product_code: DataFrame} 的字典
    """
    return {sym: load_daily_data(sym, start, end) for sym in symbols}


# ── 新增：个体合约加载 + 时间线构建 ──


def load_individual_contracts(product: str) -> dict[str, pd.DataFrame]:
    """加载指定品种的所有个体合约 CSV。

    文件命名约定: {product}{yy}{mm}_daily_*.csv，如 rb1905_daily_20190102_20190515.csv

    Returns:
        {contract_code: DataFrame} 字典。
        contract_code 如 'rb1905', 'rb1910'，不包含路径。
    """
    pattern = os.path.join(DATA_DIR, f"{product}[0-9][0-9][0-9][0-9]_daily_*.csv")
    files = sorted(glob.glob(pattern))

    contracts = {}
    for fpath in files:
        fname = os.path.basename(fpath)
        # 提取合约代码: "rb1905_daily_..." -> "rb1905"
        code = fname.split('_')[0]
        df = pd.read_csv(fpath, encoding='utf-8-sig')
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        contracts[code] = df

    return contracts


# ── 新增：连续合约跳空检测 ──


def _compute_rollover_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """检测主力连续合约中的移仓换月跳空。

    当开盘价相对前日收盘的跳空超过 3× ATR 时，标记为移仓跳空。
    添加 rollover_gap 列（跳空幅度，正常日为 0）。

    Returns:
        带 rollover_gap 列的 DataFrame
    """
    if len(df) < 20:
        df['rollover_gap'] = 0.0
        return df

    prev_close = df['close'].shift(1)
    gap = df['open'] - prev_close  # 开盘跳空

    atr_series = calculate_atr(df, 20)
    threshold = 3.0 * atr_series
    is_rollover = (abs(gap) > threshold) & (atr_series > 0)

    df['rollover_gap'] = gap.where(is_rollover, 0.0).fillna(0.0)
    return df


def build_daily_timeline(product: str, start: str = None, end: str = None) -> pd.DataFrame:
    """构建含主力合约标识和移仓日期的每日时间线。

    使用 open_oi 启发式方法确定每日活跃合约：
    - 加载所有个体合约
    - 对每个日期，取 open_oi 最大的合约作为 active_contract
    - 当 active_contract 在相邻日期发生变化时标记 is_rollover_date=True

    将 active_contract 信息合并到主连合约的 K 线数据中。

    Returns:
        DataFrame: datetime, open, high, low, close, volume, open_oi,
                   active_contract, is_rollover_date
    """
    # 1. 加载主连合约（价格数据源）
    main_df = load_daily_data(product, start, end)

    # 2. 加载个体合约（用于确定活跃合约）
    contracts = load_individual_contracts(product)
    if not contracts:
        print("[WARN] 无个体合约数据，将使用产品代码作为活跃合约")
        main_df['active_contract'] = product.upper()
        main_df['is_rollover_date'] = False
        main_df = _compute_rollover_gaps(main_df)
        return main_df

    # 3. 构建 OI 时间线：对每个日期找到 open_oi 最大的合约
    print(f"[INFO] 构建 OI 时间线: {len(contracts)} 个合约")
    oi_parts = []
    for code, df in contracts.items():
        d = df[['datetime', 'open_oi']].copy()
        d['contract'] = code
        oi_parts.append(d)

    all_oi = pd.concat(oi_parts, ignore_index=True)
    all_oi = all_oi.dropna(subset=['open_oi'])

    # 每个日期取 open_oi 最大的合约
    idx = all_oi.groupby('datetime')['open_oi'].idxmax()
    active_map = all_oi.loc[idx, ['datetime', 'contract']].set_index('datetime')['contract']

    # 4. 合并到主连时间线
    main_df = main_df.merge(
        active_map.to_frame('active_contract'),
        on='datetime',
        how='left',
    )
    # 前填：数据起始段可能没有个体合约覆盖
    main_df['active_contract'] = main_df['active_contract'].ffill().bfill()

    # 5. 检测移仓日期
    main_df['_prev_contract'] = main_df['active_contract'].shift(1)
    main_df['is_rollover_date'] = (
        (main_df['active_contract'] != main_df['_prev_contract'])
        & main_df['_prev_contract'].notna()
    )
    main_df = main_df.drop(columns=['_prev_contract'])

    rollover_count = main_df['is_rollover_date'].sum()
    print(f"[INFO] 检测到 {rollover_count} 个移仓日期")

    main_df = _compute_rollover_gaps(main_df)
    return main_df
