# -*- coding: utf-8 -*-
"""ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成"""

from rest_framework.decorators import action
from rest_framework.views import APIView

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from itsm.models import Workflow, WorkflowVersion, State, Transition, Field
from itsm.serializers import (
    WorkflowSerializer, WorkflowCreateSerializer,
    WorkflowVersionSerializer,
    StateSerializer, TransitionSerializer, FieldSerializer,
)
from itsm.services.ai_generator import AIGenerator


class WorkflowViewSet(CustomModelViewSet):
    """流程模板管理"""
    model = Workflow
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    create_serializer_class = WorkflowCreateSerializer
    update_serializer_class = WorkflowCreateSerializer
    filter_fields = ['itsm_type', 'is_enabled', 'is_draft']
    search_fields = ['name', 'description']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def deploy(self, request, pk=None):
        """部署 — 创建 WorkflowVersion"""
        instance = self.get_object()
        message = request.data.get('message', '')
        try:
            version = instance.create_version(
                operator=request.user.username,
                message=message,
            )
            instance.is_draft = False
            instance.is_enabled = True
            instance.save(update_fields=['is_draft', 'is_enabled'])
            return DetailResponse(data=WorkflowVersionSerializer(version).data,
                                  msg='部署成功')
        except Exception as e:
            return ErrorResponse(msg=f'部署失败: {str(e)}')


class WorkflowVersionViewSet(CustomModelViewSet):
    """流程版本管理"""
    model = WorkflowVersion
    queryset = WorkflowVersion.objects.all()
    serializer_class = WorkflowVersionSerializer
    filter_fields = ['workflow']
    ordering = ['-create_datetime']


class StateViewSet(CustomModelViewSet):
    """节点管理"""
    model = State
    queryset = State.objects.all()
    serializer_class = StateSerializer
    filter_fields = ['workflow', 'type']
    ordering = ['id']

    def get_queryset(self):
        qs = super().get_queryset()
        workflow_pk = self.request.query_params.get('workflow') or \
                      self.kwargs.get('workflow_pk')
        if workflow_pk:
            qs = qs.filter(workflow_id=workflow_pk)
        return qs


class TransitionViewSet(CustomModelViewSet):
    """连线管理"""
    model = Transition
    queryset = Transition.objects.all()
    serializer_class = TransitionSerializer
    filter_fields = ['workflow', 'from_state', 'to_state']

    def get_queryset(self):
        qs = super().get_queryset()
        workflow_pk = self.request.query_params.get('workflow') or \
                      self.kwargs.get('workflow_pk')
        if workflow_pk:
            qs = qs.filter(workflow_id=workflow_pk)
        return qs

    @action(methods=['POST'], detail=False)
    def batch_update(self, request):
        """批量更新连线"""
        workflow_id = request.data.get('workflow_id')
        transitions = request.data.get('transitions', [])
        if not workflow_id:
            return ErrorResponse(msg='workflow_id required')
        for t in transitions:
            Transition.objects.filter(id=t.get('id')).update(**t)
        return DetailResponse(msg='批量更新成功')


class FieldViewSet(CustomModelViewSet):
    """字段管理"""
    model = Field
    queryset = Field.objects.all()
    serializer_class = FieldSerializer
    filter_fields = ['state', 'type']

    def get_queryset(self):
        qs = super().get_queryset()
        state_pk = self.kwargs.get('state_pk')
        if state_pk:
            qs = qs.filter(state_id=state_pk)
        return qs


class AIGenerateView(APIView):
    """AI 生成工作流 (APIView)"""

    def post(self, request):
        description = request.data.get('description', '')
        itsm_type = request.data.get('itsm_type', 'change')

        if not description:
            return ErrorResponse(msg='请输入审批流程描述')

        # Determine action from URL path
        is_fields = 'generate-fields' in request.path

        try:
            generator = AIGenerator()
            if is_fields:
                fields = generator.generate_fields(description)
                return DetailResponse(data=fields, msg='生成成功')
            else:
                result = generator.generate_workflow(description, itsm_type)
                return DetailResponse(data=result, msg='生成成功')
        except Exception as e:
            return ErrorResponse(msg=f'生成失败: {str(e)}')
