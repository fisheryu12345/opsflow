"""
用户账户数据隔离过滤器

自动将 queryset 限制为当前用户有权访问的账户数据。
超级管理员可以访问所有数据。

对于 account FK 为 null=True 的模型（如 FullContractList），
null 记录视为全局共享，所有用户可见。
"""
from rest_framework import filters
from django.db.models import Q
from stock.models import TradingAccount


def get_user_account_ids(user):
    """
    获取当前用户有权限访问的账户ID列表。
    返回 None 表示所有账户均可访问（超级管理员）。
    返回空列表表示无可用账户。
    """
    if user.is_superuser:
        return None
    return list(TradingAccount.objects.filter(user=user).values_list('id', flat=True))


def validate_account_access(user, account_id):
    """
    验证当前用户是否有权限访问指定账户。
    供 Pattern D 自定义视图手动调用。
    返回 True/False。
    """
    if user.is_superuser:
        return True
    return TradingAccount.objects.filter(user=user, id=account_id).exists()


class UserAccountFilterBackend(filters.BaseFilterBackend):
    """
    用户账户数据隔离过滤器

    添加到 ViewSet 的 filter_backends 后，自动将查询范围限制为
    当前用户有权限访问的账户数据。

    使用方式:
        filter_backends = [DjangoFilterBackend, UserAccountFilterBackend, ...]
    """

    def filter_queryset(self, request, queryset, view):
        user = request.user

        # 未认证用户 → 空结果
        if not user or user.is_anonymous:
            return queryset.model.objects.none() if hasattr(queryset.model, 'objects') else queryset.none()

        # 超级管理员不受限
        if user.is_superuser:
            return queryset

        user_account_ids = get_user_account_ids(user)

        # 该用户无可用账户 → 空结果
        if not user_account_ids:
            return queryset.model.objects.none() if hasattr(queryset.model, 'objects') else queryset.none()

        model = queryset.model

        # TradingAccount 本身
        if model == TradingAccount:
            return queryset.filter(id__in=user_account_ids)

        # 其他有 account FK 的模型
        if hasattr(model, 'account'):
            field = model._meta.get_field('account')
            if field.null:
                # null=True 表示全局共享记录（如 FullContractList），所有用户均可见
                return queryset.filter(Q(account_id__in=user_account_ids) | Q(account__isnull=True))
            return queryset.filter(account_id__in=user_account_ids)

        return queryset
