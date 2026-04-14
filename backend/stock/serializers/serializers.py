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
    DailyPerformance,
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

    class Meta:
        model = DailyStrategySignal
        fields = '__all__'
        read_only_fields = ['id']


class PositionStateSerializer(serializers.ModelSerializer):
    """策略持仓状态序列化器"""
    
    class Meta:
        model = PositionState
        fields = '__all__'
        read_only_fields = ['id', 'last_update_time']



class DailyPerformanceSerializer(serializers.ModelSerializer):
    """每日绩效指标序列化器"""
    
    class Meta:
        model = DailyPerformance
        fields = '__all__'
        read_only_fields = ['id']
