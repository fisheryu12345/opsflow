"""
期货合约列表视图集
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.models import FullContractList
from stock.serializers.serializers import FullContractListSerializer


class FullContractListViewSet(viewsets.ModelViewSet):
    """
    期货合约列表视图集 - 支持增删改查
    """
    queryset = FullContractList.objects.all()
    serializer_class = FullContractListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 精确过滤字段
    filterset_fields = {
        'exchange': ['exact'],
        'product_code': ['exact', 'icontains'],
        'is_active': ['exact'],
        'allow_open': ['exact'],
        'category': ['exact', 'icontains'],
        # 'need_rollover': ['exact'],
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
        'is_active',
        'created_at',
        'updated_at',
    ]
    
    # 默认排序
    ordering = ['exchange', 'product_code']

    def get_serializer_class(self):
        """根据动作选择不同的序列化器"""
        # 目前所有操作都使用同一个序列化器
        return FullContractListSerializer

    def get_queryset(self):
        """优化查询性能"""
        queryset = super().get_queryset()
        # 只在列表视图时进行优化
        if self.action == 'list':
            queryset = queryset.select_related()
        return queryset

    @action(detail=False, methods=['get'], url_path='exchanges')
    def get_exchanges(self, request):
        """
        获取所有交易所列表（去重）
        
        Returns:
        [
            {"value": "SHFE", "label": "上期所", "count": 17},
            {"value": "DCE", "label": "大商所", "count": 17},
            ...
        ]
        """
        from django.db.models import Count
        
        # 交易所中文映射
        exchange_labels = {
            'SHFE': '上期所',
            'DCE': '大商所',
            'CZCE': '郑商所',
            'CFFEX': '中金所',
            'GFEX': '广期所',
        }
        
        exchanges = FullContractList.objects.values('exchange').annotate(
            count=Count('id')
        ).order_by('exchange')
        
        result = []
        for item in exchanges:
            result.append({
                'value': item['exchange'],
                'label': exchange_labels.get(item['exchange'], item['exchange']),
                'count': item['count']
            })
        
        return Response(result)


    @action(detail=False, methods=['post'])
    def activate(self, request):
        """
        批量激活合约
        
        Request body:
        {
            "ids": [1, 2, 3]  # 合约ID列表
        }
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': '请提供合约ID列表'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        count = FullContractList.objects.filter(id__in=ids).update(is_active=True)
        
        return Response({
            'message': f'成功激活 {count} 个合约',
            'count': count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def deactivate(self, request):
        """
        批量停用合约
        
        Request body:
        {
            "ids": [1, 2, 3]  # 合约ID列表
        }
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response(
                {'error': '请提供合约ID列表'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        count = FullContractList.objects.filter(id__in=ids).update(is_active=False)
        
        return Response({
            'message': f'成功停用 {count} 个合约',
            'count': count
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        获取合约统计信息
        
        Returns:
        {
            "total": 总数,
            "active": 激活数量,
            "inactive": 停用数量,
            "by_exchange": {按交易所统计},
        }
        """
        from django.db.models import Count
        
        total = FullContractList.objects.count()
        active = FullContractList.objects.filter(is_active=True).count()
        inactive = total - active
        
        # 按交易所统计
        by_exchange = FullContractList.objects.values('exchange').annotate(
            count=Count('id')
        ).order_by('exchange')
        

        
        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'by_exchange': list(by_exchange),
        })

    @action(detail=False, methods=['get'], url_path='simple')
    def simple_list(self, request):
        """
        获取简化版合约列表（用于下拉选择）
        
        Query params:
        - exchange: 交易所过滤
        - is_active: 是否只返回激活的合约 (true/false)
        """
        queryset = self.get_queryset()
        
        # 默认只返回激活的合约
        is_active = request.query_params.get('is_active', 'true')
        if is_active.lower() == 'true':
            queryset = queryset.filter(is_active=True)
        
        # 交易所过滤
        exchange = request.query_params.get('exchange')
        if exchange:
            queryset = queryset.filter(exchange=exchange)
        
        queryset = queryset.order_by('exchange', 'product_code')
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        切换单个合约的激活状态
        """
        contract = self.get_object()
        contract.is_active = not contract.is_active
        contract.save(update_fields=['is_active', 'updated_at'])
        
        return Response({
            'message': f'合约 {contract.symbol} 已{"激活" if contract.is_active else "停用"}',
            'is_active': contract.is_active
        })
