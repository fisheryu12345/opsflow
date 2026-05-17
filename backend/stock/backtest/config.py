"""
Backtest configuration dataclass.
Mirrors strategy params from core.config_loader DEFAULTS + backtest-specific settings.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BacktestConfig:
    # ── Strategy params (mirrors core.config_loader DEFAULTS) ──
    risk_base_amount: float = 4000
    risk_multiplier: int = 2
    max_units: int = 3
    protect_cost_ratio: float = 2.5       # PROTECT_COST_ENABLED_RATIO
    gap_protection_ratio: float = 1.5     # GAP_PROTECTION_RATIO
    gap_atr_limit: float = 2.0           # GAP_ATR_LIMIT (ATR倍数)
    trend_factor_max: float = 0.5          # TREND_FACTOR_MAX

    # ── Backtest-specific ──
    initial_capital: float = 1_000_000
    volume_multiple: int = 10
    price_tick: float = 1.0
    slippage: float = 1.0                 # 1 tick slippage per trade
    output_dir: str = "./backtest_results"

    # ── Product (overridden at construction from product_data / CLI args) ──
    product: str = ""
    start_year: int = 2019
    end_year: int = 2026
    entry_period: int = 20                 # Donchian breakout period
    atr_period: int = 20
    ma_periods: tuple = (10, 20, 40)       # MA filter periods
