# -*- coding: utf-8 -*-
"""Base ViewSet for Neo4j node operations

所有 CMDB Neo4j ViewSet 继承此类，提供标准 CRUD 和统一响应格式。
"""

from rest_framework import viewsets, status
from rest_framework.response import Response

from dvadmin.utils.json_response import DetailResponse, ErrorResponse


class Neo4jViewSet(viewsets.GenericViewSet):
    """
    Neo4j 节点 CRUD 基类

    提供 create / list / retrieve / update / destroy 标准操作。
    子类需设置:
    - model_class: neomodel StructuredNode 子类
    - serializer_class: DRF Serializer
    """
    model_class = None
    serializer_class = None
    search_fields = []
    ordering = []

    def get_queryset(self):
        """返回排序后的节点列表"""
        qs = self.model_class.nodes.all()
        if isinstance(qs, list):
            return qs
        return list(qs)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        # 搜索过滤
        query = request.query_params.get('search', '')
        if query and self.search_fields:
            queryset = [
                obj for obj in queryset
                if any(query.lower() in str(getattr(obj, f, '')).lower()
                       for f in self.search_fields)
            ]
        serializer = self.get_serializer(queryset, many=True)
        return DetailResponse(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.model_class.nodes.get(element_id=kwargs.get('pk'))
        except self.model_class.DoesNotExist:
            # Fallback: try primary key field
            pk_field = getattr(self.model_class, '__primaryproperty__', 'element_id')
            try:
                instance = self.model_class.nodes.get(**{pk_field: kwargs.get('pk')})
            except (self.model_class.DoesNotExist, Exception):
                return ErrorResponse(msg='节点不存在', code=4000, status=404)
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = self.model_class(**serializer.validated_data).save()
            out_serializer = self.get_serializer(instance)
            return DetailResponse(data=out_serializer.data, msg='创建成功',
                                  status=status.HTTP_201_CREATED)
        except Exception as e:
            return ErrorResponse(msg=f'创建失败: {str(e)}')

    def update(self, request, *args, **kwargs):
        try:
            pk_field = self._get_pk_field()
            instance = self.model_class.nodes.get(**{pk_field: kwargs.get('pk')})
        except self.model_class.DoesNotExist:
            return ErrorResponse(msg='节点不存在', code=4000, status=404)

        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        try:
            for key, value in serializer.validated_data.items():
                setattr(instance, key, value)
            instance.save()
            out_serializer = self.get_serializer(instance)
            return DetailResponse(data=out_serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def partial_update(self, request, *args, **kwargs):
        try:
            pk_field = self._get_pk_field()
            instance = self.model_class.nodes.get(**{pk_field: kwargs.get('pk')})
        except self.model_class.DoesNotExist:
            return ErrorResponse(msg='节点不存在', code=4000, status=404)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            for key, value in serializer.validated_data.items():
                setattr(instance, key, value)
            instance.save()
            out_serializer = self.get_serializer(instance)
            return DetailResponse(data=out_serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def destroy(self, request, *args, **kwargs):
        try:
            pk_field = self._get_pk_field()
            instance = self.model_class.nodes.get(**{pk_field: kwargs.get('pk')})
        except self.model_class.DoesNotExist:
            return ErrorResponse(msg='节点不存在', code=4000, status=404)
        try:
            instance.delete()
            return DetailResponse(msg='删除成功')
        except Exception as e:
            return ErrorResponse(msg=f'删除失败: {str(e)}')

    def _get_pk_field(self):
        """获取主键字段名"""
        for attr in dir(self.model_class):
            if not attr.startswith('_'):
                prop = getattr(self.model_class, attr, None)
                if hasattr(prop, 'is_unique_id') and prop.is_unique_id:
                    return attr
        return 'element_id'
