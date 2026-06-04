# -*- coding: utf-8 -*-
"""DynamicInstanceViewSet — 动态模型实例 CRUD（纯 Cypher 驱动）

所有模型类型的实例操作通过统一接口：
  /api/cmdb/instances/{model_code}/
"""

from rest_framework import viewsets, status

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.model_definition import ModelDefinition
from ..serializers.instance_serializers import DynamicInstanceSerializer
from ..services.node_service import NodeService


class DynamicInstanceViewSet(viewsets.GenericViewSet):
    """
    动态模型实例 CRUD

    根据 URL 中的 model_code 动态确定模型类型。
    所有操作通过 NodeService（纯 Cypher）执行。

    create: 创建实例
    list: 查询实例列表（支持过滤、分页、搜索）
    retrieve: 实例详情
    update: 全量更新实例
    partial_update: 部分更新实例
    destroy: 删除实例
    """
    serializer_class = DynamicInstanceSerializer

    def get_model_code(self):
        """从 URL 参数获取 model_code"""
        return self.kwargs.get('model_code')

    def get_service(self):
        return NodeService(self.get_model_code())

    def get_field_defs(self):
        """获取当前模型的字段定义列表（给序列化器用）"""
        try:
            model_def = ModelDefinition.objects.get(code=self.get_model_code())
            return list(model_def.fields.all().values(
                'name', 'label', 'field_type', 'required', 'options'
            ))
        except ModelDefinition.DoesNotExist:
            return []

    def get_serializer(self, *args, **kwargs):
        kwargs['field_defs'] = self.get_field_defs()
        return super().get_serializer(*args, **kwargs)

    def create(self, request, **kwargs):
        """创建实例"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = self.get_service().create(serializer.validated_data)
            out_serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=out_serializer.data, msg='创建成功',
                                  status=status.HTTP_201_CREATED)
        except Exception as e:
            return ErrorResponse(msg=f'创建失败: {str(e)}')

    def list(self, request, **kwargs):
        """查询实例列表"""
        model_code = self.get_model_code()
        filters = {}
        for key, value in request.query_params.items():
            if key not in ('page', 'page_size', 'search', 'ordering'):
                filters[key] = value

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        order_by = request.query_params.get('ordering')

        svc = self.get_service()

        # 搜索模式 vs 过滤模式
        search_q = request.query_params.get('search', '')
        if search_q:
            items = svc.search(search_q, limit=page_size)
            return DetailResponse(data={
                'items': items,
                'total': len(items),
                'page': 1,
                'page_size': page_size,
            })

        result = svc.list(filters, page=page, page_size=page_size,
                          order_by=order_by)
        return DetailResponse(data=result)

    def retrieve(self, request, pk=None, **kwargs):
        """实例详情"""
        try:
            instance = self.get_service().retrieve(pk)
            if not instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)
            serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=serializer.data)
        except Exception as e:
            return ErrorResponse(msg=f'查询失败: {str(e)}')

    def update(self, request, pk=None, **kwargs):
        """全量更新实例"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = self.get_service().update(pk, serializer.validated_data)
            if not instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)
            out_serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=out_serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def partial_update(self, request, pk=None, **kwargs):
        """部分更新实例"""
        try:
            instance = self.get_service().update(pk, request.data)
            if not instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)
            serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def destroy(self, request, pk=None, **kwargs):
        """删除实例"""
        try:
            deleted = self.get_service().delete(pk)
            if deleted:
                return DetailResponse(msg='删除成功')
            return ErrorResponse(msg='实例不存在', code=4000, status=404)
        except Exception as e:
            return ErrorResponse(msg=f'删除失败: {str(e)}')
