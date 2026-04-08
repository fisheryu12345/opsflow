"""
期货合约列表序列化器
"""
from rest_framework import serializers
from stock.models import FullContractList


class FullContractListSerializer(serializers.ModelSerializer):
    """
    期货合约列表序列化器
    
    用于展示和管理所有可交易的期货合约信息
    """
    
    # 添加只读的状态显示字段
    status_display = serializers.CharField(
        source='get_is_active_display',
        read_only=True,
        label='交易状态'
    )
    
    rollover_display = serializers.CharField(
        source='get_need_rollover_display',
        read_only=True,
        label='移仓状态'
    )

    class Meta:
        model = FullContractList
        fields = [
            'id',
            'exchange',
            'product_code',
            'symbol',
            'name',
            'is_active',
            'status_display',
            'allow_open',
            'volume_multiple',
            'price_tick',
            'margin_ratio',
            'sector',
            'category',
            'need_rollover',
            'rollover_display',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]
        extra_kwargs = {
            'exchange': {
                'help_text': '交易所代码：SHFE, DCE, CZCE, CFFEX, GFEX'
            },
            'product_code': {
                'help_text': '品种代码（不带年份），如：rb, MA, IF'
            },
            'symbol': {
                'help_text': '当前主力合约代码，如：rb2405, MA605'
            },
            'volume_multiple': {
                'help_text': '每手合约的价值乘数'
            },
            'price_tick': {
                'help_text': '价格最小变动单位'
            },
        }


class FullContractListCreateSerializer(serializers.ModelSerializer):
    """
    期货合约创建序列化器
    
    用于批量导入或手动添加新合约
    """
    
    class Meta:
        model = FullContractList
        fields = [
            'exchange',
            'product_code',
            'symbol',
            'name',
            'is_active',
            'allow_open',
            'volume_multiple',
            'price_tick',
            'margin_ratio',
            'sector',
            'category',
            'need_rollover',
        ]
        extra_kwargs = {
            'name': {
                'required': False,
                'allow_blank': True,
            },
            'sector': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            },
            'category': {
                'required': False,
                'allow_blank': True,
                'allow_null': True,
            },
        }


class FullContractListUpdateSerializer(serializers.ModelSerializer):
    """
    期货合约更新序列化器
    
    用于更新合约信息（如主力合约切换）
    """
    
    class Meta:
        model = FullContractList
        fields = [
            'symbol',
            'name',
            'is_active',
            'allow_open',
            'volume_multiple',
            'price_tick',
            'margin_ratio',
            'need_rollover',
        ]


class FullContractListSimpleSerializer(serializers.ModelSerializer):
    """
    简化版合约序列化器
    
    用于下拉选择等简单场景
    """
    
    display_name = serializers.SerializerMethodField(label='显示名称')

    class Meta:
        model = FullContractList
        fields = [
            'id',
            'symbol',
            'product_code',
            'exchange',
            'display_name',
            'is_active',
        ]
        read_only_fields = fields

    def get_display_name(self, obj):
        """生成显示名称"""
        return f"{obj.exchange}.{obj.symbol} ({obj.name or obj.product_code})"
