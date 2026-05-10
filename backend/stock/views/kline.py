"""
K线数据视图集 — 提供K线数据查询和交易事件标记接口
"""
from decimal import Decimal
from datetime import date
from rest_framework import viewsets, mixins, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from stock.models import KlineData, DailyStrategySignal, ClosedPositionRecord
from stock.serializers.serializers import KlineDataSerializer
from stock.filters import validate_account_access


class KlineDataViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    【K线数据视图集】- 只读

    💡 用途：
    - 查询指定合约的日K线数据
    - 支持按日期范围、合约代码过滤
    - 用于前端ECharts K线图渲染

    📊 典型查询：
    - GET /api/kline-data/?symbol=SHFE.rb2410&date__gte=2024-01-01&date__lte=2024-12-31
    - GET /api/kline-data/?product_code=rb&date__gte=2024-06-01&ordering=date
    """
    queryset = KlineData.objects.all()
    serializer_class = KlineDataSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = {
        'symbol': ['exact'],
        'product_code': ['exact'],
        'exchange': ['exact'],
        'date': ['exact', 'gte', 'lte', 'range'],
    }

    search_fields = ['symbol', 'product_code']
    ordering_fields = ['date']
    ordering = ['date']
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'code': 2000,
            'msg': 'success',
            'data': serializer.data,
        })


class TradeMarkersView(viewsets.ViewSet):
    """
    【交易事件标记接口】

    根据账户+合约，返回入场、加仓、移仓、平仓四种事件标记，
    用于前端K线图上叠加显示。

    📊 请求：
    GET /api/kline-data/trade-markers/?account=1&symbol=SHFE.rb2410

    📊 返回：
    [
        {
            "date": "2024-03-15",
            "trade_type": "ENTRY",
            "price": 4850.00,
            "direction": 1,
            "label": "入场",
            "description": "开仓 1 Unit @ 4850.00"
        },
        ...
    ]

    💡 数据来源：
    - ENTRY:   DailyStrategySignal (trade_type=ENTRY, executed_status=SUCCESS)
    - ADD_ON:  DailyStrategySignal (trade_type=ADD_ON, executed_status=SUCCESS)
    - ROLLOVER: DailyStrategySignal (trade_type=ROLLOVER, executed_status=SUCCESS)
    - EXIT:    ClosedPositionRecord (已平仓记录)
    """
    permission_classes = [IsAuthenticated]

    # 交易类型映射（中文标签）
    TYPE_LABEL_MAP = {
        'ENTRY': '入场',
        'ADD_ON': '加仓',
        'ROLLOVER': '移仓',
        'EXIT': '平仓',
        'STOP_LOSS': '平仓',
    }

    # 方向映射
    DIRECTION_MAP = {1: '多头', -1: '空头'}

    def _get_signal_markers(self, account_id, product_code):
        """从 DailyStrategySignal 获取入场/加仓/移仓标记"""
        markers = []
        signals = list(DailyStrategySignal.objects.filter(
            account_id=account_id,
            product_code=product_code,
            executed_status='SUCCESS'
        ).exclude(trade_type='STOP_LOSS').values(
            'trade_date', 'trade_type', 'signal_direction',
            'donchian_upper', 'donchian_lower', 'contract_target_number', 'symbol'
        ))

        # 预取相关日期的K线收盘价（用于加仓/移仓标记）
        trade_dates = [s['trade_date'] for s in signals]
        close_prices = {
            k.date: float(k.close)
            for k in KlineData.objects.filter(
                product_code=product_code,
                date__in=trade_dates
            )
        }

        for s in signals:
            price = None
            if s['trade_type'] == 'ENTRY':
                if s['signal_direction'] == 1:
                    price = float(s['donchian_upper']) if s['donchian_upper'] else None
                elif s['signal_direction'] == -1:
                    price = float(s['donchian_lower']) if s['donchian_lower'] else None
                desc = f"{self.DIRECTION_MAP.get(s['signal_direction'], '')}开仓 {s['contract_target_number'] or 1} Unit"
            elif s['trade_type'] == 'ADD_ON':
                price = close_prices.get(s['trade_date'])
                desc = f"加仓 {s['contract_target_number'] or 1} Unit"
            elif s['trade_type'] == 'ROLLOVER':
                price = close_prices.get(s['trade_date'])
                desc = f"移仓换月"
            else:
                continue

            if price is not None:
                desc += f" @ {price:.2f}"

            markers.append({
                'date': s['trade_date'].isoformat(),
                'trade_type': s['trade_type'],
                'price': price,
                'direction': s['signal_direction'] or 0,
                'label': self.TYPE_LABEL_MAP.get(s['trade_type'], s['trade_type']),
                'description': desc,
            })

        return markers

    def _get_exit_markers(self, account_id, product_code):
        """从 ClosedPositionRecord 获取平仓标记"""
        markers = []
        closed = ClosedPositionRecord.objects.filter(
            account_id=account_id,
            product_code=product_code
        ).values('trade_date', 'direction', 'exit_price', 'volume', 'pnl', 'holding_days', 'symbol')

        for c in closed:
            direction_label = self.DIRECTION_MAP.get(c['direction'], '')
            price = float(c['exit_price']) if c['exit_price'] else None
            desc = f"{direction_label}平仓 {c['volume']}手"

            # 补充当前开仓的持仓标记；关闭的持仓不显示具体入场价格
            if price is not None:
                desc += f" @ {price:.2f}"

            if c['pnl'] is not None:
                pnl_val = float(c['pnl'])
                desc += f" 盈亏:{pnl_val:+.2f}"

            markers.append({
                'date': c['trade_date'].isoformat(),
                'trade_type': 'EXIT',
                'price': price,
                'direction': c['direction'] or 0,
                'label': '平仓',
                'description': desc,
            })

        return markers

    def list(self, request):
        account_id = request.query_params.get('account')
        product_code = request.query_params.get('product_code')

        if not account_id:
            return Response({
                'code': 4000,
                'msg': '缺少账户ID参数',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        if not product_code:
            return Response({
                'code': 4000,
                'msg': '缺少品种代码参数',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        if not validate_account_access(request.user, account_id):
            return Response({
                'code': 4003,
                'msg': '无权访问该账户',
                'data': []
            }, status=status.HTTP_403_FORBIDDEN)

        # 获取各种标记并合并
        signal_markers = self._get_signal_markers(account_id, product_code)
        exit_markers = self._get_exit_markers(account_id, product_code)
        all_markers = signal_markers + exit_markers

        # 按日期排序
        all_markers.sort(key=lambda m: m['date'])

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': all_markers,
        })


class ContractsForKlineView(viewsets.ViewSet):
    """
    【K线可用合约列表接口】

    返回当前用户有权限查看的合约列表（用于前端下拉选择器）
    前端通过 product_code 查询 KlineData 和 TradeMarkers

    📊 请求：
    GET /api/kline-data/available-contracts/?account=1
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        account_id = request.query_params.get('account')

        if not account_id:
            return Response({
                'code': 4000,
                'msg': '缺少账户ID参数',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        if not validate_account_access(request.user, account_id):
            return Response({
                'code': 4003,
                'msg': '无权访问该账户',
                'data': []
            }, status=status.HTTP_403_FORBIDDEN)

        from stock.models import AccountContractConfig, FullContractList

        # 获取该账户激活的品种
        active_product_codes = AccountContractConfig.objects.filter(
            account_id=account_id,
            is_active=True
        ).values_list('product_code', flat=True)

        # 获取这些品种对应的主力合约
        contracts = FullContractList.objects.filter(
            product_code__in=list(active_product_codes)
        ).values('symbol', 'product_code', 'name', 'exchange')

        data = []
        for c in contracts:
            data.append({
                'symbol': c['symbol'],
                'product_code': c['product_code'],
                'name': c['name'],
                'exchange': c['exchange'],
            })

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': data,
        })
