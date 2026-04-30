"""
绩效数据视图集 - 支持三层绩效模型的增删改查
"""
from rest_framework import viewsets, filters, status
from rest_framework.permissions import AllowAny  # ⚠️ 仅用于开发测试，生产环境请移除！
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Case, When, Value, IntegerField, Q
from stock.serializers.serializers import (
    DailyEquitySnapshotSerializer,
    RollingPerformanceMetricsSerializer,
    AccountPerformanceSummarySerializer,
    ClosedPositionRecordSerializer
)
from stock.models import (
    DailyEquitySnapshot,
    RollingPerformanceMetrics,
    AccountPerformanceSummary,
    ClosedPositionRecord
)


class DailyEquitySnapshotViewSet(viewsets.ModelViewSet):
    """
    【日权益快照视图集】- Layer 1
    
    💡 用途：
    - 查询历史资金曲线数据
    - 展示某天的详细权益信息
    - 计算日收益率序列
    
    📊 典型查询：
    - GET /api/equity-snapshots/?account=1&ordering=-trade_date
    - GET /api/equity-snapshots/?account=1&trade_date__gte=2024-01-01&trade_date__lte=2024-01-31
    """
    queryset = DailyEquitySnapshot.objects.all()
    serializer_class = DailyEquitySnapshotSerializer
    permission_classes = [AllowAny]  # ⚠️ 临时允许匿名访问（仅开发测试用）
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 过滤字段配置
    filterset_fields = {
        'account': ['exact'],
        'trade_date': ['exact', 'gte', 'lte', 'range'],  # 支持日期范围查询
    }
    
    # 搜索字段（模糊搜索）
    search_fields = ['account__name']
    
    # 排序字段
    ordering_fields = ['trade_date', 'balance', 'daily_return']
    ordering = ['-trade_date']  # 默认按日期倒序


class RollingPerformanceMetricsViewSet(viewsets.ModelViewSet):
    """
    【滚动绩效指标视图集】- Layer 2
    
    💡 用途：
    - 查询不同窗口的绩效指标（20/60/120日）
    - 对比多周期策略表现
    - 监控指标稳定性
    
    📊 典型查询：
    - GET /api/rolling-metrics/?account=1&window_days=20&ordering=-calc_date
    - GET /api/rolling-metrics/?account=1&window_days__in=20,60,120,250日
    - GET /api/rolling-metrics/?account=1&data_quality=COMPLETE
    - GET /api/rolling-metrics/?account=1&data_quality=COMPLETE
    """
    queryset = RollingPerformanceMetrics.objects.all()
    serializer_class = RollingPerformanceMetricsSerializer
    permission_classes = [AllowAny]  # ⚠️ 临时允许匿名访问（仅开发测试用）
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 过滤字段配置
    filterset_fields = {
        'account': ['exact'],
        'calc_date': ['exact', 'gte', 'lte', 'range'],
        'window_days': ['exact', 'in'],  # 支持多窗口查询
        'data_quality': ['exact'],
    }
    
    # 搜索字段
    search_fields = ['account__name']
    
    # 排序字段
    ordering_fields = ['calc_date', 'sharpe_ratio', 'volatility', 'window_days']
    ordering = ['-calc_date']  # 默认按计算日期倒序


class AccountPerformanceSummaryViewSet(viewsets.ModelViewSet):
    """
    【账户绩效总览视图集】- Layer 3
    
    💡 用途：
    - Dashboard 首页展示
    - 账户整体健康度评估
    - 快速获取全局指标
    
    📊 典型查询：
    - GET /api/account-summaries/?account=1&ordering=-snapshot_date
    - GET /api/account-summaries/?account=1&snapshot_date__gte=2024-01-01
    """
    queryset = AccountPerformanceSummary.objects.all()
    serializer_class = AccountPerformanceSummarySerializer
    permission_classes = [AllowAny]  # ⚠️ 临时允许匿名访问（仅开发测试用）
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 过滤字段配置
    filterset_fields = {
        'account': ['exact'],
        'snapshot_date': ['exact', 'gte', 'lte', 'range'],
    }
    
    # 搜索字段
    search_fields = ['account__name']
    
    # 排序字段
    ordering_fields = ['snapshot_date', 'total_return', 'max_drawdown_all_time']
    ordering = ['-snapshot_date']  # 默认按快照日期倒序


class SymbolWinRateView(viewsets.ViewSet):
    """
    【品种胜率统计接口】
    
    💡 返回格式：
    [
        {
            "product_code": "rb",
            "product_name": "螺纹钢",
            "total_trades": 45,
            "winning_trades": 31,
            "win_rate": 68.89,
            "long_trades": 30,
            "short_trades": 15,
            "total_pnl": 12500.00
        },
        ...
    ]
    """
    permission_classes = [AllowAny]  # ⚠️ 临时允许匿名访问（仅开发测试用）
    
    def list(self, request):
        account_id = request.query_params.get('account')
        
        if not account_id:
            return Response({
                'code': 4000,
                'msg': '缺少账户ID参数',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 使用 Django ORM 聚合查询
        stats = ClosedPositionRecord.objects.filter(
            account_id=account_id
        ).values(
            'product_code'
        ).annotate(
            total_trades=Count('id'),
            winning_trades=Count(Case(
                When(pnl__gt=0, then=1),
                output_field=IntegerField()
            )),
            long_trades=Count(Case(
                When(direction=1, then=1),
                output_field=IntegerField()
            )),
            short_trades=Count(Case(
                When(direction=-1, then=1),
                output_field=IntegerField()
            )),
            total_pnl=Sum('pnl')
        ).order_by('-total_pnl')
        
        # 计算胜率并格式化返回
        result = []
        for item in stats:
            win_rate = (item['winning_trades'] / item['total_trades'] * 100) if item['total_trades'] > 0 else 0
            result.append({
                'name': item['product_code'],  # 前端期望的字段名
                'product_code': item['product_code'],
                'winRate': round(win_rate, 2),
                'trades': item['total_trades'],
                'LongNum': item['long_trades'],
                'ShortNum': item['short_trades'],
                'profit': float(item['total_pnl']) if item['total_pnl'] else 0
            })
        
        return Response({
            'code': 2000,
            'msg': 'success',
            'data': result
        })


class AccountCumulativeStatsView(viewsets.ViewSet):
    """
    【账户累计统计接口】
    
    💡 返回格式：
    {
        "code": 2000,
        "msg": "success",
        "data": {
            "total_closed_pnl": 12500.00,  // 累计平仓盈亏
            "total_commission": 850.50     // 累计手续费
        }
    }
    """
    permission_classes = [AllowAny]  # ⚠️ 临时允许匿名访问（仅开发测试用）
    
    def list(self, request):
        account_id = request.query_params.get('account')
        
        if not account_id:
            return Response({
                'code': 4000,
                'msg': '缺少账户ID参数',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. 累计平仓盈亏（从 ClosedPositionRecord 聚合）
        closed_pnl_agg = ClosedPositionRecord.objects.filter(
            account_id=account_id
        ).aggregate(
            total_pnl=Sum('pnl')
        )
        total_closed_pnl = float(closed_pnl_agg['total_pnl'] or 0)
        
        # 2. 累计手续费（从 DailyEquitySnapshot 聚合）
        commission_agg = DailyEquitySnapshot.objects.filter(
            account_id=account_id
        ).aggregate(
            total_commission=Sum('commission')
        )
        total_commission = float(commission_agg['total_commission'] or 0)
        
        return Response({
            'code': 2000,
            'msg': 'success',
            'data': {
                'total_closed_pnl': total_closed_pnl,
                'total_commission': total_commission
            }
        })
