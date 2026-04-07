from django.test import TestCase
import pandas as pd

from .turtle_strategy import (
    calculate_atr,
    calculate_breakout_levels,
    calculate_dynamic_stop,
    calculate_trend_factor,
    calculate_unit_count,
)


class TurtleStrategyTestCase(TestCase):
    def test_calculate_atr(self):
        df = pd.DataFrame(
            {
                "high": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
                "low": [9, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5, 21.5, 22.5, 23.5, 24.5, 25.5, 26.5, 27.5, 28.5],
                "close": [9.5, 10.8, 11.8, 12.8, 13.8, 14.8, 15.8, 16.8, 17.8, 18.8, 19.8, 20.8, 21.8, 22.8, 23.8, 24.8, 25.8, 26.8, 27.8, 28.8, 29.8],
            }
        )
        atr = calculate_atr(df, period=20)
        self.assertGreater(atr, 0)

    def test_calculate_trend_factor_strong_bull(self):
        info = calculate_trend_factor(110.0, 100.0, 90.0)
        self.assertEqual(info.factor, 0.5)
        self.assertEqual(info.label, "strong_bull")

    def test_calculate_trend_factor_choppy(self):
        info = calculate_trend_factor(100.5, 100.0, 99.8)
        self.assertEqual(info.factor, -0.3)
        self.assertEqual(info.label, "choppy")

    def test_calculate_breakout_levels(self):
        closes = [10.0 + i for i in range(25)]
        df = pd.DataFrame({"close": closes, "high": closes, "low": closes})
        high, low = calculate_breakout_levels(df, window=20)
        self.assertEqual(high, 33.0)
        self.assertEqual(low, 14.0)

    def test_calculate_dynamic_stop_long(self):
        stop = calculate_dynamic_stop(1, 120.0, 2.0, 0.5)
        self.assertEqual(stop, 120.0 - 2.0 * 1.5 * 2.0)

    def test_calculate_unit_count(self):
        units = calculate_unit_count(10.0, contract_multiplier=1.0)
        self.assertEqual(units, 3)
        units_small = calculate_unit_count(2000.0, contract_multiplier=1.0)
        self.assertEqual(units_small, 1)
