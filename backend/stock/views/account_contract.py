"""
账户交易品种配置视图集 — 用户选择自己交易的品种
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from stock.models import AccountContractConfig, FullContractList
from stock.serializers.serializers import AccountContractConfigSerializer
from stock.filters import UserAccountFilterBackend, get_user_account_ids, validate_account_access


class AccountContractConfigViewSet(viewsets.ModelViewSet):
    """
    账户交易品种配置视图集

    list:     获取当前账户已配置的品种列表
    create:   为新品种创建配置
    update:   修改配置（激活/停用）
    destroy:  删除配置

    toggle:   快速切换品种的启用状态
    available: 获取可选的全局合约列表
    """
    queryset = AccountContractConfig.objects.all()
    serializer_class = AccountContractConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_code', 'is_active', 'account']
    search_fields = ['product_code']
    ordering_fields = ['product_code', 'created_at']
    ordering = ['product_code']

    def get_queryset(self):
        """默认只返回当前用户首个账户的配置（多账户时前端可切换）"""
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        # 如果查询未指定 account，自动使用用户的首个账户
        if not self.request.query_params.get('account'):
            account_ids = get_user_account_ids(user)
            if account_ids:
                qs = qs.filter(account_id=account_ids[0])
        return qs

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """
        快速切换品种的启用状态

        Request: {"product_code": "rb", "account": 1}
        """
        product_code = request.data.get('product_code')
        account_id = request.data.get('account')

        if not product_code:
            return Response({'code': 4000, 'msg': '缺少品种代码参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 未指定账户时自动使用用户的首个账户
        if not account_id:
            account_ids = get_user_account_ids(request.user)
            if not account_ids:
                return Response({'code': 4000, 'msg': '无可用交易账户'}, status=status.HTTP_400_BAD_REQUEST)
            account_id = account_ids[0]

        if not validate_account_access(request.user, account_id):
            return Response({'code': 4003, 'msg': '无权访问该账户'}, status=status.HTTP_403_FORBIDDEN)

        config, created = AccountContractConfig.objects.get_or_create(
            account_id=account_id,
            product_code=product_code,
            defaults={'is_active': True}
        )

        if not created:
            config.is_active = not config.is_active
            config.save(update_fields=['is_active', 'updated_at'])

        serializer = self.get_serializer(config)
        return Response({
            'code': 2000,
            'msg': '操作成功',
            'data': serializer.data
        })

    @action(detail=False, methods=['post'])
    def batch_toggle(self, request):
        """
        批量激活/停用品种

        Request: {"product_codes": ["rb", "MA", ...], "active": true, "account": 1}
        """
        product_codes = request.data.get('product_codes', [])
        active = request.data.get('active', True)
        account_id = request.data.get('account')

        if not product_codes:
            return Response({'code': 4000, 'msg': '缺少品种代码列表'}, status=status.HTTP_400_BAD_REQUEST)

        if not account_id:
            account_ids = get_user_account_ids(request.user)
            if not account_ids:
                return Response({'code': 4000, 'msg': '无可用交易账户'}, status=status.HTTP_400_BAD_REQUEST)
            account_id = account_ids[0]

        if not validate_account_access(request.user, account_id):
            return Response({'code': 4003, 'msg': '无权访问该账户'}, status=status.HTTP_403_FORBIDDEN)

        for code in product_codes:
            config, created = AccountContractConfig.objects.get_or_create(
                account_id=account_id,
                product_code=code,
                defaults={'is_active': active}
            )
            if not created and config.is_active != active:
                config.is_active = active
                config.save(update_fields=['is_active', 'updated_at'])

        return Response({
            'code': 2000,
            'msg': f'已{"激活" if active else "停用"} {len(product_codes)} 个品种',
        })

    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        获取可选的全局合约列表（来自 FullContractList，master list）

        返回当前用户有权限看到的合约列表，标记哪些已激活。
        """
        account_id = request.query_params.get('account')
        if not account_id:
            account_ids = get_user_account_ids(request.user)
            if not account_ids:
                return Response({'code': 2000, 'msg': 'success', 'data': []})
            account_id = account_ids[0]

        if not validate_account_access(request.user, account_id):
            return Response({'code': 4003, 'msg': '无权访问该账户', 'data': []}, status=status.HTTP_403_FORBIDDEN)

        # 全局合约列表（不按 is_active 过滤，让用户自己选择要激活哪些品种）
        contracts = FullContractList.objects.values(
            'product_code', 'exchange', 'symbol', 'name', 'category'
        ).distinct().order_by('product_code')

        # 当前账户已激活的品种
        active_codes = set(
            AccountContractConfig.objects.filter(
                account_id=account_id, is_active=True
            ).values_list('product_code', flat=True)
        )

        result = []
        for c in contracts:
            result.append({
                'product_code': c['product_code'],
                'exchange': c['exchange'],
                'symbol': c['symbol'],
                'name': c['name'],
                'category': c['category'],
                'is_active': c['product_code'] in active_codes,
            })

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': result
        })
