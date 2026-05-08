"""
期货合约相关序列化器 - 支持增删改查
"""
from rest_framework import serializers
from stock.models import (
    FullContractList,
    TradingAccount,
    StrategyConfig,
    DailyStrategySignal,
    PositionState,
    # DailyPerformance,
    TradeLog,
    ErrorLog,
    DailyEquitySnapshot,
    RollingPerformanceMetrics,
    AccountPerformanceSummary,
    ClosedPositionRecord
)


class FullContractListSerializer(serializers.ModelSerializer):
    """期货合约列表序列化器"""
    
    class Meta:
        model = FullContractList
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TradingAccountSerializer(serializers.ModelSerializer):
    """交易账户序列化器"""
    
    class Meta:
        model = TradingAccount
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class StrategyConfigSerializer(serializers.ModelSerializer):
    """策略参数配置序列化器"""
    
    class Meta:
        model = StrategyConfig
        fields = '__all__'
        read_only_fields = ['id']


class DailyStrategySignalSerializer(serializers.ModelSerializer):
    """每日策略信号序列化器"""
    
    class Meta:
        model = DailyStrategySignal
        fields = '__all__'
        read_only_fields = ['id']
        depth = 1  # 展开外键关系，方便前端显示账户信息


class PositionStateSerializer(serializers.ModelSerializer):
    """策略持仓状态序列化器"""
    
    class Meta:
        model = PositionState
        fields = '__all__'
        read_only_fields = ['id', 'last_update_time']
        depth = 1  # 展开外键关系，方便前端显示账户信息


# class DailyPerformanceSerializer(serializers.ModelSerializer):
#     """每日绩效指标序列化器"""
    
#     class Meta:
#         model = DailyPerformance
#         fields = '__all__'
#         read_only_fields = ['id']


class TradeLogSerializer(serializers.ModelSerializer):
    """每日绩效指标序列化器"""
    
    class Meta:
        model = TradeLog
        fields = '__all__'
        read_only_fields = ['id']


class ErrorLogSerializer(serializers.ModelSerializer):
    """每日绩效指标序列化器"""
    
    class Meta:
        model = ErrorLog
        fields = '__all__'
        read_only_fields = ['id']


class ClosedPositionRecordSerializer(serializers.ModelSerializer):
    """
    【平仓交易记录序列化器】
    
    💡 用途：
    - 查询历史平仓记录
    - 品种胜率统计分析
    - 盈亏分布分析
    """
    account_name = serializers.CharField(source='account.name', read_only=True, help_text="账户名称")
    
    class Meta:
        model = ClosedPositionRecord
        fields = [
            'id',
            'account',
            'account_name',
            'symbol',
            'product_code',
            'direction',
            'volume',
            'exit_price',
            'cost_price',
            'pnl',
            'trade_date',
            'executed_at',
            'holding_days',
        ]
        read_only_fields = ['id']


# ==================== 三层绩效模型序列化器 ====================

class DailyEquitySnapshotSerializer(serializers.ModelSerializer):
    """
    【日权益快照序列化器】- Layer 1
    
    💡 用途：
    - 查询历史资金曲线数据
    - 展示某天的详细权益信息
    - 计算日收益率序列
    """
    account_name = serializers.CharField(source='account.name', read_only=True, help_text="账户名称")
    
    class Meta:
        model = DailyEquitySnapshot
        fields = [
            'id',
            'account',
            'account_name',
            'trade_date',
            'balance',
            'available',
            'float_profit',
            'margin',
            'risk_ratio',
            'commission',
            'daily_return',
            'daily_pnl',
            'closed_pnl',  # 新增：平仓盈亏字段
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RollingPerformanceMetricsSerializer(serializers.ModelSerializer):
    """
    【滚动绩效指标序列化器】- Layer 2
    
    💡 用途：
    - 查询不同窗口的绩效指标（20/60/120日）
    - 对比多周期策略表现
    - 监控指标稳定性
    """
    account_name = serializers.CharField(source='account.name', read_only=True, help_text="账户名称")
    
    class Meta:
        model = RollingPerformanceMetrics
        fields = [
            'id',
            'account',
            'account_name',
            'calc_date',
            'window_days',
            'sharpe_ratio',
            'sortino_ratio',
            'volatility',
            'win_rate',
            'profit_loss_ratio',
            'total_trades',
            'data_quality',
            'calculated_at',
        ]
        read_only_fields = ['id', 'calculated_at']


class AccountPerformanceSummarySerializer(serializers.ModelSerializer):
    """
    【账户绩效总览序列化器】- Layer 3
    
    💡 用途：
    - Dashboard 首页展示
    - 账户整体健康度评估
    - 快速获取全局指标
    """
    account_name = serializers.CharField(source='account.name', read_only=True, help_text="账户名称")
    
    class Meta:
        model = AccountPerformanceSummary
        fields = [
            'id',
            'account',
            'account_name',
            'snapshot_date',
            # === 全局收益指标 ===
            'total_return',
            'annualized_return',
            # === 全局风险指标 ===
            'max_drawdown_all_time',
            'current_drawdown',
            'max_drawdown_duration',
            'calmar_ratio',
            # === 全局交易统计 ===
            'total_trades_all_time',
            'overall_win_rate',
            'overall_profit_factor',
            # === 极端值统计 ===
            'best_single_trade',
            'worst_single_trade',
            'consecutive_wins',
            'consecutive_losses',
            # === 持仓统计 ===
            'current_long_position',
            'current_short_position',
            'avg_holding_days',
            # === 引用滚动指标 ===
            'latest_sharpe_20d',
            'latest_volatility_20d',
            'latest_sortino_20d',
            # === 交易行为统计 ===
            'trading_frequency',
            # === 累计财务数据 ===
            'closed_profit_total',
            'commission_total',
            # === 元数据 ===
            'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']
