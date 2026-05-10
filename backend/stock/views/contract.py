"""
期货合约列表视图集
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.models import FullContractList
from stock.serializers.serializers import FullContractListSerializer
from stock.filters import UserAccountFilterBackend, get_user_account_ids


class FullContractListViewSet(viewsets.ModelViewSet):
    """
    期货合约列表视图集 - 支持增删改查
    """
    queryset = FullContractList.objects.all()
    serializer_class = FullContractListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 精确过滤字段
    filterset_fields = {
        'exchange': ['exact'],
        'product_code': ['exact', 'icontains'],
        'category': ['exact', 'icontains'],
    }
    
    # 搜索字段（模糊搜索）
    search_fields = [
        'symbol',
        'product_code',
        'name',
        'exchange',
        'category',
    ]
    
    # 排序字段
    ordering_fields = [
        'exchange',
        'product_code',
        'symbol',
        'category',
        'volume_multiple',
        'price_tick',
        'created_at',
        'updated_at',
    ]
    
    # 默认排序
    ordering = ['exchange', 'product_code']

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        获取合约统计信息

        Returns:
        {
            "total": 总数,
            "by_exchange": {按交易所统计},
        }
        """
        from django.db.models import Count

        base_qs = self.filter_queryset(self.get_queryset())
        total = base_qs.count()

        exchange_labels = {
            'SHFE': '上期所', 'DCE': '大商所', 'CZCE': '郑商所',
            'CFFEX': '中金所', 'GFEX': '广期所',
        }
        by_exchange = base_qs.values('exchange').annotate(
            count=Count('id')
        ).order_by('exchange')

        by_exchange_list = []
        for item in by_exchange:
            by_exchange_list.append({
                'label': exchange_labels.get(item['exchange'], item['exchange']),
                'count': item['count']
            })

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': {
                'total': total,
                'by_exchange': by_exchange_list,
            }
        })
