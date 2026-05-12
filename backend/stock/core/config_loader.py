"""
Centralized config loader — reads from DB (StrategyConfig) with fallback to hardcoded defaults.
now all callers use get_config() from this module.
"""

DEFAULTS = {
    'POSITION_RISK_BASE_AMOUNT': 4000,
    'POSITION_RISK_MULTIPLIER': 2,
    'POSITION_MAX_UNITS': 3,
    'TIMEOUT_SECONDS': 60,
    'PROTECT_COST_ENABLED_RATIO': 2.5,
    'GAP_PROTECTION_RATIO': 1.5,
    'TREND_GAP_LIMIT': 0.03,
    'TREND_FACTOR_MAX': 0.5,
    'TREND_LABEL_STRONG_RATIO': 0.80,
    'TREND_LABEL_WEAK_RATIO': 0.30,
    'TQAPI_ACCOUNT': 'yupei1986',
    'TQAPI_PASSWORD': 'yupei1986',
}

# Map config names → StrategyConfig model field names
FIELD_MAP = {
    'POSITION_RISK_BASE_AMOUNT': 'risk_per_unit',
    'POSITION_RISK_MULTIPLIER': 'position_risk_multiplier',
    'POSITION_MAX_UNITS': 'max_units',
    'TIMEOUT_SECONDS': 'timeout_seconds',
    'PROTECT_COST_ENABLED_RATIO': 'protect_cost_enabled_ratio',
    'GAP_PROTECTION_RATIO': 'gap_threshold',
    'TREND_GAP_LIMIT': 'trend_gap_limit',
    'TREND_FACTOR_MAX': 'trend_factor_max',
    'TREND_LABEL_STRONG_RATIO': 'trend_label_strong_ratio',
    'TREND_LABEL_WEAK_RATIO': 'trend_label_weak_ratio',
    'TQAPI_ACCOUNT': 'tqapi_account',
    'TQAPI_PASSWORD': 'tqapi_password',
}


def _load_config(account_id=None):
    """
    Load StrategyConfig from DB.

    If account_id is given, load that account's config (OneToOne).
    Otherwise fall back to the first available config.
    """
    try:
        from stock.models import StrategyConfig
        if account_id:
            config = StrategyConfig.objects.filter(account_id=account_id).first()
        else:
            config = StrategyConfig.objects.first()
        if config is None:
            return dict(DEFAULTS)
    except Exception:
        return dict(DEFAULTS)

    result = {}
    for param_name, field_name in FIELD_MAP.items():
        raw = getattr(config, field_name, None)
        if raw is None or raw == '':
            result[param_name] = DEFAULTS[param_name]
        else:
            result[param_name] = _convert(param_name, raw)
    return result


def _convert(key, value):
    """Convert DB field value to the expected Python type."""
    from decimal import Decimal

    target_type = _expected_type(key)

    if target_type is list:
        if isinstance(value, str):
            return [v.strip() for v in value.split(',') if v.strip()]
        return list(value)

    if target_type is float and isinstance(value, Decimal):
        return float(value)

    if target_type is int:
        return int(value)

    if target_type is str:
        return str(value)

    return value


def _expected_type(key):
    """Return the expected Python type for each config key."""
    type_map = {
        'POSITION_RISK_BASE_AMOUNT': float,
        'POSITION_RISK_MULTIPLIER': int,
        'POSITION_MAX_UNITS': int,
        'TIMEOUT_SECONDS': int,
        'PROTECT_COST_ENABLED_RATIO': float,
        'GAP_PROTECTION_RATIO': float,
        'TREND_GAP_LIMIT': float,
        'TREND_FACTOR_MAX': float,
        'TREND_LABEL_STRONG_RATIO': float,
        'TREND_LABEL_WEAK_RATIO': float,
        'TQAPI_ACCOUNT': str,
        'TQAPI_PASSWORD': str,
    }
    return type_map.get(key, str)


def get_config(key, account_id=None):
    """
    Get a single config value by key.

    If account_id is given, return that account's config; otherwise the default.
    """
    return _load_config(account_id)[key]
