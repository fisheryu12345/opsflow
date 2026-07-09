# -*- coding: utf-8 -*-
"""ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传"""

import time

from django.db import models

from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse

from opsflow.views.base import ProjectFilteredViewSet
from iam.permissions import TenantPermission, EnvironmentGatePermission

from itsm.models import Ticket, TicketStatus, SignTask, WorkflowVersion, SlaTask
from itsm.serializers import (
    TicketSerializer, TicketCreateSerializer,
    TicketStatusSerializer, SignTaskSerializer,
)
from itsm.services.itsm_engine import ITSMEngine
from itsm.services.opsflow_trigger import OpsflowTriggerService
from itsm.views.workflow_views import ItsmProjectViewSet


class TicketViewSet(ItsmProjectViewSet):
    """工单管理 — project-scoped with environment gate"""
    model = Ticket
    queryset = Ticket.objects.prefetch_related(
        models.Prefetch('sla_tasks', queryset=SlaTask.objects.select_related('sla_policy'))
    )
    serializer_class = TicketSerializer
    filter_fields = ['itsm_type', 'current_status', 'priority', 'creator']
    search_fields = ['sn', 'title']
    ordering = ['-create_datetime']
    permission_classes = [IsAuthenticated, TenantPermission, EnvironmentGatePermission]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return TicketCreateSerializer
        return TicketSerializer

    def _resolve_workflow_version(self, itsm_type, project_id=None):
        """根据工单类型自动匹配最新已部署的流程版本"""
        return WorkflowVersion.objects.filter(
            workflow__itsm_type=itsm_type,
            workflow__is_draft=False,
            workflow__is_enabled=True,
            workflow__project_id=project_id,
        ).order_by('-create_datetime').first()

    def perform_create(self, serializer):
        if not serializer.validated_data.get('workflow_version'):
            itsm_type = serializer.validated_data.get('itsm_type', 'change')
            project_id = serializer.validated_data.get('project_id')
            version = self._resolve_workflow_version(itsm_type, project_id)
            if not version:
                raise ValidationError(
                    f'工单类型 "{dict(Ticket.ITSM_TYPE_CHOICES).get(itsm_type, itsm_type)}" '
                    f'没有已部署的流程模板，请先联系管理员配置'
                )
            serializer.validated_data['workflow_version'] = version
        # Resolve project assignment (inherited from ProjectFilteredViewSet)
        kwargs = self.resolve_project_kwargs(self.request)
        if 'project_id' in kwargs:
            user_project_ids = self.get_user_project_ids()
            if kwargs['project_id'] not in user_project_ids:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('无权限在此项目中创建资源')
        kwargs['creator'] = self.request.user.id
        instance = serializer.save(**kwargs)
        # Auto-fill business from project's business
        if instance.project and instance.project.business_id:
            instance.business = instance.project.business
            instance.save(update_fields=['business'])
        instance.do_after_create()
        return instance

    @action(methods=['POST'], detail=True)
    def submit(self, request, pk=None):
        """提交工单 — 启动 pipeline + 自动分派"""
        instance = self.get_object()
        if instance.current_status != 'draft':
            return ErrorResponse(msg='工单已提交，不能重复提交')
        if not instance.workflow_version:
            return ErrorResponse(msg='工单未绑定流程版本，无法提交')
        try:
            logger = __import__('logging').getLogger(__name__)
            logger.info(f'[SubmitTicket] ticket={instance.id} current meta keys={list((instance.meta or {}).keys())[:5]}')
            # Sync auto-complete first NORMAL node from form_data (same as _submit_flow)
            form_data = (instance.meta or {}).get('form_data', {})
            states = (instance.workflow_version and instance.workflow_version.states) or {}
            first_normal_id = None
            first_normal_key = None
            for key, s in states.items():
                if s.get('type') == 'NORMAL':
                    first_normal_id = s.get('id')
                    first_normal_key = key
                    break
            if form_data and first_normal_id:
                instance.do_in_state(first_normal_id, form_data, 'system')
                # Clear form_data to prevent auto-completion of subsequent NORMAL nodes
                meta = dict(instance.meta or {})
                meta.pop('form_data', None)
                instance.meta = meta
                instance.save(update_fields=['meta'])

            pipeline_id, tree = ITSMEngine(instance).run(instance.workflow_version)
            instance.pipeline_id = pipeline_id
            instance.current_status = 'running'
            instance.save(update_fields=['pipeline_id', 'current_status'])

            # Trigger callback to advance pipeline past first NORMAL (same as _submit_flow)
            if form_data and first_normal_key:
                from pipeline.eri.models import Process as BambooProcess, Schedule as BambooSchedule
                from itsm.services.bamboo_engine import activity_callback as bamboo_cb
                node_id_map = (instance.meta or {}).get('_pipeline_id_map', {})
                activity_id = node_id_map.get(str(first_normal_key))
                if activity_id:
                    ok = False
                    for attempt in range(25):
                        proc = BambooProcess.objects.filter(root_pipeline_id=pipeline_id).first()
                        if proc and BambooSchedule.objects.filter(process_id=proc.id, finished=False).exists():
                            bamboo_cb(activity_id, {'ticket_id': instance.id, 'state_id': first_normal_id, 'fields': form_data, 'operator': 'system'})
                            ok = True
                            break
                        time.sleep(0.2)
                    if not ok:
                        logger = __import__('logging').getLogger(__name__)
                        logger.error(f'[SubmitTicket] Callback polling timed out after 5s for ticket={instance.id}, pipeline may be stuck')

            return DetailResponse(data={
                'pipeline_id': pipeline_id,
                'ticket_id': instance.id,
                'sn': instance.sn,
            }, msg='工单提交成功，pipeline 已启动')
        except Exception as e:
            return ErrorResponse(msg=f'提交失败: {str(e)}')

    @action(methods=['POST'], detail=True)
    def node_submit(self, request, pk=None):
        """提交节点表单（填单节点回调）"""
        instance = self.get_object()
        state_id = request.data.get('state_id')
        fields = request.data.get('fields', {})
        if not state_id:
            return ErrorResponse(msg='state_id required')
        try:
            ITSMEngine.activity_callback(
                activity_id=self._get_activity_id(instance, state_id),
                callback_data={
                    'ticket_id': instance.id,
                    'state_id': state_id,
                    'fields': fields,
                    'operator': request.user.username,
                }
            )
            return DetailResponse(msg='节点提交成功')
        except Exception as e:
            return ErrorResponse(msg=f'节点提交失败: {str(e)}')

    @action(methods=['POST'], detail=True, parser_classes=[])  # DRF auto-detects MultiPartParser
    def upload_file(self, request, pk=None):
        """上传工单附件（FILE 类型字段使用）"""
        instance = self.get_object()
        file = request.FILES.get('file')
        field_key = request.data.get('field_key', '')
        if not file:
            return ErrorResponse(msg='请选择文件')
        try:
            from django.core.files.storage import default_storage
            import os
            path = f'itsm/{instance.id}/{field_key}/{file.name}'
            saved_path = default_storage.save(path, file)
            url = default_storage.url(saved_path)
            meta = dict(instance.meta or {})
            uploads = meta.setdefault('_uploads', [])
            uploads.append({
                'field_key': field_key,
                'file_name': file.name,
                'file_size': file.size,
                'path': saved_path,
                'url': url,
            })
            instance.meta = meta
            instance.save(update_fields=['meta'])
            return DetailResponse(data={'url': url, 'name': file.name, 'size': file.size},
                                  msg='文件上传成功')
        except Exception as e:
            return ErrorResponse(msg=f'文件上传失败: {str(e)}')

    @action(methods=['POST'], detail=True)
    def approve(self, request, pk=None):
        """审批通过"""
        instance = self.get_object()
        state_id = request.data.get('state_id')
        comment = request.data.get('comment', '')
        return self._do_approve(instance, state_id, 'true', comment, request)

    @action(methods=['POST'], detail=True)
    def reject(self, request, pk=None):
        """审批拒绝"""
        instance = self.get_object()
        state_id = request.data.get('state_id')
        comment = request.data.get('comment', '')
        return self._do_approve(instance, state_id, 'false', comment, request)

    @action(methods=['POST'], detail=True)
    def suspend(self, request, pk=None):
        """挂起工单（统一暂停 pipeline + SLA + 升级检测）"""
        instance = self.get_object()
        ITSMEngine(instance).pause()
        return DetailResponse(msg='工单已挂起')

    @action(methods=['POST'], detail=True)
    def resume(self, request, pk=None):
        """恢复工单（统一恢复 pipeline + SLA）"""
        instance = self.get_object()
        ITSMEngine(instance).resume()
        return DetailResponse(msg='工单已恢复')

    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        """关闭工单（撤销 pipeline + 停止 SLA）"""
        instance = self.get_object()
        ITSMEngine(instance).revoke()
        return DetailResponse(msg='工单已关闭')

    @action(methods=['POST'], detail=True)
    def assign(self, request, pk=None):
        """分派工单 — 手动分派/转派给指定用户"""
        instance = self.get_object()
        user_id_raw = request.data.get('user_id')
        reason = request.data.get('reason', '')
        if not user_id_raw:
            return ErrorResponse(msg='user_id required')
        try:
            user_id = int(user_id_raw)
        except (ValueError, TypeError):
            return ErrorResponse(msg='user_id must be a valid integer')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
            meta = dict(instance.meta or {})
            meta['assignee'] = {
                'id': user.id,
                'username': user.username,
                'name': user.name,
            }
            instance.meta = meta
            instance.current_status = 'assigned'
            instance.save(update_fields=['meta', 'current_status'])
            return DetailResponse(msg='工单已分派')
        except User.DoesNotExist:
            return ErrorResponse(msg='用户不存在')
        except Exception as e:
            return ErrorResponse(msg=f'分派失败: {str(e)}')

    @action(methods=['GET'], detail=True)
    def status(self, request, pk=None):
        """获取工单状态详情"""
        instance = self.get_object()
        status_records = TicketStatus.objects.filter(ticket=instance)
        return DetailResponse(data={
            'ticket': TicketSerializer(instance).data,
            'node_status': TicketStatusSerializer(status_records, many=True).data,
            'sign_tasks': SignTaskSerializer(
                instance.sign_tasks.all(), many=True
            ).data,
        })

    def _do_approve(self, instance, state_id, result, comment, request):
        """执行审批操作"""
        if not state_id:
            return ErrorResponse(msg='state_id required')
        try:
            fields = request.data.get('fields', {}) or {}
            activity_id = self._get_activity_id(instance, state_id)
            if not activity_id:
                return ErrorResponse(msg='未找到审批节点，pipeline 可能尚未就绪，请稍后重试')
            # Retry up to 3 times with 1s delay for Celery schedule creation
            ok = False
            import logging
            log = logging.getLogger(__name__)
            for attempt in range(3):
                log.info(f'[_do_approve] attempt {attempt+1}/3: activity_id={activity_id} ticket={instance.id} state={state_id}')
                ok = ITSMEngine.activity_callback(
                    activity_id=activity_id,
                    callback_data={
                        'ticket_id': instance.id,
                        'state_id': state_id,
                        'approve_result': result,
                        'comment': comment,
                        'fields': fields,
                        'operator': request.user.username,
                    }
                )
                if ok:
                    break
                time.sleep(1)
            if not ok:
                return ErrorResponse(msg='审批回调失败，pipeline 可能尚未就绪，请稍后重试')

            action_name = '通过' if result == 'true' else '拒绝'

            if result == 'true':
                trigger_result = OpsflowTriggerService.on_ticket_approved(instance)
                if trigger_result.get('triggered'):
                    logger = __import__('logging').getLogger(__name__)
                    logger.info(
                        'Ticket %s approved, triggered OpsFlow execution: %s',
                        instance.sn, trigger_result.get('execution_id'),
                    )

            return DetailResponse(msg=f'审批{action_name}成功')
        except Exception as e:
            return ErrorResponse(msg=f'审批失败: {str(e)}')

    @staticmethod
    def _get_activity_id(ticket, state_id):
        """获取 pipeline activity ID — 用 node_key + pipeline_id_map 匹配 bamboo element ID

        每个 pipeline 运行使用唯一 element ID (带 run_salt 后缀)，
        _pipeline_id_map 保存在 ticket.meta 中用于状态 key → element ID 的解析。
        """
        id_map = (ticket.meta or {}).get('_pipeline_id_map', {})
        key = str(state_id)
        # Fast path: direct lookup in pipeline id_map
        if key in id_map:
            return id_map[key]
        # Fallback: resolve from workflow_version states, then map through id_map
        states = (ticket.workflow_version and ticket.workflow_version.states) or {}
        if key in states:
            s = states[key]
            node_key = str(s.get('node_key') or key)
            return id_map.get(node_key, node_key)
        # Fallback: search by id field
        for s in states.values():
            if str(s.get('id')) == key:
                node_key = str(s.get('node_key') or key)
                return id_map.get(node_key, node_key)
        # Last resort
        return id_map.get(key, key)
