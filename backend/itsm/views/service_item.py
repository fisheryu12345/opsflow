# -*- coding: utf-8 -*-
"""ServiceItem views — 服务目录 CRUD + 提交申请"""

import logging

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.utils.json_response import DetailResponse, ErrorResponse
from iam.permissions import TenantPermission

from itsm.models import ServiceItem, WorkflowVersion, Ticket
from itsm.serializers import (
    ServiceItemSerializer,
    ServiceItemCreateUpdateSerializer,
    ServiceItemSubmitSerializer,
)
from itsm.views.workflow_views import ItsmProjectViewSet
from itsm.services.itsm_engine import ITSMEngine

logger = logging.getLogger(__name__)


class ServiceItemViewSet(ItsmProjectViewSet):
    """服务目录管理 — 服务项 CRUD + 提交申请"""
    model = ServiceItem
    queryset = ServiceItem.objects.all()
    serializer_class = ServiceItemSerializer
    filter_fields = ['mode', 'is_active', 'category', 'visible_to']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ServiceItemCreateUpdateSerializer
        return ServiceItemSerializer

    def get_queryset(self):
        """普通用户只看可见且已启用的服务"""
        qs = super().get_queryset()
        user = self.request.user
        # Admin 可以看到所有
        if user.is_superuser:
            return qs
        if self.action == 'list' and not self.request.query_params.get('include_inactive'):
            qs = qs.filter(is_active=True)
        return qs

    @action(methods=['POST'], detail=True)
    def submit(self, request, pk=None):
        """用户提交服务申请"""
        service_item = self.get_object()
        if not service_item.is_active:
            return ErrorResponse(msg="该服务已停用")

        serializer = ServiceItemSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        form_data = serializer.validated_data.get('form_data', {})
        title = serializer.validated_data.get('title') or service_item.name
        priority = serializer.validated_data.get('priority', 'P3')

        try:
            if service_item.mode == 'flow':
                ticket = self._submit_flow(service_item, title, form_data, priority, request.user)
            else:
                ticket = self._submit_lightweight(service_item, title, form_data, priority, request.user)
            return DetailResponse(data={
                'ticket_id': ticket.id,
                'sn': ticket.sn,
            }, msg="服务申请已提交")
        except Exception as e:
            logger.exception(f"ServiceItem submit failed: service_item={service_item.id}")
            return ErrorResponse(msg=f"提交失败: {str(e)}")

    def _submit_flow(self, service_item, title, form_data, priority, user):
        """流程驱动模式 — 创建 WorkflowVersion + Ticket + 启动 Pipeline"""
        workflow = service_item.workflow
        if not workflow:
            raise ValueError("流程驱动模式未绑定 Workflow")

        # 创建部署快照
        version = workflow.create_version(operator=user.id)

        # 合并服务项自定义字段到提单节点
        if service_item.form_fields:
            states = version.states or {}
            for key, state_data in states.items():
                if state_data.get('type') == 'NORMAL':
                    existing = state_data.get('fields') or []
                    merged = list(existing)
                    existing_keys = {f.get('key') for f in existing}
                    for f in service_item.form_fields:
                        if f.get('key') not in existing_keys:
                            merged.append(f)
                    state_data['fields'] = merged
                    states[key] = state_data
            version.states = states
            version.save(update_fields=['states'])

        # 创建工单
        ticket = Ticket.objects.create(
            workflow_version=version,
            project=service_item.category.project if service_item.category else None,
            itsm_type=workflow.itsm_type,
            title=title,
            priority=priority,
            creator=user.id,
            meta={
                'service_item_id': service_item.id,
                'service_item_name': service_item.name,
                'form_data': form_data,
            },
        )
        ticket.do_after_create()

        # 启动 Pipeline
        pipeline_id, tree = ITSMEngine(ticket).run(version)
        ticket.pipeline_id = pipeline_id
        ticket.current_status = 'running'
        ticket.save(update_fields=['pipeline_id', 'current_status'])

        return ticket

    def _submit_lightweight(self, service_item, title, form_data, priority, user):
        """快捷服务模式 — 创建轻量 Ticket 并分派"""
        ticket = Ticket.objects.create(
            project=service_item.category.project if service_item.category else None,
            itsm_type='request',
            title=title,
            priority=priority,
            current_status='assigned',
            creator=user.id,
            meta={
                'service_item_id': service_item.id,
                'service_item_name': service_item.name,
                'form_data': form_data,
                'is_lightweight': True,
            },
        )
        # 按配置分派到默认处理人
        if service_item.default_assignee:
            ticket.meta['assignee'] = service_item.default_assignee
            ticket.save(update_fields=['meta'])

        return ticket
