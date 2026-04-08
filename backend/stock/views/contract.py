"""
期货合约列表视图集
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.models import FullContractList
from stock.serializers.contract import (
    FullContractListSerializer,
    FullContractListCreateSerializer,
    FullContractListUpdateSerializer,
    FullContractListSimpleSerializer,
)


class FullContractListViewSet(viewsets.ModelViewSet):
    """
    期货合约列表视图集
    
    provide:
        - list: 获取合约列表（支持筛选、搜索、排序）
        - retrieve: 获取单个合约详情
        - create: 创建新合约
        - update: 更新合约信息
        - partial_update: 部分更新合约
        - destroy: 删除合约
        - activate: 批量激活合约
        - deactivate: 批量停用合约
        - statistics: 获取合约统计信息
    """
    queryset = FullContractList.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 精确过滤字段
    filterset_fields = {
        'exchange': ['exact'],  # 交易所：精确匹配
        'product_code': ['exact', 'icontains'],  # 品种代码：精确或模糊
        'is_active': ['exact'],  # 是否激活：精确匹配
        'allow_open': ['exact'],  # 是否允许开仓：精确匹配
        'sector': ['exact', 'icontains'],  # 板块：精确或模糊
        'category': ['exact', 'icontains'],  # 分类：精确或模糊
        'need_rollover': ['exact'],  # 是否需要移仓：精确匹配
    }
    
    # 搜索字段（模糊搜索）
    search_fields = [
        'symbol',
        'product_code',
        'name',
        'exchange',
        'sector',
        'category',
    ]
    
    # 排序字段（支持升序/降序）
    ordering_fields = [
        'exchange',           # 按交易所排序
        'product_code',       # 按品种代码排序
        'symbol',             # 按主力合约排序
        'sector',             # 按板块排序
        'category',           # 按分类排序
        'volume_multiple',    # 按合约乘数排序
        'price_tick',         # 按最小变动价位排序
        'margin_ratio',       # 按保证金比例排序
        'is_active',          # 按激活状态排序
        'created_at',         # 按创建时间排序
        'updated_at',         # 按更新时间排序
    ]
    
    # 默认排序：先按交易所，再按品种代码
    ordering = ['exchange', 'product_code']

    def get_serializer_class(self):
        """根据动作选择不同的序列化器"""
        if self.action == 'list':
            return FullContractListSerializer
        elif self.action == 'create':
            return FullContractListCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FullContractListUpdateSerializer
        elif self.action == 'simple_list':
            return FullContractListSimpleSerializer
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

    @action(detail=False, methods=['get'], url_path='sectors')
    def get_sectors(self, request):
        """
        获取所有板块列表（去重）
        
        Query params:
        - exchange: 可选，按交易所过滤
        
        Returns:
        [
            {"value": "黑色金属", "count": 5},
            {"value": "化工", "count": 12},
            ...
        ]
        """
        from django.db.models import Count
        
        queryset = FullContractList.objects
        
        # 如果指定了交易所，则只返回该交易所的板块
        exchange = request.query_params.get('exchange')
        if exchange:
            queryset = queryset.filter(exchange=exchange)
        
        sectors = queryset.values('sector').annotate(
            count=Count('id')
        ).order_by('-count')  # 按数量降序排列
        
        # 过滤掉空值
        result = [
            {'value': item['sector'], 'count': item['count']}
            for item in sectors
            if item['sector']  # 排除空值
        ]
        
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
            "by_sector": {按板块统计}
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
        
        # 按板块统计
        by_sector = FullContractList.objects.values('sector').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'by_exchange': list(by_exchange),
            'by_sector': list(by_sector),
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
