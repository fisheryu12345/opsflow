"""
每日策略信号视图集
"""
from datetime import date, timedelta
from decimal import Decimal
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg
from django.utils import timezone
from stock.serializers.serializers import DailyStrategySignalSerializer
from stock.models import DailyStrategySignal
from stock.filters import UserAccountFilterBackend, get_user_account_ids


class DailyStrategySignalViewSet(viewsets.ModelViewSet):
    """
    每日策略信号视图集 - 支持增删改查
    """
    queryset = DailyStrategySignal.objects.all().order_by('-trade_date')
    serializer_class = DailyStrategySignalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['executed_status', 'trade_type', 'symbol', 'is_breakout', 'signal_direction', 'account', 'trend_label']
    search_fields = ['symbol', 'remark','executed_status', 'trade_type']
    ordering_fields = ['trade_date', 'trend_factor']
    ordering = ['-trade_date']

    def get_queryset(self):
        qs = super().get_queryset()
        trade_date__gte = self.request.query_params.get('trade_date__gte')
        trade_date__lte = self.request.query_params.get('trade_date__lte')
        if trade_date__gte:
            qs = qs.filter(trade_date__gte=trade_date__gte)
        if trade_date__lte:
            qs = qs.filter(trade_date__lte=trade_date__lte)
        return qs


class SignalExecutionStatsView(APIView):
    """
    信号执行统计接口

    提供：
    - 按交易类型统计执行成功率
    - 按失败原因分布统计
    - 总体执行概况
    - 平均执行延迟

    GET /api/stock/signal-stats/?date_from=...&date_to=...&account=...
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        account_id = request.query_params.get('account')

        # 基础过滤
        filters = Q()
        if date_from:
            filters &= Q(trade_date__gte=date_from)
        if date_to:
            filters &= Q(trade_date__lte=date_to)
        if account_id:
            filters &= Q(account_id=account_id)

        # 账户数据隔离：非超管只能看到自己有权限的账户数据
        user_account_ids = get_user_account_ids(request.user)
        if user_account_ids is not None:
            filters &= Q(account_id__in=user_account_ids)

        base_qs = DailyStrategySignal.objects.filter(filters)

        # 1. 总体概况
        total = base_qs.count()
        success_count = base_qs.filter(executed_status='SUCCESS').count()
        failed_count = base_qs.filter(executed_status='FAILED').count()
        cancelled_count = base_qs.filter(executed_status='CANCELLED').count()
        pending_count = base_qs.filter(executed_status='PENDING').count()

        executed_total = success_count + failed_count
        overall_rate = round(success_count / executed_total * 100, 1) if executed_total > 0 else 0

        # 2. 按交易类型统计
        type_stats = []
        type_qs = base_qs.values('trade_type').annotate(
            total=Count('id'),
            success=Count('id', filter=Q(executed_status='SUCCESS')),
            failed=Count('id', filter=Q(executed_status='FAILED')),
            cancelled=Count('id', filter=Q(executed_status='CANCELLED')),
            pending=Count('id', filter=Q(executed_status='PENDING')),
        ).order_by('trade_type')
        for item in type_qs:
            executed = item['success'] + item['failed']
            type_stats.append({
                'trade_type': item['trade_type'],
                'total': item['total'],
                'success': item['success'],
                'failed': item['failed'],
                'cancelled': item['cancelled'],
                'pending': item['pending'],
                'rate': round(item['success'] / executed * 100, 1) if executed > 0 else 0,
            })

        # 3. 失败原因分布
        failure_qs = base_qs.filter(
            executed_status='FAILED'
        ).values('remark').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        failure_reasons = [{'reason': item['remark'] or '未知', 'count': item['count']} for item in failure_qs]

        # 4. 平均执行延迟（仅统计有 updated_at 的成功/失败信号）
        from django.db.models import ExpressionWrapper, F, DurationField
        delay_qs = base_qs.filter(
            executed_status__in=['SUCCESS', 'FAILED'],
            updated_at__isnull=False,
        ).annotate(
            delay=ExpressionWrapper(
                F('updated_at') - F('created_at'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_delay_seconds=Avg(
                ExpressionWrapper(
                    F('updated_at') - F('created_at'),
                    output_field=DurationField()
                )
            )
        )
        avg_delay = None
        if delay_qs['avg_delay_seconds'] is not None:
            avg_delay = round(delay_qs['avg_delay_seconds'].total_seconds(), 1)

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': {
                'summary': {
                    'total': total,
                    'success': success_count,
                    'failed': failed_count,
                    'cancelled': cancelled_count,
                    'pending': pending_count,
                    'overall_rate': overall_rate,
                    'avg_execution_delay_seconds': avg_delay,
                },
                'by_type': type_stats,
                'failure_reasons': failure_reasons,
            },
        })
