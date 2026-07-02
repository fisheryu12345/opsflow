# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/6/1 001 22:38
@Remark: 菜单模块 — using IAMMenu (migrated from dvadmin Menu)
"""
from django.db import models
from rest_framework import serializers
from rest_framework.decorators import action

from iam.models.page_config import IAMMenu
from common.utils.json_response import SuccessResponse, ErrorResponse
from common.utils.serializers import CustomModelSerializer
from common.utils.viewset import CustomModelViewSet


class MenuSerializer(CustomModelSerializer):
    hasChild = serializers.SerializerMethodField()
    name_display = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    def get_hasChild(self, instance):
        return IAMMenu.objects.filter(dept_belong_id=str(instance.id)).exists()

    def get_name_display(self, obj):
        return obj.name

    def get_parent(self, instance):
        if not instance.dept_belong_id:
            return None
        try:
            return int(instance.dept_belong_id)
        except (ValueError, TypeError):
            return instance.dept_belong_id

    class Meta:
        model = IAMMenu
        fields = "__all__"
        read_only_fields = ["id"]


class MenuCreateSerializer(CustomModelSerializer):
    name = serializers.CharField(required=False)
    parent = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)

    class Meta:
        model = IAMMenu
        fields = [
            'id', 'name', 'name_en', 'icon', 'sort', 'parent',
            'web_path', 'component', 'component_name',
            'is_catalog', 'is_link', 'link_url', 'is_iframe', 'is_affix',
            'status', 'visible', 'cache',
            'description', 'app',
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        parent = validated_data.pop('parent', None)
        if parent and str(parent).strip():
            validated_data['dept_belong_id'] = str(parent)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        parent = validated_data.pop('parent', None)
        if parent and str(parent).strip():
            validated_data['dept_belong_id'] = str(parent)
        elif 'parent' in validated_data:
            validated_data['dept_belong_id'] = None
        return super().update(instance, validated_data)


class WebRouterSerializer(CustomModelSerializer):
    path = serializers.CharField(source="web_path")
    title = serializers.CharField(source="name")
    parent = serializers.SerializerMethodField()

    def get_parent(self, instance):
        if not instance.dept_belong_id:
            return None
        try:
            return int(instance.dept_belong_id)
        except (ValueError, TypeError):
            return instance.dept_belong_id

    class Meta:
        model = IAMMenu
        fields = (
            'id', 'icon', 'sort', 'parent', 'path', 'title', 'is_link', 'link_url',
            'is_catalog', 'web_path', 'component', 'component_name',
            'cache', 'visible', 'is_iframe', 'status')
        read_only_fields = ["id"]


class MenuViewSet(CustomModelViewSet):
    queryset = IAMMenu.objects.all()
    serializer_class = MenuSerializer
    create_serializer_class = MenuCreateSerializer
    update_serializer_class = MenuCreateSerializer
    search_fields = ['name', 'status']
    filter_fields = ['name', 'status', 'is_link', 'visible', 'cache', 'is_catalog']

    def list(self, request):
        params = request.query_params.copy()
        parent_val = params.pop('parent', [None])[0]
        page = params.pop('page', [None])[0]
        limit = params.pop('limit', [None])[0]
        if parent_val is not None:
            queryset = self.queryset.filter(dept_belong_id=str(parent_val))
        elif params:
            queryset = self.filter_queryset(self.queryset.all())
        else:
            queryset = self.queryset.all()
        serializer = MenuSerializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data)

    @action(methods=['GET'], detail=False, permission_classes=[])
    def web_router(self, request):
        """返回当前用户可见的菜单列表 — 所有用户可见，功能权限由 PageTab/PageButton 控制"""
        queryset = self.queryset.filter(visible=True)
        serializer = WebRouterSerializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, total=len(serializer.data), msg="获取成功")

    @action(methods=['GET'], detail=False, permission_classes=[])
    def get_all_menu(self, request):
        """获取所有菜单（管理用）"""
        queryset = self.queryset.all()
        serializer = WebRouterSerializer(queryset, many=True, request=request)
        return SuccessResponse(data=serializer.data, total=len(serializer.data), msg="获取成功")

    @action(methods=['POST'], detail=False, permission_classes=[])
    def move_up(self, request):
        menu_id = request.data.get('menu_id')
        try:
            menu = IAMMenu.objects.get(id=menu_id)
        except IAMMenu.DoesNotExist:
            return ErrorResponse(msg="菜单不存在")
        previous_menu = IAMMenu.objects.filter(sort__lt=menu.sort).order_by('-sort').first()
        if previous_menu:
            previous_menu.sort, menu.sort = menu.sort, previous_menu.sort
            previous_menu.save()
            menu.save()
        return SuccessResponse(data=[], msg="上移成功")

    @action(methods=['POST'], detail=False, permission_classes=[])
    def move_down(self, request):
        menu_id = request.data['menu_id']
        try:
            menu = IAMMenu.objects.get(id=menu_id)
        except IAMMenu.DoesNotExist:
            return ErrorResponse(msg="菜单不存在")
        next_menu = IAMMenu.objects.filter(sort__gt=menu.sort).order_by('sort').first()
        if next_menu:
            next_menu.sort, menu.sort = menu.sort, next_menu.sort
            next_menu.save()
            menu.save()
        return SuccessResponse(data=[], msg="下移成功")
