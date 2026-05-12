"""
持仓状态视图集
"""
from decimal import Decimal
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django.db.models import OuterRef, Subquery, Sum, Max, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from stock.serializers.serializers import PositionStateSerializer
from stock.models import PositionState, FullContractList, DailyEquitySnapshot
from stock.filters import UserAccountFilterBackend, get_user_account_ids


class PositionStateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    策略持仓状态视图集 - 只读（数据由系统自动生成和维护）
    """
    queryset = PositionState.objects.annotate(
        volume_multiple=Subquery(
            FullContractList.objects.filter(product_code=OuterRef('product_code'))
            .values('volume_multiple')[:1]
        )
    )
    serializer_class = PositionStateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 精确过滤字段配置（使用字典格式以支持多种过滤类型）
    filterset_fields = {
        'account': ['exact'],
        'symbol': ['exact', 'icontains'],
        'product_code': ['exact', 'icontains'],
        'direction': ['exact'],
        'units': ['exact', 'gt', 'gte', 'lt', 'lte'],
        'contract_total_position': ['exact', 'gt', 'gte', 'lt', 'lte'],  # 支持大于、小于等范围查询
        'is_rollover_needed': ['exact'],
    }
    
    # 搜索字段（模糊搜索）
    search_fields = ['symbol', 'product_code']
    ordering_fields = '__all__'

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # 确定账户过滤范围（与 UserAccountFilterBackend 一致）
        account_id = request.query_params.get('account')
        account_filter = Q()
        if account_id:
            account_filter = Q(account_id=account_id)
        elif not request.user.is_superuser:
            account_ids = get_user_account_ids(request.user)
            if account_ids:
                account_filter = Q(account_id__in=account_ids)
            else:
                account_filter = Q(pk__in=[])  # 无可访问账户 → 空

        # 今日手续费（来自日权益快照）
        today = timezone.now().date()
        total_commission = DailyEquitySnapshot.objects.filter(
            account_filter, trade_date=today
        ).aggregate(total=Sum('commission'))['total'] or Decimal('0')
        response.data['today_commission'] = str(total_commission.quantize(Decimal('0.01')))

        # 数据最新更新时间（取所有可访问持仓中最大的 last_update_time）
        last_update = PositionState.objects.filter(account_filter).aggregate(
            max_time=Max('last_update_time')
        )['max_time']
        response.data['last_data_update_time'] = last_update

        return response
