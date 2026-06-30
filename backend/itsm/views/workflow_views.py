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


def _filter_model_fields(model, data: dict) -> dict:
    """只保留 model 字段名，过滤前端额外数据"""
    field_names = {f.name for f in model._meta.get_fields()}
    fk_names = {'workflow', 'from_state', 'to_state', 'state'}
    result = {}
    for k, v in data.items():
        if k.endswith('_id'):
            base = k[:-3]
            if base in fk_names and base in field_names:
                result[k] = v
        elif k in field_names and k not in fk_names:
            result[k] = v
    return result


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
                operator=request.user,
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

    @action(methods=['POST'], detail=True)
    def rollback(self, request, pk=None):
        old_version = self.get_object()
        workflow = old_version.workflow
        message = request.data.get('message', 'Rollback to v' + old_version.version)
        workflow.states.all().delete()
        workflow.transitions.all().delete()
        Field.objects.filter(state__workflow=workflow).delete()
        state_id_map = {}
        for sid, sdata in old_version.states.items():
            ns = State.objects.create(
                workflow=workflow, name=sdata.get('name', ''),
                type=sdata.get('type', 'NORMAL'),
                processors_type=sdata.get('processors_type', 'PERSON'),
                processors=sdata.get('processors', ''),
                is_multi=sdata.get('is_multi', False),
                is_sequential=sdata.get('is_sequential', False),
                finish_condition=sdata.get('finish_condition', {}),
                is_allow_skip=sdata.get('is_allow_skip', False),
                fields=sdata.get('fields', []), extras=sdata.get('extras', {}),
                is_builtin=sdata.get('is_builtin', False),
            )
            state_id_map[int(sid)] = ns.id
        for tid, tdata in old_version.transitions.items():
            Transition.objects.create(
                workflow=workflow, name=tdata.get('name', ''),
                from_state_id=state_id_map.get(tdata.get('from_state_id')),
                to_state_id=state_id_map.get(tdata.get('to_state_id')),
                condition=tdata.get('condition', ''),
                direction=tdata.get('direction', 'forward'),
            )
        for fid, fdata in old_version.fields.items():
            sid = state_id_map.get(fdata.get('state_id'))
            if sid:
                Field.objects.create(
                    state_id=sid, key=fdata.get('key', ''),
                    name=fdata.get('name', ''), type=fdata.get('type', 'STRING'),
                    required=fdata.get('required', False),
                    layout=fdata.get('layout', 'COL_12'),
                    choice=fdata.get('choice', []), default=fdata.get('default', []),
                )
        new_version = workflow.create_version(operator=request.user, message=message)
        return DetailResponse(data=WorkflowVersionSerializer(new_version).data, msg='Rolled back v'+old_version.version+', created v'+new_version.version)

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

    @action(methods=['POST'], detail=False)
    def sync(self, request):
        """全量同步节点（自动保存用）— 差异删除+创建+更新"""
        workflow_id = request.data.get('workflow_id')
        states = request.data.get('states', [])
        if not workflow_id:
            return ErrorResponse(msg='workflow_id required')
        existing_ids = set(State.objects.filter(workflow_id=workflow_id).values_list('id', flat=True))
        incoming_ids = set()
        for s in states:
            sid = s.get('id')
            clean = _filter_model_fields(State, s)
            clean.pop('id', None)
            if sid and State.objects.filter(id=sid, workflow_id=workflow_id).exists():
                State.objects.filter(id=sid).update(**clean)
                incoming_ids.add(sid)
            else:
                clean['workflow_id'] = workflow_id
                new_state = State.objects.create(**clean)
                incoming_ids.add(new_state.id)
        to_delete = existing_ids - incoming_ids
        State.objects.filter(id__in=to_delete).delete()
        return DetailResponse(msg='节点全量同步成功')


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
    def sync(self, request):
        """全量同步连线（自动保存用）"""
        workflow_id = request.data.get('workflow_id')
        transitions = request.data.get('transitions', [])
        if not workflow_id:
            return ErrorResponse(msg='workflow_id required')
        existing_ids = set(Transition.objects.filter(workflow_id=workflow_id).values_list('id', flat=True))
        incoming_ids = set()
        for t in transitions:
            tid = t.get('id')
            clean = _filter_model_fields(Transition, t)
            clean.pop('id', None)
            if tid and Transition.objects.filter(id=tid, workflow_id=workflow_id).exists():
                Transition.objects.filter(id=tid).update(**clean)
                incoming_ids.add(tid)
            else:
                clean['workflow_id'] = workflow_id
                new_t = Transition.objects.create(**clean)
                incoming_ids.add(new_t.id)
        to_delete = existing_ids - incoming_ids
        Transition.objects.filter(id__in=to_delete).delete()
        return DetailResponse(msg='连线全量同步成功')


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

    @action(methods=['POST'], detail=False)
    def batch_update(self, request):
        """批量更新字段（自动保存用）"""
        state_id = request.data.get('state_id')
        fields = request.data.get('fields', [])
        if not state_id:
            return ErrorResponse(msg='state_id required')
        for f in fields:
            fid = f.get('id')
            clean = _filter_model_fields(Field, f)
            clean.pop('id', None)
            if fid and Field.objects.filter(id=fid, state_id=state_id).exists():
                Field.objects.filter(id=fid).update(**clean)
            else:
                clean['state_id'] = state_id
                Field.objects.create(**clean)
        return DetailResponse(msg='字段批量更新成功')


class AIGenerateView(APIView):
    """AI 生成工作流 (APIView)"""

    def post(self, request):
        description = request.data.get('description', '')
        itsm_type = request.data.get('itsm_type', 'change')

        if not description:
            return ErrorResponse(msg='请输入审批流程描述')

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
