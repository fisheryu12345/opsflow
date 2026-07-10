# -*- coding: utf-8 -*-
"""ServiceItem views — 服务目录 CRUD + 提交申请"""

import logging

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.utils.json_response import DetailResponse, ErrorResponse
from iam.models import Project
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
        logger.info(f'[ServiceItem.submit] request.data keys={list(request.data.keys())} title={request.data.get("title")!r}')

        form_data = serializer.validated_data.get('form_data', {})
        title = serializer.validated_data.get('title') or service_item.name
        priority = serializer.validated_data.get('priority', 'P3')
        logger.info(f'[ServiceItem.submit] validated: title={title!r} priority={priority!r} form_data_keys={list(form_data.keys()) if form_data else []}')

        # Resolve project from request context (not from service_item.category)
        project_id = request.query_params.get('project_id')
        try:
            if service_item.mode == 'flow':
                ticket = self._submit_flow(service_item, title, form_data, priority, request.user, project_id)
            else:
                ticket = self._submit_lightweight(service_item, title, form_data, priority, request.user, project_id)
            return DetailResponse(data={
                'ticket_id': ticket.id,
                'sn': ticket.sn,
            }, msg="服务申请已提交")
        except Exception as e:
            logger.exception(f"ServiceItem submit failed: service_item={service_item.id}")
            return ErrorResponse(msg=f"提交失败: {str(e)}")

    def _submit_flow(self, service_item, title, form_data, priority, user, project_id=None):
        """流程驱动模式 — 创建 WorkflowVersion + Ticket + 启动 Pipeline"""
        logger.info(f'[_submit_flow] START service_item={service_item.id} title={title!r} project_id={project_id}')

        workflow = service_item.workflow
        if not workflow:
            raise ValueError("流程驱动模式未绑定 Workflow")

        # 创建部署快照
        version = workflow.create_version(operator=user.id)
        logger.info(f'[_submit_flow] Version created: {version.id}')

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

        # 创建工单 — project 使用请求上下文的 project_id
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=int(project_id))
            except (Project.DoesNotExist, ValueError, TypeError):
                pass
        if not project:
            project = service_item.category.project if service_item.category else None

        ticket = Ticket.objects.create(
            workflow_version=version,
            project=project,
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
        logger.info(f'[_submit_flow] Ticket #{ticket.id} created, sn={ticket.sn}, do_after_create done')

        # 找到第一个 NORMAL 节点的 state_id 和 state_key
        first_normal_state_id = None
        first_normal_state_key = None
        states = version.states or {}
        for key, state_data in states.items():
            if state_data.get('type') == 'NORMAL':
                first_normal_state_id = state_data.get('id')
                first_normal_state_key = key
                break

        # 同步自动完成第一个填单节点
        if form_data and first_normal_state_id:
            logger.info(f'[_submit_flow] Auto-completing state_id={first_normal_state_id} with {len(form_data)} fields')
            ticket.do_in_state(first_normal_state_id, form_data, 'system')
            logger.info(f'[_submit_flow] Auto-complete done for state_id={first_normal_state_id}')
        else:
            logger.info(f'[_submit_flow] No form_data, skipping auto-complete')

        # 启动 Pipeline
        logger.info(f'[_submit_flow] Starting pipeline... ticket_id={ticket.id} version_id={version.id}')
        pipeline_id, tree = ITSMEngine(ticket).run(version)
        ticket.pipeline_id = pipeline_id
        ticket.current_status = 'running'
        ticket.save(update_fields=['pipeline_id', 'current_status'])
        logger.info(f'[_submit_flow] Pipeline {pipeline_id} started')

        # 触发 pipeline callback 推进流程（避免 Celery CALLBACK schedule 永久等待）
        if form_data and first_normal_state_id:
            from pipeline.eri.models import Process as BambooProcess, Schedule as BambooSchedule
            from itsm.services.itsm_engine import ITSMEngine as Engine
            import time as _time

            # Resolve ITSM state_key → bamboo-engine activity_id
            # node_id_map = {state_key: element_id, ...} e.g. {"node_2": "node_2_613f56"}
            node_id_map = (ticket.meta or {}).get('_pipeline_id_map', {})
            activity_id = node_id_map.get(str(first_normal_state_key)) if isinstance(node_id_map, dict) else None

            if activity_id:
                # Wait for Celery to create the Schedule (up to 5s)
                for attempt in range(25):
                    proc = BambooProcess.objects.filter(root_pipeline_id=pipeline_id).first()
                    sched = None
                    if proc:
                        sched = BambooSchedule.objects.filter(process_id=proc.id, finished=False).first()
                    if sched:
                        logger.info(f'[_submit_flow] Schedule found after {attempt * 0.2:.1f}s, triggering callback activity_id={activity_id}')
                        try:
                            Engine.activity_callback(activity_id, {
                                'ticket_id': ticket.id,
                                'state_id': first_normal_state_id,
                                'fields': form_data,
                                'operator': 'system',
                            })
                            logger.info(f'[_submit_flow] Callback triggered successfully')
                        except Exception as e:
                            logger.warning(f'[_submit_flow] Callback failed: {e}')
                        break
                    _time.sleep(0.2)
                else:
                    logger.warning(f'[_submit_flow] Schedule not found after 5s, callback skipped')
            else:
                logger.warning(f'[_submit_flow] No activity_id found for state_id={first_normal_state_id}')

        return ticket

    def _submit_lightweight(self, service_item, title, form_data, priority, user, project_id=None):
        """快捷服务模式 — 创建轻量 Ticket 并分派"""
        project = None
        if project_id:
            try:
                project = Project.objects.get(id=int(project_id))
            except (Project.DoesNotExist, ValueError, TypeError):
                pass
        if not project:
            project = service_item.category.project if service_item.category else None

        ticket = Ticket.objects.create(
            project=project,
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
