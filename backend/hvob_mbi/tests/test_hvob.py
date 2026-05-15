"""
HVOB-MBI 单元测试。
核心逻辑测试（MBI、评分等），引擎集成测试需实盘环境。
"""
from decimal import Decimal
from django.test import TestCase
from hvob_mbi.mbi import score_for_symbol, mbi_to_label, get_trading_permission


class MbiTests(TestCase):
    """MBI 计算逻辑测试"""

    def test_score_bullish(self):
        """所有维度看多 → +3"""
        score = score_for_symbol(
            product_code='RB',
            open_price=4000, pre_close=3950,  # 高开
            or_h=4020, or_l=3980,             # 重心 > 昨收
            last_price=4050,                   # 突破区间上沿
        )
        self.assertEqual(score, 3)

    def test_score_bearish(self):
        """所有维度看空 → -3"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3900, pre_close=3950,  # 低开
            or_h=3920, or_l=3880,             # 重心 < 昨收
            last_price=3850,                   # 跌破区间下沿
        )
        self.assertEqual(score, -3)

    def test_score_neutral(self):
        """平开 + 重心持平 + 区间内 → 0"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3950, pre_close=3950,  # 平开
            or_h=3960, or_l=3940,             # 重心 = 3950
            last_price=3950,                   # 区间内
        )
        self.assertEqual(score, 0)

    def test_score_mixed(self):
        """混合信号"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3960, pre_close=3950,  # 高开 +1
            or_h=3970, or_l=3940,             # 重心 3955 > 3950 +1
            last_price=3930,                   # 跌破下沿 -1
        )
        self.assertEqual(score, 1)  # +1 +1 -1 = +1


class MbiLabelTests(TestCase):
    """MBI 标签映射测试"""

    def test_extreme_bull(self):
        self.assertEqual(mbi_to_label(Decimal('0.80')), '极强多头')

    def test_bull(self):
        self.assertEqual(mbi_to_label(Decimal('0.70')), '多头')

    def test_neutral(self):
        self.assertEqual(mbi_to_label(Decimal('0.55')), '中性')

    def test_bear(self):
        self.assertEqual(mbi_to_label(Decimal('0.40')), '空头')

    def test_extreme_bear(self):
        self.assertEqual(mbi_to_label(Decimal('0.30')), '极强空头')


class TradingPermissionTests(TestCase):
    """MBI 交易权限测试"""

    def test_extreme_bull_long_allowed(self):
        self.assertEqual(get_trading_permission(Decimal('0.80'), 1), 1.0)

    def test_extreme_bull_short_forbidden(self):
        self.assertEqual(get_trading_permission(Decimal('0.80'), -1), 0.0)

    def test_extreme_bear_long_forbidden(self):
        self.assertEqual(get_trading_permission(Decimal('0.30'), 1), 0.0)

    def test_extreme_bear_short_allowed(self):
        self.assertEqual(get_trading_permission(Decimal('0.30'), -1), 1.0)

    def test_bear_half_long(self):
        self.assertEqual(get_trading_permission(Decimal('0.40'), 1), 0.5)

    def test_bull_half_short(self):
        self.assertEqual(get_trading_permission(Decimal('0.70'), -1), 0.5)

    def test_neutral_both(self):
        self.assertEqual(get_trading_permission(Decimal('0.55'), 1), 1.0)
        self.assertEqual(get_trading_permission(Decimal('0.55'), -1), 1.0)
