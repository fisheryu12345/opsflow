"""
品种交易所映射与元数据 —— 多品种回测基础配置。

用法：
    from stock.backtest.product_data import get_product, tqsdk_symbol

    info = get_product('rb')
    sym = tqsdk_symbol('MA')  # -> 'KQ.m@CZCE.MA'
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductInfo:
    code: str                     # 内部代码（如 'rb', 'MA', 'si'）
    exchange: str                 # 交易所代码（SHFE / CZCE / DCE / GFEX）
    name: str                     # 中文品名
    volume_multiple: int          # 合约乘数（吨/手）
    price_tick: float             # 最小变动价位
    listing_date: Optional[str]   # 上市日期 'YYYY-MM-DD'；None 表示 2019 以前已上市
    risk_base: float = 4000       # 每单位风险金额
    risk_multiplier: int = 2
    max_units: int = 3


PRODUCTS = [
    # ── SHFE（上海期货交易所）──
    ProductInfo('rb', 'SHFE', '螺纹钢',    10, 1.0,  None),
    ProductInfo('hc', 'SHFE', '热轧卷板',   10, 1.0,  None),
    ProductInfo('al', 'SHFE', '铝',         5,  5.0,  None),
    ProductInfo('fu', 'SHFE', '燃料油',     10, 1.0,  None),
    ProductInfo('ru', 'SHFE', '天然橡胶',   10, 5.0,  None),
    ProductInfo('sp', 'SHFE', '纸浆',       10, 2.0,  None),
    ProductInfo('ag', 'SHFE', '白银',       15, 1.0,  None),

    # ── CZCE（郑州商品交易所）──
    ProductInfo('MA', 'CZCE', '甲醇',       10, 1.0,  None),
    ProductInfo('TA', 'CZCE', '精对苯二甲酸', 5, 2.0,  None),
    ProductInfo('SA', 'CZCE', '纯碱',       20, 1.0,  '2019-12-06'),
    ProductInfo('FG', 'CZCE', '玻璃',       20, 1.0,  None),
    ProductInfo('UR', 'CZCE', '尿素',       20, 1.0,  '2019-08-09'),
    ProductInfo('CF', 'CZCE', '棉花',        5, 5.0,  None),
    # ProductInfo('RM', 'CZCE', '菜粕',       10, 1.0,  None),
    ProductInfo('AP', 'CZCE', '苹果',       10, 1.0,  None),
    ProductInfo('SR', 'CZCE', '白糖',       10, 1.0,  None),

    # ── DCE（大连商品交易所）──
    ProductInfo('m',  'DCE', '豆粕',        10, 1.0,  None),
    ProductInfo('p',  'DCE', '棕榈油',      10, 2.0,  None),
    ProductInfo('jd', 'DCE', '鸡蛋',         5, 1.0,  None),
    ProductInfo('lh', 'DCE', '生猪',        16, 1.0,  '2021-01-08'),

    # ── GFEX（广州期货交易所）──
    ProductInfo('si', 'GFEX', '工业硅',      5, 5.0,  '2022-12-22'),
]


PRODUCT_MAP = {p.code: p for p in PRODUCTS}


def get_product(code: str) -> ProductInfo:
    """按代码查询品种信息。"""
    if code not in PRODUCT_MAP:
        raise KeyError(f"未知品种: {code}，可选: {list(PRODUCT_MAP.keys())}")
    return PRODUCT_MAP[code]


def tqsdk_symbol(code: str) -> str:
    """获取 TqSDK 主力连续合约代码（KQ.m@{交易所}.{品种}）。"""
    p = get_product(code)
    return f"KQ.m@{p.exchange}.{code}"
