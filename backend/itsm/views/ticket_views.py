# -*- coding: utf-8 -*-
"""ITSM Ticket views — 工单管理、提交、审批、状态管理、文件上传"""

from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from itsm.models import Ticket, TicketStatus, SignTask, WorkflowVersion
from itsm.serializers import (
    TicketSerializer, TicketCreateSerializer,
    TicketStatusSerializer, SignTaskSerializer,
)
from itsm.services.pipeline_wrapper import PipelineWrapper
from itsm.services.opsflow_trigger import OpsflowTriggerService


class TicketViewSet(CustomModelViewSet):
    """工单管理"""
    model = Ticket
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    create_serializer_class = TicketCreateSerializer
    filter_fields = ['itsm_type', 'current_status', 'priority', 'creator']
    search_fields = ['sn', 'title']
    ordering = ['-create_datetime']

    def perform_create(self, serializer):
        instance = serializer.save(creator=self.request.user)
        instance.do_after_create()
        return instance

    @action(methods=['POST'], detail=True)
    def submit(self, request, pk=None):
        """提交工单 — 启动 pipeline + 自动分派"""
        instance = self.get_object()
        if instance.current_status != 'draft':
            return ErrorResponse(msg='工单已提交，不能重复提交')
        try:
            wrapper = PipelineWrapper(instance.workflow_version)
            pipeline_id, tree = wrapper.run_pipeline(instance.id)
            instance.pipeline_id = pipeline_id
            instance.current_status = 'running'
            instance.save(update_fields=['pipeline_id', 'current_status'])

            # 提交后尝试自动分派
            try:
                from itsm.services.assign_engine import AssignEngine
                engine = AssignEngine(instance)
                engine.auto_assign()
            except Exception as assign_err:
                import logging
                logging.getLogger(__name__).warning(
                    "Auto-assign failed for ticket %s: %s", instance.sn, assign_err
                )

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
            PipelineWrapper.activity_callback(
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
        """挂起工单"""
        instance = self.get_object()
        if instance.pipeline_id:
            PipelineWrapper.pause_pipeline(instance.pipeline_id)
        instance.set_status('suspended', request.user.username)
        return DetailResponse(msg='工单已挂起')

    @action(methods=['POST'], detail=True)
    def resume(self, request, pk=None):
        """恢复工单"""
        instance = self.get_object()
        if instance.pipeline_id:
            PipelineWrapper.resume_pipeline(instance.pipeline_id)
        instance.set_status('running', request.user.username)
        return DetailResponse(msg='工单已恢复')

    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        """关闭工单"""
        instance = self.get_object()
        if instance.pipeline_id:
            PipelineWrapper.revoke_pipeline(instance.pipeline_id)
        instance.set_status('terminated', request.user.username)
        return DetailResponse(msg='工单已关闭')

    @action(methods=['POST'], detail=True)
    def assign(self, request, pk=None):
        """分派工单 — 手动分派/转派给指定用户"""
        from itsm.services.assign_engine import AssignEngine

        instance = self.get_object()
        user_id = request.data.get('user_id')
        group_id = request.data.get('group_id')
        reason = request.data.get('reason', '')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        try:
            from dvadmin.system.models import Users
            user = Users.objects.get(id=user_id)
            group = None
            if group_id:
                from itsm.models.skill_group import SkillGroup
                try:
                    group = SkillGroup.objects.get(id=group_id)
                except SkillGroup.DoesNotExist:
                    pass
            AssignEngine.manual_assign(instance, user, group, reason)
            return DetailResponse(msg='工单已分派')
        except Users.DoesNotExist:
            return ErrorResponse(msg='用户不存在')
        except Exception as e:
            return ErrorResponse(msg=f'分派失败: {str(e)}')

    @action(methods=['POST'], detail=True)
    def auto_assign(self, request, pk=None):
        """触发自动分派，由 AssignEngine 按规则决定"""
        from itsm.services.assign_engine import AssignEngine

        instance = self.get_object()
        engine = AssignEngine(instance)
        result = engine.auto_assign()
        if result:
            return DetailResponse(data=result, msg='自动分派完成')
        return ErrorResponse(msg='无匹配规则，未分派')

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
            PipelineWrapper.activity_callback(
                activity_id=self._get_activity_id(instance, state_id),
                callback_data={
                    'ticket_id': instance.id,
                    'state_id': state_id,
                    'approve_result': result,
                    'comment': comment,
                    'operator': request.user.username,
                }
            )
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
        """获取 pipeline activity ID（目前直接使用 state_id）"""
        return str(state_id)
