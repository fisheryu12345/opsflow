# -*- coding: utf-8 -*-
"""Algorithm Engine — 检测算法引擎

支持 14 种检测算法，插件化注册。
算法返回值: (is_triggered: bool, anomaly_value: float, expression: str)
"""

import logging
import statistics
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)
FSM = 'algorithm_engine'


class BaseAlgorithm(ABC):
    """算法基类"""

    @abstractmethod
    def check(self, values: list, config: dict) -> tuple:
        """
        检测指标值是否触发告警
        Args:
            values: [(timestamp, value), ...] 或 [value, ...] 时序数据
            config: 算法配置参数
        Returns:
            (is_triggered: bool, anomaly_value: float, expression: str)
        """
        pass

    def _extract_values(self, values: list) -> list:
        """提取数值列"""
        result = []
        for v in values:
            if isinstance(v, (list, tuple)):
                if len(v) >= 2:
                    try:
                        result.append(float(v[1]))
                    except (ValueError, TypeError):
                        continue
            else:
                try:
                    result.append(float(v))
                except (ValueError, TypeError):
                    continue
        return result


class ThresholdAlgorithm(BaseAlgorithm):
    """静态阈值算法 — method: gt/lt/gte/lte, threshold: float"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if not nums:
            return False, 0, 'no data'
        latest = nums[-1]
        method = config.get('method', 'gte')
        threshold = config.get('threshold', 0)
        if method == 'gt':      triggered = latest > threshold
        elif method == 'lt':    triggered = latest < threshold
        elif method == 'gte':   triggered = latest >= threshold
        elif method == 'lte':   triggered = latest <= threshold
        else:                   triggered = latest >= threshold
        expr = f"当前值 {latest:.2f} {'>' if 'gt' in method else '<'} 阈值 {threshold}"
        return triggered, latest, expr


class SimpleRingRatioAlgorithm(BaseAlgorithm):
    """简易环比 — 与上一周期值比较变化率"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 2:
            return False, 0, 'insufficient data'
        v1, v2 = nums[-1], nums[-2]
        if v2 == 0:
            return False, v1, 'baseline is zero'
        ratio = (v1 - v2) / abs(v2)
        threshold = config.get('ratio', 0.5)
        floor = config.get('floor', 0)
        triggered = abs(ratio) > threshold and abs(v1 - v2) > floor
        expr = f"环比 {ratio*100:.1f}%（阈值 {threshold*100:.1f}%）"
        return triggered, v1, expr


class AdvancedRingRatioAlgorithm(BaseAlgorithm):
    """高级环比 — 与过去 N 个周期的均值比较"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 3:
            return False, 0, 'insufficient data'
        v1 = nums[-1]
        refer_count = min(config.get('refer_count', 5), len(nums) - 1)
        baseline = statistics.mean(nums[-refer_count-1:-1])
        if baseline == 0:
            return False, v1, 'baseline is zero'
        ratio = abs(v1 - baseline) / abs(baseline)
        threshold = config.get('ratio', 0.3)
        triggered = ratio > threshold
        expr = f"高级环比 {ratio*100:.1f}%（基线 {baseline:.2f}）"
        return triggered, v1, expr


class SimpleYearRoundAlgorithm(BaseAlgorithm):
    """简易同比 — 与 N 个周期前同一点比较"""

    def check(self, values, config):
        nums = self._extract_values(values)
        period = config.get('period', len(nums) // 2)
        if len(nums) < period + 1:
            return False, 0, 'insufficient data'
        v1 = nums[-1]
        v_prev = nums[-1 - period]
        if v_prev == 0:
            return False, v1, 'baseline is zero'
        ratio = (v1 - v_prev) / abs(v_prev)
        threshold = config.get('ratio', 0.5)
        triggered = abs(ratio) > threshold
        expr = f"同比 {ratio*100:.1f}%（参照 {v_prev:.2f}）"
        return triggered, v1, expr


class AdvancedYearRoundAlgorithm(BaseAlgorithm):
    """高级同比 — 与历史同期多周期的中位数比较"""

    def check(self, values, config):
        nums = self._extract_values(values)
        period = config.get('period', len(nums) // 2)
        if len(nums) < period * 2:
            return False, 0, 'insufficient data'
        v1 = nums[-1]
        historical = [nums[i] for i in range(len(nums) - period - 1, -1, -period)]
        if not historical:
            return False, v1, 'no historical data'
        baseline = statistics.median(historical)
        if baseline == 0:
            return False, v1, 'baseline is zero'
        ratio = abs(v1 - baseline) / abs(baseline)
        threshold = config.get('ratio', 0.3)
        triggered = ratio > threshold
        expr = f"高级同比 {ratio*100:.1f}%（中位数基线 {baseline:.2f}）"
        return triggered, v1, expr


class YearRoundAmplitudeAlgorithm(BaseAlgorithm):
    """同比振幅 — 与去年同期值比较差异幅度"""

    def check(self, values, config):
        nums = self._extract_values(values)
        period = config.get('period', len(nums) // 2)
        if len(nums) < period + 1:
            return False, 0, 'insufficient data'
        v1, v_prev = nums[-1], nums[-1 - period]
        if v_prev == 0:
            return False, v1, 'baseline is zero'
        amplitude = abs(v1 - v_prev)
        threshold = config.get('threshold', 100)
        triggered = amplitude > threshold
        expr = f"振幅 {amplitude:.2f}（阈值 {threshold}）"
        return triggered, v1, expr


class YearRoundRangeAlgorithm(BaseAlgorithm):
    """同比区间 — 值是否超出历史同期置信区间"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 6:
            return False, 0, 'insufficient data'
        v1 = nums[-1]
        mean = statistics.mean(nums[:-1])
        stdev = statistics.pstdev(nums[:-1]) if len(nums) > 2 else 0
        if stdev == 0:
            return False, v1, 'zero stdev'
        z_score = (v1 - mean) / stdev
        threshold = config.get('threshold', 2.0)
        triggered = abs(z_score) > threshold
        expr = f"z-score: {z_score:.2f}（阈值 {threshold}）"
        return triggered, v1, expr


class RingRatioAmplitudeAlgorithm(BaseAlgorithm):
    """环比振幅 — 连续两个周期的变化幅度"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 4:
            return False, 0, 'insufficient data'
        v1 = nums[-1]
        # 计算当前周期均值 vs 上一周期均值
        half = len(nums) // 2
        current_mean = statistics.mean(nums[half:])
        prev_mean = statistics.mean(nums[:half])
        diff = abs(current_mean - prev_mean)
        threshold = config.get('threshold', 50)
        triggered = diff > threshold
        expr = f"周期振幅 {diff:.2f}（阈值 {threshold}）"
        return triggered, v1, expr


class IntelligentDetectAlgorithm(BaseAlgorithm):
    """智能异常检测 — 基于 3-sigma 动态阈值"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 10:
            return False, 0, 'insufficient data(need 10+)'
        v1 = nums[-1]
        window = min(config.get('window', len(nums)), len(nums))
        recent = nums[-window:]
        mean = statistics.mean(recent)
        stdev = statistics.pstdev(recent) if len(recent) > 2 else 0
        if stdev == 0:
            return False, v1, 'zero stdev'
        z_score = (v1 - mean) / stdev
        sensitivity = config.get('sensitivity', 3.0)
        triggered = abs(z_score) > sensitivity
        expr = f"智能检测 z={z_score:.2f} sigma={sensitivity}"
        return triggered, v1, expr


class TimeSeriesForecastingAlgorithm(BaseAlgorithm):
    """时序预测 — 简单线性回归预测下一个值与实际值比较"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 5:
            return False, 0, 'insufficient data'
        # 最小二乘线性回归
        x = list(range(len(nums)))
        n = len(x)
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(nums)
        slope = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, nums)) / sum((xi - x_mean) ** 2 for xi in x)
        intercept = y_mean - slope * x_mean
        predicted = slope * n + intercept
        actual = nums[-1]
        confidence = config.get('confidence', 0.2)
        diff = abs(actual - predicted) / max(abs(predicted), 1)
        triggered = diff > confidence
        expr = f"预测 {predicted:.2f}, 实际 {actual:.2f}, 偏差 {diff*100:.1f}%"
        return triggered, actual, expr


class PartialNodesAlgorithm(BaseAlgorithm):
    """部分节点数 — 当有效节点数低于阈值时触发"""

    def check(self, values, config):
        nums = self._extract_values(values)
        total = config.get('total', 100)
        min_count = config.get('min_count', 10)
        percentage = config.get('percentage', 20)
        count = len(nums)
        threshold = max(min_count, int(total * percentage / 100))
        triggered = count < threshold
        expr = f"节点数 {count}/{total}（阈值 {threshold}）"
        return triggered, float(count), expr


class OsRestartAlgorithm(BaseAlgorithm):
    """主机重启检测 — 判断指标是否出现突降后突升模式"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if len(nums) < 10:
            return False, 0, 'insufficient data'
        # 检测连续下降后急剧回升的模式
        drops = sum(1 for i in range(1, len(nums)) if nums[i] < nums[i-1] * 0.5)
        jumps = sum(1 for i in range(1, len(nums)) if nums[i] > nums[i-1] * 2.0)
        triggered = drops >= 3 and jumps >= 2
        expr = f"下降{drops}次 回升{jumps}次"
        return triggered, nums[-1], expr


class PingUnreachableAlgorithm(BaseAlgorithm):
    """Ping不可达 — 连续 N 次无响应"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if not nums:
            return True, 1, 'no data received'
        threshold = config.get('threshold', 0)
        # 1 = 不可达, 0 = 可达
        unreachable = sum(1 for v in nums[-10:] if v >= threshold)
        trigger_count = config.get('trigger_count', 5)
        triggered = unreachable >= trigger_count
        expr = f"不可达 {unreachable}/{trigger_count} 次"
        return triggered, float(unreachable), expr


class ProcPortAlgorithm(BaseAlgorithm):
    """进程端口检测 — 检测进程/端口是否存活的布尔值"""

    def check(self, values, config):
        nums = self._extract_values(values)
        if not nums:
            return True, 1, 'no data'
        # 0 = 进程不存在, 1 = 进程存在
        latest = nums[-1]
        threshold = config.get('threshold', 0.5)
        triggered = latest < threshold
        expr = f"进程状态: {'异常' if triggered else '正常'}"
        return triggered, latest, expr


# ═══════════════════════════════════════════════════════════════════════
# 算法注册表
# ═══════════════════════════════════════════════════════════════════════
ALGORITHM_REGISTRY = {
    'Threshold': ThresholdAlgorithm,
    'SimpleRingRatio': SimpleRingRatioAlgorithm,
    'AdvancedRingRatio': AdvancedRingRatioAlgorithm,
    'SimpleYearRound': SimpleYearRoundAlgorithm,
    'AdvancedYearRound': AdvancedYearRoundAlgorithm,
    'YearRoundAmplitude': YearRoundAmplitudeAlgorithm,
    'YearRoundRange': YearRoundRangeAlgorithm,
    'RingRatioAmplitude': RingRatioAmplitudeAlgorithm,
    'IntelligentDetect': IntelligentDetectAlgorithm,
    'TimeSeriesForecasting': TimeSeriesForecastingAlgorithm,
    'PartialNodes': PartialNodesAlgorithm,
    'OsRestart': OsRestartAlgorithm,
    'PingUnreachable': PingUnreachableAlgorithm,
    'ProcPort': ProcPortAlgorithm,
}


def get_algorithm(algorithm_type: str) -> Optional[BaseAlgorithm]:
    """获取算法实例"""
    cls = ALGORITHM_REGISTRY.get(algorithm_type)
    if cls:
        return cls()
    logger.warning(f"Unknown algorithm type: {algorithm_type}")
    return None


def run_detection(algorithm_type: str, values: list, config: dict) -> tuple:
    """执行检测 — 返回 (is_triggered, anomaly_value, expression)"""
    algo = get_algorithm(algorithm_type)
    if not algo:
        return False, 0, f'unknown algorithm: {algorithm_type}'
    try:
        return algo.check(values, config)
    except Exception as e:
        logger.error(f"Algorithm {algorithm_type} error: {e}", exc_info=True)
        return False, 0, f'error: {e}'
