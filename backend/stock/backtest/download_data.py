"""
下载期货日K线数据：主连续合约 + 各月份合约（用于移仓换月分析）。

数据文件：
  data/rb_main_daily_*.csv          — 主连连续合约 (KQ.m@SHFE.rb，自动拼接)
  data/rb_YYMM_daily_*.csv           — 各月份合约（如 rb2405, rb2410 ...）

用法：
    python -m stock.backtest.download_data
"""
import os
import sys
import time
import pandas as pd

# Windows GBK 终端兼容：保证 Unicode 能正常输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from tqsdk import TqApi, TqAuth

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
START_YEAR = 2019
WAIT_SEC = 20  # wait_update 超时秒数


# ── 工具函数 ──────────────────────────────────────────

def _cols(df):
    """保留标准 K 线列。"""
    keep = [c for c in ['datetime', 'open', 'high', 'low', 'close', 'volume', 'open_oi'] if c in df.columns]
    return df[keep]


def _clean(df):
    """datetime 列纳秒→上海时间，去空，排序去重。"""
    ts = pd.to_numeric(df['datetime'], errors='coerce')
    df['datetime'] = pd.to_datetime(ts, unit='ns', utc=True, errors='coerce').dt.tz_convert('Asia/Shanghai').dt.tz_localize(None)
    df = df.dropna(subset=['datetime'])
    df = df[df['datetime'].dt.year >= START_YEAR]
    df = df.sort_values('datetime').drop_duplicates(subset=['datetime']).reset_index(drop=True)
    for c in ['open', 'high', 'low', 'close']:
        if c in df.columns:
            df[c] = df[c].round(2)
    return df


def _save(df, filename):
    """保存 CSV。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False, encoding='utf-8-sig', float_format='%.2f')
    size = os.path.getsize(path) / 1024
    print(f"  [OK] {filename}  ({len(df)}条, {size:.1f}KB)")
    return path


def _fetch_kline(api, symbol, max_bars=3000):
    """获取 K 线，等待异步加载完成。"""
    klines = api.get_kline_serial(symbol, duration_seconds=86400, data_length=max_bars)
    api.wait_update(deadline=time.time() + WAIT_SEC)
    time.sleep(0.3)
    api.wait_update(deadline=time.time() + 5)
    return klines.copy() if len(klines) else pd.DataFrame()


# ── 1. 下载主连合约 ──────────────────────────────────

def download_main_contract(api):
    """下载 KQ.m@SHFE.rb 主连续合约。"""
    print("\n═══ 主连续合约 ═══")
    df = _clean(_cols(_fetch_kline(api, "KQ.m@SHFE.rb")))
    if len(df):
        s = df['datetime'].iloc[0].strftime('%Y%m%d')
        e = df['datetime'].iloc[-1].strftime('%Y%m%d')
        _save(df, f"rb_main_daily_{s}_{e}.csv")
    return df


# ── 2. 发现可下载的合约代码 ──────────────────────────

def discover_contracts(api) -> list[str]:
    """发现所有可获取数据的螺纹钢合约代码。"""
    all_quotes = api.query_quotes()
    hot = sorted({q for q in all_quotes if q.startswith('SHFE.rb') and len(q) < 15})
    # 补充已退市但仍可能有历史数据的旧合约（每月份覆盖）
    years = ['19', '20', '21', '22', '23']
    months = ['01', '05', '10']
    cold = [f"SHFE.rb{t}{m}" for t in years for m in months]
    codes = sorted(set(hot + cold))
    print(f"  [query_quotes] {len(hot)} 个热合约 + {len(codes)-len(hot)} 个冷合约 = {len(codes)}")
    return codes


def download_individual_contracts(api, codes: list[str]):
    """批量下载各月份合约的日K线。

    先一次性订阅所有合约的 K 线（data_length=2500 覆盖 2019-2026 全区间），
    然后单次 wait_update 等待所有数据异步加载完成，最后统一读取保存。

    这样从逐个等待（85合约 × 25秒 ≈ 35分钟）变为一次等待（约 30-60秒）。
    """
    print(f"\n═══ 各月份合约 ═══")

    # 批量订阅所有合约的 K 线（2019-2026 约需 1800 条，取 2500 保险）
    print("  [批量订阅] 一次性订阅所有合约...")
    kline_refs = {}
    for code in codes:
        kline_refs[code] = api.get_kline_serial(code, duration_seconds=86400, data_length=2500)

    # 单次长等待：让所有 K 线数据异步加载完成
    print("  [等待加载] 等待所有合约数据加载（约 60 秒）...")
    for _ in range(12):  # 12 × 10s = 120s 最大等待
        api.wait_update(deadline=time.time() + 10)
        # 检查是否所有合约都有数据了
        all_ready = all(len(v) > 0 for v in kline_refs.values())
        if all_ready:
            print("  [完成] 所有合约数据已就绪")
            break
    time.sleep(1)
    api.wait_update(deadline=time.time() + 5)  # 最后一次刷新

    # 统一读取保存
    results = {}
    for i, code in enumerate(codes, 1):
        short = code.split('.')[1].lower()
        raw = kline_refs[code]
        if len(raw) == 0:
            continue
        df = _clean(_cols(raw.copy()))
        if len(df) == 0:
            continue
        s = df['datetime'].iloc[0].strftime('%Y%m%d')
        e = df['datetime'].iloc[-1].strftime('%Y%m%d')
        _save(df, f"{short}_daily_{s}_{e}.csv")
        results[short] = {
            "start": df['datetime'].iloc[0],
            "end": df['datetime'].iloc[-1],
            "bars": len(df),
            "last_close": df['close'].iloc[-1],
        }
        if i % 10 == 0:
            print(f"  ... 进度: {i}/{len(codes)}")

    print(f"  [总计] 成功下载 {len(results)}/{len(codes)} 个合约")
    return results


# ── 4. 生成移仓参考信息 ──────────────────────────────

def build_rollover_reference(main_df: pd.DataFrame, contract_info: dict):
    """基于各合约数据，推断主力合约切换时间点。

    检测逻辑：沿着时间轴看哪个合约的成交量 / 持仓量最大。
    简化版：基于各合约数据的时间区间重叠关系做近似推断。
    """
    print("\n═══ 移仓换月参考 ═══")

    # 按合约到期日排序
    sorted_contracts = sorted(contract_info.items(), key=lambda x: x[1]['end'])
    rows = []
    for i, (code, info) in enumerate(sorted_contracts):
        expiry = info['end'].strftime('%Y-%m-%d')
        # 前一个合约的结束日作为可能的切换开始
        prev_end = sorted_contracts[i-1][1]['end'].strftime('%Y-%m-%d') if i > 0 else "-"
        # 该合约活跃天数
        active_days = f"{info['bars']} 天"
        rows.append({
            "合约": code,
            "数据起始": info['start'].strftime('%Y-%m-%d'),
            "数据结束": expiry,
            "活跃天数": active_days,
            "末期收盘价": info['last_close'],
            "前主力结束": prev_end,
        })

    ref_df = pd.DataFrame(rows)
    path = os.path.join(DATA_DIR, "rollover_reference.csv")
    ref_df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f"  [OK] rollover_reference.csv  ({len(ref_df)} 条)")
    return ref_df


# ── 主函数 ────────────────────────────────────────────

def main():
    print(f"[INFO] 数据目录: {DATA_DIR}")

    api = TqApi(auth=TqAuth("yupei1986", "yupei1986"))
    try:
        # 1. 主连合约
        main_df = download_main_contract(api)
        print(f"       范围: {main_df['datetime'].iloc[0]} → {main_df['datetime'].iloc[-1]}")

        # 2. 各月份合约
        codes = discover_contracts(api)
        contract_info = download_individual_contracts(api, codes)
        print(f"       共下载 {len(contract_info)} 个合约")

        # 3. 移仓参考
        build_rollover_reference(main_df, contract_info)

    finally:
        api.close()

    print(f"\n[INFO] 完成。数据目录: {DATA_DIR}")


if __name__ == "__main__":
    main()
