"""
滑点记录视图集 - SlippageRecord 列表查询 + 滑点统计汇总
"""
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Q
from stock.serializers.serializers import SlippageRecordSerializer
from stock.models import SlippageRecord, TradingAccount
from stock.filters import UserAccountFilterBackend, validate_account_access


class SlippageRecordViewSet(viewsets.ModelViewSet):
    """
    【滑点记录视图集】

    💡 用途：
    - 查询历史滑点记录
    - 按账户/品种/交易类型过滤
    - 多账户数据隔离

    📊 典型查询：
    - GET /api/stock/slippage/?account=1
    - GET /api/stock/slippage/?account=1&trade_type=ENTRY
    - GET /api/stock/slippage/?account=1&symbol=SHFE.rb2510
    """
    queryset = SlippageRecord.objects.all()
    serializer_class = SlippageRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'account': ['exact'],
        'symbol': ['exact', 'contains'],
        'product_code': ['exact'],
        'trade_type': ['exact'],
        'trade_date': ['exact', 'gte', 'lte'],
        'is_favorable': ['exact'],
    }
    search_fields = ['symbol', 'product_code']
    ordering_fields = ['trade_date', 'created_at', 'slippage_ticks']
    ordering = ['-trade_date', '-created_at']


class SlippageStatsView(viewsets.ViewSet):
    """
    【滑点统计汇总接口】

    💡 返回指定账户的滑点汇总：
    - 总记录数、平均滑点（跳动）、有利滑点率
    - 按交易类型细分统计
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        account_id = request.query_params.get('account')

        if not account_id:
            return Response({
                'code': 4000,
                'msg': '缺少账户ID参数',
                'data': {}
            }, status=status.HTTP_400_BAD_REQUEST)

        if not validate_account_access(request.user, account_id):
            return Response({
                'code': 4003,
                'msg': '无权访问该账户',
                'data': {}
            }, status=status.HTTP_403_FORBIDDEN)

        # 总览统计
        base_qs = SlippageRecord.objects.filter(account_id=account_id)
        total_records = base_qs.count()

        avg_slippage = base_qs.aggregate(avg=Avg('slippage_ticks'))['avg']
        avg_slippage_ticks = round(float(avg_slippage), 2) if avg_slippage is not None else 0

        favorable_count = base_qs.filter(is_favorable=True).count()
        favorable_ratio = round(favorable_count / total_records * 100, 1) if total_records > 0 else 0

        # 按交易类型细分
        type_stats = base_qs.values('trade_type').annotate(
            count=Count('id'),
            avg_ticks=Avg('slippage_ticks'),
            favorable_count=Count('id', filter=Q(is_favorable=True)),
        ).order_by('-count')

        by_type = []
        for item in type_stats:
            fav_ratio = round(item['favorable_count'] / item['count'] * 100, 1) if item['count'] > 0 else 0
            avg_tick = round(float(item['avg_ticks']), 2) if item['avg_ticks'] is not None else 0
            by_type.append({
                'trade_type': item['trade_type'],
                'count': item['count'],
                'avg_slippage_ticks': avg_tick,
                'favorable_ratio': fav_ratio,
            })

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': {
                'total_records': total_records,
                'avg_slippage_ticks': avg_slippage_ticks,
                'favorable_ratio': favorable_ratio,
                'by_type': by_type,
            }
        })
