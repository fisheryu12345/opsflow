# -*- coding: utf-8 -*-
"""Strategy models — MoniorStrategy 四层策略模型 (Strategy→Item→QueryConfig→Detect→Algorithm)

对标 bk-monitor StrategyModel / ItemModel / QueryConfigModel / DetectModel / AlgorithmModel
"""

from django.db import models
from common.utils.models import table_prefix


def default_target():
    return [[]]


def no_data_config():
    return {"is_enabled": True, "continuous": 5, "agg_dimension": []}


# ═══════════════════════════════════════════════════════════════════════
# 策略
# ═══════════════════════════════════════════════════════════════════════
class MonitorStrategy(models.Model):
    """
    监控策略 (Strategy)
    对标 bk-monitor StrategyModel。定义一组监控项的集合及触发行为。
    """

    class StrategyType:
        """策略类型"""
        MONITOR = "monitor"
        FTA = "fta"
        DASHBOARD = "dashboard"
        CHOICES = (
            (MONITOR, "监控"),
            (FTA, "故障自愈"),
            (DASHBOARD, "仪表盘"),
        )

    class InvalidType:
        """失效类型"""
        NONE = ""
        INVALID_RELATED_STRATEGY = "invalid_related_strategy"
        INVALID_TARGET = "invalid_target"
        INVALID_METRIC = "invalid_metric"
        INVALID_BIZ = "invalid_biz"
        CHOICES = [
            (NONE, ""),
            (INVALID_RELATED_STRATEGY, "关联策略已失效"),
            (INVALID_TARGET, "监控目标全部失效"),
            (INVALID_METRIC, "监控指标不存在"),
            (INVALID_BIZ, "策略所属业务不存在"),
        ]

    name = models.CharField(max_length=128, verbose_name="策略名称", db_index=True)
    bk_biz_id = models.IntegerField(verbose_name="业务ID", db_index=True)
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business',
        help_text='Business line for tenant isolation / 业务线归属'
    )
    scenario = models.CharField(max_length=32, verbose_name="监控场景",
                                help_text="如 host / service / custom")
    source = models.CharField(max_length=32, default="monitor", verbose_name="来源系统")
    type = models.CharField(
        max_length=12, choices=StrategyType.CHOICES,
        default=StrategyType.MONITOR, verbose_name="策略类型", db_index=True,
    )
    is_enabled = models.BooleanField(default=True, verbose_name="是否启用")
    is_invalid = models.BooleanField(default=False, verbose_name="是否失效")
    invalid_type = models.CharField(
        max_length=32, blank=True, default=InvalidType.NONE,
        choices=InvalidType.CHOICES, verbose_name="失效类型",
    )
    priority = models.IntegerField(null=True, blank=True, verbose_name="优先级")
    priority_group_key = models.CharField(
        max_length=64, null=True, blank=True, verbose_name="优先级分组Key",
    )
    create_user = models.CharField(max_length=32, default="", verbose_name="创建人")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_user = models.CharField(max_length=32, default="", verbose_name="修改人")
    update_time = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = table_prefix + "monitor_strategy"
        verbose_name = "监控策略"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
        indexes = [
            models.Index(fields=["is_enabled", "bk_biz_id", "scenario"]),
        ]

    def __str__(self):
        return self.name


# ═══════════════════════════════════════════════════════════════════════
# 监控项
# ═══════════════════════════════════════════════════════════════════════
class MonitorItem(models.Model):
    """
    监控项 (Item)
    对标 bk-monitor ItemModel。定义一条具体的监控指标及查询方式。
    """
    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="items", verbose_name="关联策略",
    )
    name = models.CharField(max_length=256, verbose_name="监控项名称")
    expression = models.TextField(blank=True, default="", verbose_name="计算公式")
    functions = models.JSONField(default=list, verbose_name="计算函数")
    origin_sql = models.TextField(blank=True, default="", verbose_name="原始查询语句")
    no_data_config = models.JSONField(default=no_data_config, verbose_name="无数据配置")
    target = models.JSONField(default=default_target, verbose_name="监控目标")
    meta = models.JSONField(default=list, verbose_name="查询配置元数据")
    metric_type = models.CharField(max_length=32, blank=True, default="", verbose_name="指标类型")
    time_delay = models.IntegerField(default=0, verbose_name="策略等待时间(秒)")

    class Meta:
        db_table = table_prefix + "monitor_item"
        verbose_name = "监控项"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.strategy.name} / {self.name}"


# ═══════════════════════════════════════════════════════════════════════
# 查询配置
# ═══════════════════════════════════════════════════════════════════════
class MonitorQueryConfig(models.Model):
    """
    查询配置 (QueryConfig)
    对标 bk-monitor QueryConfigModel。定义指标查询的数据源和参数。
    """
    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="query_configs", verbose_name="关联策略",
    )
    item = models.ForeignKey(
        MonitorItem, on_delete=models.CASCADE,
        related_name="query_configs", verbose_name="关联监控项",
    )
    alias = models.CharField(max_length=12, verbose_name="别名")
    data_source_label = models.CharField(
        max_length=32, verbose_name="数据来源标签",
        help_text="prometheus / influxdb / custom",
    )
    data_type_label = models.CharField(
        max_length=32, verbose_name="数据类型标签",
        help_text="metric / event / log",
    )
    metric_id = models.CharField(max_length=128, verbose_name="指标ID")
    config = models.JSONField(default=dict, verbose_name="查询配置",
                              help_text="promql / agg_interval / agg_method 等")

    class Meta:
        db_table = table_prefix + "monitor_query_config"
        verbose_name = "查询配置"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["data_source_label", "data_type_label"]),
        ]

    def __str__(self):
        return f"{self.alias} ({self.metric_id})"


# ═══════════════════════════════════════════════════════════════════════
# 检测配置
# ═══════════════════════════════════════════════════════════════════════
class MonitorDetectConfig(models.Model):
    """
    检测配置 (Detect Config)
    对标 bk-monitor DetectModel。定义告警级别、触发条件与恢复条件。
    """
    LEVEL_CHOICES = (
        (1, "致命"),
        (2, "预警"),
        (3, "提醒"),
    )

    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="detect_configs", verbose_name="关联策略",
    )
    item = models.ForeignKey(
        MonitorItem, on_delete=models.CASCADE,
        related_name="detect_configs", verbose_name="关联监控项",
    )
    level = models.IntegerField(choices=LEVEL_CHOICES, default=3, verbose_name="告警级别")
    expression = models.TextField(blank=True, default="", verbose_name="计算公式")
    trigger_config = models.JSONField(default=dict, verbose_name="触发条件配置",
                                      help_text="如 {'count': 3, 'check_window': 5}")
    recovery_config = models.JSONField(default=dict, verbose_name="恢复条件配置")
    connector = models.CharField(
        max_length=4, choices=(("and", "AND"), ("or", "OR")),
        default="and", verbose_name="同级算法连接符",
    )

    class Meta:
        db_table = table_prefix + "monitor_detect_config"
        verbose_name = "检测配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"Level-{self.level} / {self.strategy.name}"


# ═══════════════════════════════════════════════════════════════════════
# 算法配置
# ═══════════════════════════════════════════════════════════════════════
class MonitorAlgorithmConfig(models.Model):
    """
    检测算法配置 (Algorithm Config)
    对标 bk-monitor AlgorithmModel。定义具体的检测算法及参数。
    """
    class AlgorithmType:
        """算法类型枚举"""
        THRESHOLD = "Threshold"
        SIMPLE_RING_RATIO = "SimpleRingRatio"
        ADVANCED_RING_RATIO = "AdvancedRingRatio"
        SIMPLE_YEAR_ROUND = "SimpleYearRound"
        ADVANCED_YEAR_ROUND = "AdvancedYearRound"
        YEAR_ROUND_AMPLITUDE = "YearRoundAmplitude"
        YEAR_ROUND_RANGE = "YearRoundRange"
        RING_RATIO_AMPLITUDE = "RingRatioAmplitude"
        INTELLIGENT_DETECT = "IntelligentDetect"
        TIME_SERIES_FORECASTING = "TimeSeriesForecasting"
        PARTIAL_NODES = "PartialNodes"
        OS_RESTART = "OsRestart"
        PING_UNREACHABLE = "PingUnreachable"
        PROC_PORT = "ProcPort"

        CHOICES = (
            (THRESHOLD, "静态阈值"),
            (SIMPLE_RING_RATIO, "简易环比"),
            (ADVANCED_RING_RATIO, "高级环比"),
            (SIMPLE_YEAR_ROUND, "简易同比"),
            (ADVANCED_YEAR_ROUND, "高级同比"),
            (YEAR_ROUND_AMPLITUDE, "同比振幅"),
            (YEAR_ROUND_RANGE, "同比区间"),
            (RING_RATIO_AMPLITUDE, "环比振幅"),
            (INTELLIGENT_DETECT, "智能异常检测"),
            (TIME_SERIES_FORECASTING, "时序预测"),
            (PARTIAL_NODES, "部分节点数"),
            (OS_RESTART, "主机重启"),
            (PING_UNREACHABLE, "Ping不可达"),
            (PROC_PORT, "进程端口"),
        )

    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="algorithms", verbose_name="关联策略",
    )
    item = models.ForeignKey(
        MonitorItem, on_delete=models.CASCADE,
        related_name="algorithms", verbose_name="关联监控项",
    )
    detect = models.ForeignKey(
        MonitorDetectConfig, on_delete=models.CASCADE,
        related_name="algorithms", verbose_name="关联检测配置",
    )
    level = models.IntegerField(
        choices=MonitorDetectConfig.LEVEL_CHOICES, default=3, verbose_name="告警级别",
    )
    type = models.CharField(
        max_length=64, choices=AlgorithmType.CHOICES,
        verbose_name="算法类型", db_index=True,
    )
    config = models.JSONField(default=dict, verbose_name="算法配置",
                              help_text="如 {'threshold': 90, 'method': 'gte'}")

    class Meta:
        db_table = table_prefix + "monitor_algorithm_config"
        verbose_name = "算法配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.get_type_display()} / Level-{self.level}"


# ═══════════════════════════════════════════════════════════════════════
# 策略标签
# ═══════════════════════════════════════════════════════════════════════
class MonitorStrategyLabel(models.Model):
    """策略标签"""
    label_name = models.CharField(max_length=128, verbose_name="标签名称")
    bk_biz_id = models.IntegerField(default=0, blank=True, verbose_name="业务ID", db_index=True)
    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="labels", null=True, blank=True, verbose_name="策略",
    )

    class Meta:
        db_table = table_prefix + "monitor_strategy_label"
        verbose_name = "策略标签"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.label_name


# ═══════════════════════════════════════════════════════════════════════
# 策略变更历史
# ═══════════════════════════════════════════════════════════════════════
class MonitorStrategyHistory(models.Model):
    """策略操作历史"""
    strategy = models.ForeignKey(
        MonitorStrategy, on_delete=models.CASCADE,
        related_name="history", verbose_name="关联策略",
    )
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    create_user = models.CharField(max_length=32, verbose_name="操作人")
    content = models.JSONField(default=dict, verbose_name="保存内容")
    operate = models.CharField(
        max_length=12,
        choices=(("delete", "删除"), ("create", "创建"), ("update", "更新")),
        verbose_name="操作",
    )
    status = models.BooleanField(default=False, verbose_name="操作状态")
    message = models.TextField(blank=True, default="", verbose_name="错误信息")

    class Meta:
        db_table = table_prefix + "monitor_strategy_history"
        verbose_name = "策略变更历史"
        verbose_name_plural = verbose_name
        ordering = ["-create_time"]
