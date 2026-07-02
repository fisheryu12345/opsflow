# -*- coding: utf-8 -*-
"""DynamicInstanceViewSet — 动态模型实例 CRUD（纯 Cypher 驱动）

所有模型类型的实例操作通过统一接口：
  /api/cmdb/instances/{model_code}/

集成变更历史追踪：
  - perform_create → track_create
  - perform_update / partial_update → track_update
  - perform_destroy → track_delete

提供 change_history action 查询实例变更记录。
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action

from common.utils.json_response import DetailResponse, ErrorResponse

from ..models.model_definition import ModelDefinition
from ..models.change_log import ChangeLog
from ..serializers.instance_serializers import DynamicInstanceSerializer
from ..services.node_service import NodeService
from ..services.change_tracker import track_create, track_update, track_delete


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
    change_history: 查询实例变更历史
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

    def get_operator(self, request):
        """从 request 获取当前操作人"""
        if request.user and request.user.username:
            return request.user.username
        return 'system'

    def create(self, request, **kwargs):
        """创建实例"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = self.get_service().create(serializer.validated_data)
            # 记录变更
            track_create(instance, self.get_model_code(),
                         operator=self.get_operator(request))
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
            # 更新前获取旧数据
            old_instance = self.get_service().retrieve(pk)
            if not old_instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)

            instance = self.get_service().update(pk, serializer.validated_data)
            if not instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)

            # 记录变更
            track_update(old_instance, instance, self.get_model_code(),
                         operator=self.get_operator(request))

            out_serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=out_serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def partial_update(self, request, pk=None, **kwargs):
        """部分更新实例"""
        try:
            # 更新前获取旧数据
            old_instance = self.get_service().retrieve(pk)
            if not old_instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)

            instance = self.get_service().update(pk, request.data)
            if not instance:
                return ErrorResponse(msg='实例不存在', code=4000, status=404)

            # 记录变更
            track_update(old_instance, instance, self.get_model_code(),
                         operator=self.get_operator(request))

            serializer = self.get_serializer(instance=instance)
            return DetailResponse(data=serializer.data, msg='更新成功')
        except Exception as e:
            return ErrorResponse(msg=f'更新失败: {str(e)}')

    def destroy(self, request, pk=None, **kwargs):
        """删除实例"""
        try:
            # 删除前获取快照用于记录
            old_instance = self.get_service().retrieve(pk)

            deleted = self.get_service().delete(pk)
            if deleted:
                # 记录变更
                track_delete(pk, self.get_model_code(),
                             operator=self.get_operator(request),
                             instance_snapshot=old_instance)
                return DetailResponse(msg='删除成功')
            return ErrorResponse(msg='实例不存在', code=4000, status=404)
        except Exception as e:
            return ErrorResponse(msg=f'删除失败: {str(e)}')

    @action(detail=True, methods=['get'])
    def change_history(self, request, pk=None, **kwargs):
        """查询实例变更历史

        GET /api/cmdb/instances/{model_code}/{pk}/change_history/
        Query params:
          - action: create/update/delete
          - start_date: 开始日期 (YYYY-MM-DD)
          - end_date: 结束日期 (YYYY-MM-DD)
          - operator: 操作人（模糊匹配）
          - page: 页码 (default 1)
          - page_size: 每页条数 (default 20)
        """
        model_code = self.get_model_code()

        queryset = ChangeLog.objects.filter(
            model_code=model_code,
            instance_id=pk,
        )

        # 过滤条件
        q_action = request.query_params.get('action')
        if q_action:
            queryset = queryset.filter(action=q_action)

        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(create_datetime__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(create_datetime__lte=end_date + 'T23:59:59')

        q_operator = request.query_params.get('operator')
        if q_operator:
            queryset = queryset.filter(operator__icontains=q_operator)

        # 分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        total = queryset.count()

        offset = (page - 1) * page_size
        items = list(queryset[offset:offset + page_size].values(
            'id', 'action', 'changes', 'operator', 'create_datetime'
        ))

        return DetailResponse(data={
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        })
