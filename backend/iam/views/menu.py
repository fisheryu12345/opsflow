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
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse
from dvadmin.utils.serializers import CustomModelSerializer
from dvadmin.utils.viewset import CustomModelViewSet


class MenuSerializer(CustomModelSerializer):
    hasChild = serializers.SerializerMethodField()

    def get_hasChild(self, instance):
        return False  # Flat menu list, no hierarchy in current DB schema

    def get_name_display(self, obj):
        return obj.name

    class Meta:
        model = IAMMenu
        fields = "__all__"
        read_only_fields = ["id"]


class MenuCreateSerializer(CustomModelSerializer):
    name = serializers.CharField(required=False)

    class Meta:
        model = IAMMenu
        fields = "__all__"
        read_only_fields = ["id"]


class WebRouterSerializer(CustomModelSerializer):
    path = serializers.CharField(source="web_path")
    title = serializers.CharField(source="name")

    class Meta:
        model = IAMMenu
        fields = (
            'id', 'icon', 'sort', 'path', 'title', 'is_link', 'link_url',
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
        request.query_params._mutable = True
        params = request.query_params
        page = params.get('page', None)
        limit = params.get('limit', None)
        if page: del params['page']
        if limit: del params['limit']
        queryset = self.filter_queryset(self.queryset.all()) if not params else self.queryset.filter() if not params.get('parent') else self.queryset.filter()
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
