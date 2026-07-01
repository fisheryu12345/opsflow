# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/3 003 0:30
@Remark: 角色管理 — using IAMRole (new unified role model)
"""
from django.db import transaction
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from iam.models.permission import IAMRole
from dvadmin.utils.json_response import SuccessResponse, DetailResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.validator import CustomUniqueValidator
from dvadmin.utils.viewset import CustomModelViewSet


class RoleSerializer(CustomModelSerializer):
    """
    角色-序列化器
    """

    class Meta:
        model = IAMRole
        fields = "__all__"
        read_only_fields = ["id"]


class RoleCreateUpdateSerializer(CustomModelSerializer):
    key = serializers.CharField(max_length=50,
                                validators=[CustomUniqueValidator(queryset=IAMRole.objects.all(), message="权限字符必须唯一")])
    name = serializers.CharField(max_length=50, validators=[CustomUniqueValidator(queryset=IAMRole.objects.all())])

    class Meta:
        model = IAMRole
        fields = '__all__'


class RoleViewSet(CustomModelViewSet):
    """
    角色管理接口
    list:查询
    create:新增
    update:修改
    retrieve:单例
    destroy:删除
    """
    queryset = IAMRole.objects.all()
    serializer_class = RoleSerializer
    create_serializer_class = RoleCreateUpdateSerializer
    update_serializer_class = RoleCreateUpdateSerializer
    search_fields = ['name', 'key']

    @action(methods=['GET', 'POST'], detail=True, permission_classes=[IsAuthenticated])
    def permissions(self, request, pk=None):
        """GET: return role's IAMPermission codenames. POST: bulk set."""
        from iam.models.permission import IAMRolePermission, IAMPermission
        role = self.get_object()
        if request.method == 'GET':
            codenames = IAMRolePermission.objects.filter(role=role).values_list(
                'permission__codename', flat=True
            )
            return SuccessResponse(data=sorted(codenames))
        # POST: bulk set permissions
        codenames = request.data.get('permissions', [])
        with transaction.atomic():
            IAMRolePermission.objects.filter(role=role).delete()
            for codename in codenames:
                perm = IAMPermission.objects.filter(codename=codename).first()
                if perm:
                    IAMRolePermission.objects.create(role=role, permission=perm)
        return DetailResponse(msg="权限保存成功")
