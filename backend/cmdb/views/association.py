# -*- coding: utf-8 -*-
"""Association views — 关联类型 & 模型关联 & 实例关联管理"""

from rest_framework import viewsets, status
from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.association import AssociationType, ModelAssociation
from ..serializers import (
    AssociationTypeSerializer,
    ModelAssociationSerializer,
    InstanceRelationSerializer,
)
from ..services.association_service import AssociationService


class AssociationTypeViewSet(CustomModelViewSet):
    """
    关联类型管理 (AssociationKind)

    list: 查询关联类型列表
    create: 创建关联类型(如 DEPLOY_TO)
    update: 修改关联类型
    destroy: 删除关联类型
    """
    model = AssociationType
    queryset = AssociationType.objects.all()
    serializer_class = AssociationTypeSerializer
    search_fields = ['asst_id', 'name']
    ordering = ['name']


class ModelAssociationViewSet(CustomModelViewSet):
    """
    模型关联管理

    list: 查询模型关联列表
    create: 定义哪些模型之间可以建立关联
    update: 修改关联定义
    destroy: 删除关联定义
    """
    model = ModelAssociation
    queryset = ModelAssociation.objects.all()
    serializer_class = ModelAssociationSerializer
    filter_fields = ['source_model', 'target_model', 'association_type', 'mapping']
    ordering = ['source_model', 'target_model']


class InstanceAssociationViewSet(viewsets.GenericViewSet):
    """
    实例关联管理（Neo4j 关系操作）

    create: 创建实例间关联
    destroy: 删除实例关联
    list: 查询实例关联列表
    neighbors: 获取实例的邻接节点（图遍历）
    """
    serializer_class = InstanceRelationSerializer
    service = AssociationService()

    def create(self, request):
        """创建实例间关联"""
        src_id = request.data.get('src_id')
        dst_id = request.data.get('dst_id')
        asst_type = request.data.get('asst_type')

        if not all([src_id, dst_id, asst_type]):
            return ErrorResponse(msg='缺少必要参数: src_id, dst_id, asst_type')

        try:
            rel = self.service.create_relation(src_id, dst_id, asst_type)
            return DetailResponse(data=rel, msg='关联创建成功',
                                  status=status.HTTP_201_CREATED)
        except Exception as e:
            return ErrorResponse(msg=f'创建关联失败: {str(e)}')

    def destroy(self, request, pk=None):
        """删除实例关联"""
        if not pk:
            return ErrorResponse(msg='缺少 rel_id')
        try:
            deleted = self.service.delete_relation(pk)
            if deleted:
                return DetailResponse(msg='关联已删除')
            return ErrorResponse(msg='关联不存在', code=4000, status=404)
        except Exception as e:
            return ErrorResponse(msg=f'删除关联失败: {str(e)}')

    def list(self, request):
        """查询实例关联"""
        params = {
            'instance_id': request.query_params.get('instance_id'),
            'asst_type': request.query_params.get('asst_type'),
            'src_model': request.query_params.get('src_model'),
            'dst_model': request.query_params.get('dst_model'),
            'page': int(request.query_params.get('page', 1)),
            'page_size': int(request.query_params.get('page_size', 20)),
        }
        result = self.service.list_relations(**params)
        return DetailResponse(data=result)

    @action(methods=['GET'], detail=False)
    def neighbors(self, request):
        """获取实例的邻接节点"""
        instance_id = request.query_params.get('instance_id')
        if not instance_id:
            return ErrorResponse(msg='缺少 instance_id')

        direction = request.query_params.get('direction', 'out')
        max_depth = int(request.query_params.get('max_depth', 1))
        asst_types = request.query_params.getlist('asst_types') or None

        result = self.service.get_neighbors(
            instance_id, direction=direction,
            max_depth=max_depth, asst_types=asst_types
        )
        return DetailResponse(data=result)
