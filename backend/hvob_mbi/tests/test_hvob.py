"""
HVOB-MBI 单元测试。
核心逻辑测试（MBI、评分、Position、引擎工具函数）。
引擎集成测试需实盘环境。
"""
from decimal import Decimal
from django.test import TestCase
from hvob_mbi.mbi import score_for_symbol, mbi_to_label, get_trading_permission, calculate_mbi
from hvob_mbi.trading_engine import Position


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

    def test_score_gap_pct_threshold(self):
        """跳空阈值 0.05%: 低于阈值视为平开"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3951, pre_close=3950,  # 跳空 0.025% < 0.05% → 维度1=0
            or_h=3960, or_l=3940,             # 重心=3950 = pre_close → 0
            last_price=3955,                   # 区间内 → 0
        )
        self.assertEqual(score, 0)

    def test_score_gap_pct_just_above(self):
        """跳空刚好超过 0.05%"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3953, pre_close=3950,  # 跳空 0.076% > 0.05% → +1
            or_h=3960, or_l=3940,             # 重心=3950 = pre_close → 0
            last_price=3955,                   # 区间内 → 0
        )
        self.assertEqual(score, 1)

    def test_score_negative_gap(self):
        """负跳空"""
        score = score_for_symbol(
            product_code='RB',
            open_price=3947, pre_close=3950,  # -0.076%
            or_h=3960, or_l=3940,             # 重心=3950 → 0
            last_price=3955,                   # 区间内 → 0
        )
        self.assertEqual(score, -1)


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

    def test_boundary_075(self):
        """> 0.75 极强多头，= 0.75 多头"""
        self.assertEqual(mbi_to_label(Decimal('0.751')), '极强多头')
        self.assertEqual(mbi_to_label(Decimal('0.75')), '多头')

    def test_boundary_065(self):
        """> 0.65 多头，= 0.65 中性"""
        self.assertEqual(mbi_to_label(Decimal('0.651')), '多头')
        self.assertEqual(mbi_to_label(Decimal('0.65')), '中性')

    def test_boundary_045(self):
        """> 0.45 中性，= 0.45 空头"""
        self.assertEqual(mbi_to_label(Decimal('0.451')), '中性')
        self.assertEqual(mbi_to_label(Decimal('0.45')), '空头')

    def test_boundary_035(self):
        """> 0.35 空头，= 0.35 极强空头"""
        self.assertEqual(mbi_to_label(Decimal('0.351')), '空头')
        self.assertEqual(mbi_to_label(Decimal('0.35')), '极强空头')


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

    def test_boundary_075_long(self):
        """极强多头边界: >0.75 正常, 0.75 也正常"""
        self.assertEqual(get_trading_permission(Decimal('0.751'), 1), 1.0)
        self.assertEqual(get_trading_permission(Decimal('0.75'), 1), 1.0)

    def test_boundary_075_short(self):
        """极强多头边界: >0.75 禁止, 0.75 半仓"""
        self.assertEqual(get_trading_permission(Decimal('0.751'), -1), 0.0)
        self.assertEqual(get_trading_permission(Decimal('0.75'), -1), 0.5)

    def test_boundary_065_long(self):
        """多头边界: =0.65 正常（震荡）"""
        self.assertEqual(get_trading_permission(Decimal('0.65'), 1), 1.0)

    def test_boundary_045_short(self):
        """震荡/空头边界: =0.45 空头"""
        self.assertEqual(get_trading_permission(Decimal('0.45'), -1), 1.0)

    def test_boundary_035_long(self):
        """空头/极强空头边界: =0.35 禁止"""
        self.assertEqual(get_trading_permission(Decimal('0.35'), 1), 0.0)


class PositionInitTests(TestCase):
    """Position 类初始化与止损计算"""

    def test_long_stop_loss(self):
        """多单止损 = or_l - 0.2 * or_r"""
        pos = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
        expected_stop = Decimal('3980') - Decimal('0.2') * Decimal('40')  # 3972
        self.assertEqual(pos.stop_loss, expected_stop)

    def test_short_stop_loss(self):
        """空单止损 = or_h + 0.2 * or_r"""
        pos = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
        expected_stop = Decimal('4020') + Decimal('0.2') * Decimal('40')  # 4028
        self.assertEqual(pos.stop_loss, expected_stop)

    def test_breakeven_trigger_long(self):
        """多单保本触发价 = entry_price + or_r"""
        pos = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
        self.assertEqual(pos.breakeven_trigger, Decimal('4040'))

    def test_breakeven_trigger_short(self):
        """空单保本触发价 = entry_price - or_r"""
        pos = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
        self.assertEqual(pos.breakeven_trigger, Decimal('3960'))

    def test_trailing_high_init_long(self):
        """多单trailing_high初始化为开仓价"""
        pos = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
        self.assertEqual(pos.trailing_high, Decimal('4000'))

    def test_trailing_low_init_short(self):
        """空单trailing_low初始化为开仓价"""
        pos = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
        self.assertEqual(pos.trailing_low, Decimal('4000'))


class PositionTrailingTests(TestCase):
    """Position 移动止盈/保本逻辑"""

    def setUp(self):
        # 多单: entry=4000, or_h=4020, or_l=3980, or_r=40
        # stop_loss = 3980 - 8 = 3972, stop_distance = 28
        # breakeven_trigger = 4000 + 40 = 4040
        self.long_pos = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
        # 空单: stop_loss = 4020 + 8 = 4028, stop_distance = 28
        self.short_pos = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)

    def test_trailing_high_update(self):
        """多单上涨更新trailing_high"""
        self.long_pos.update_trailing(4050)
        self.assertEqual(self.long_pos.trailing_high, Decimal('4050'))

    def test_trailing_high_no_update(self):
        """多单下跌不更新trailing_high"""
        self.long_pos.update_trailing(3950)
        self.assertEqual(self.long_pos.trailing_high, Decimal('4000'))

    def test_trailing_stop_moves_long(self):
        """多单浮盈超2倍止损距离后止损上移"""
        # stop_distance = 4000 - 3972 = 28
        # 需要 price >= 4000 + 2*28 = 4056
        self.long_pos.update_trailing(4060)
        # new_stop = max(3972, 4060 - 28 = 4032) = 4032
        self.assertEqual(self.long_pos.stop_loss, Decimal('4032'))

    def test_trailing_stop_not_move_insufficient_profit(self):
        """多单浮盈不足2倍止损距离时止损不动"""
        self.long_pos.update_trailing(4050)  # 盈利50 < 2*28=56
        self.assertEqual(self.long_pos.stop_loss, Decimal('3972'))

    def test_trailing_stop_monotonic_long(self):
        """多单止损只升不降"""
        self.long_pos.update_trailing(4060)  # stop → 4032
        self.long_pos.update_trailing(4030)  # 价格回落
        self.assertEqual(self.long_pos.stop_loss, Decimal('4032'))  # 不降

    def test_trailing_low_update_short(self):
        """空单下跌更新trailing_low"""
        self.short_pos.update_trailing(3950)
        self.assertEqual(self.short_pos.trailing_low, Decimal('3950'))

    def test_trailing_stop_moves_short(self):
        """空单浮盈超2倍止损距离后止损下移"""
        # stop_distance = 4028 - 4000 = 28
        # 需要 price <= 4000 - 2*28 = 3944
        self.short_pos.update_trailing(3940)
        # new_stop = min(4028, 3940 + 28 = 3968) = 3968
        self.assertEqual(self.short_pos.stop_loss, Decimal('3968'))

    def test_breakeven_activated_long(self):
        """多单价格达到保本触发价后止损上移至开仓价"""
        # breakeven_trigger = 4040
        self.long_pos.update_trailing(4040)
        self.assertTrue(self.long_pos.breakeven_activated)
        self.assertEqual(self.long_pos.stop_loss, Decimal('4000'))

    def test_breakeven_not_activated_before_trigger(self):
        """多单未达到保本触发价时保本不激活"""
        self.long_pos.update_trailing(4039)
        self.assertFalse(self.long_pos.breakeven_activated)
        self.assertEqual(self.long_pos.stop_loss, Decimal('3972'))

    def test_breakeven_activated_short(self):
        """空单价格达到保本触发价后止损下移至开仓价"""
        # breakeven_trigger = 3960
        self.short_pos.update_trailing(3960)
        self.assertTrue(self.short_pos.breakeven_activated)
        self.assertEqual(self.short_pos.stop_loss, Decimal('4000'))

    def test_breakeven_then_trailing_long(self):
        """保本激活后继续上行触发移动止盈"""
        self.long_pos.update_trailing(4040)   # 保本: stop=4000, stop_distance 重置
        self.long_pos.update_trailing(4060)   # profit=60, new_stop_distance=4000-4000=0
        # stop_distance = 4000 - 4000 = 0, 2*0 = 0, 不触发移动止盈
        self.assertEqual(self.long_pos.stop_loss, Decimal('4000'))

    def test_breakeven_then_trailing_after_profit_long(self):
        """保本后继续大幅上涨触发移动止盈"""
        self.long_pos.update_trailing(4040)   # 保本: stop=4000
        # 保本后 entry_price=4000, stop_loss=4000, stop_distance=0
        # update_trailing 计算: stop_distance = entry_price - stop_loss = 0
        # price - entry_price >= 0 * 2 → 总是触发
        # 所以 stop_loss = max(stop_loss, price - 0) = price
        # 也就是说，保本后只要价格上涨，stop_loss 跟随移动
        self.long_pos.update_trailing(4050)
        self.assertEqual(self.long_pos.stop_loss, Decimal('4050'))
