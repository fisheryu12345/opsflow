# -*- coding: utf-8 -*-
"""ITSM Workflow views — 流程模板管理、节点、连线、字段、AI 生成"""

import logging
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse

from itsm.views.base import ProjectFilteredViewSet
from iam.permissions import TenantPermission

from itsm.models import Workflow, WorkflowVersion, State, Transition, Field
from itsm.services.workflow_validator import validate_workflow
from itsm.serializers import (
    WorkflowSerializer, WorkflowCreateSerializer,
    WorkflowVersionSerializer,
    StateSerializer, TransitionSerializer, FieldSerializer,
)
from itsm.services.ai_generator import AIGenerator
from common.utils.language import get_request_lang


def _build_validation_data(workflow) -> tuple:
    """Build states/transitions dicts from a Workflow instance for validation.

    State keys use node_key (preferred) or id as fallback.
    Transitions include from_state_id/to_state_id as fallback for old data
    where from_node_key/to_node_key may be empty.
    """
    states_data = {}
    for s in workflow.states.all():
        key = s.node_key or str(s.id)
        states_data[key] = {
            'id': s.id, 'node_key': s.node_key or '', 'name': s.name, 'type': s.type,
            'processors': (s.processors or ''),
            'processors_type': (s.processors_type or ''),
        }
    transitions_data = {}
    for t in workflow.transitions.all():
        transitions_data[t.id] = {
            'id': t.id, 'name': t.name,
            'from_node_key': t.from_node_key or '',
            'to_node_key': t.to_node_key or '',
            'from_state_id': str(t.from_state_id) if t.from_state_id else '',
            'to_state_id': str(t.to_state_id) if t.to_state_id else '',
            'condition': t.condition,
            'condition_type': t.condition_type,
        }
    return states_data, transitions_data


class ItsmProjectViewSet(ProjectFilteredViewSet):
    """ITSM project-scoped ViewSet — 整合 IAM ProjectFilteredViewSet + dvadmin 响应格式"""
    permission_classes = [IsAuthenticated, TenantPermission]
    project_field = 'project'

    def get_queryset(self):
        """Override to include records with project_id=NULL (backward compat during migration)."""
        from django.db.models import Q
        qs = super().get_queryset()
        project_field_id = self.project_field + '_id'
        null_qs = self.model.objects.filter(**{project_field_id + '__isnull': True})
        return (qs | null_qs).distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return SuccessResponse(data=serializer.data, msg="获取成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data, msg="获取成功")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg="新增成功")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return DetailResponse(data=serializer.data, msg="更新成功")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return DetailResponse(data=[], msg="删除成功")


def _filter_model_fields(model, data: dict) -> dict:
    """只保留 model 字段名，过滤前端额外数据"""
    field_names = {f.name for f in model._meta.get_fields()}
    fk_names = {'workflow', 'from_state', 'to_state', 'state', 'preset'}
    result = {}
    for k, v in data.items():
        if k.endswith('_id'):
            base = k[:-3]
            if base in fk_names and base in field_names:
                result[k] = v
        elif k in field_names and k not in fk_names:
            result[k] = v
    return result


# ITSM node type → opsflow layout NodeType mapping
ITSM_NODE_TYPE_MAP = {
    'START': 'start_event',
    'END': 'end_event',
    'EXCLUSIVE': 'exclusive_gateway',
    'CONDITIONAL_PARALLEL': 'conditional_parallel_gateway',
    'PARALLEL': 'parallel_gateway',
    'COVERAGE': 'converge_gateway',
}


class WorkflowViewSet(ItsmProjectViewSet):
    """流程模板管理 — project-scoped with multi-tenant isolation"""
    model = Workflow
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    filter_fields = ['itsm_type', 'is_enabled', 'is_draft']
    search_fields = ['name', 'description']
    ordering = ['-create_datetime']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return WorkflowCreateSerializer
        return WorkflowSerializer

    @action(methods=['POST'], detail=True)
    def layout(self, request, pk=None):
        """计算流程布局 — 使用 Sugiyama 布局引擎"""
        from common.utils.layout import compute_layout

        instance = self.get_object()
        nodes_data = request.data.get('nodes', [])
        edges_data = request.data.get('edges', [])

        if not nodes_data:
            return ErrorResponse(msg='nodes required')

        # Map ITSM node types → opsflow node_type
        layout_nodes = []
        for n in nodes_data:
            itsm_type = n.get('type', '')
            node_type = ITSM_NODE_TYPE_MAP.get(itsm_type, '')  # default = ServiceActivity
            layout_nodes.append({
                'id': str(n.get('id', '')),
                'node_type': node_type,
                'name': n.get('name', ''),
            })

        layout_edges = []
        for e in edges_data:
            layout_edges.append({
                'id': str(e.get('id', '')),
                'source': str(e.get('from_state') or e.get('from', '')),
                'target': str(e.get('to_state') or e.get('to', '')),
            })

        try:
            positions = compute_layout(
                layout_nodes, layout_edges,
                activity_size=(280, 56),   # ITSM node card size (must match frontend CARD_HEIGHT)
                event_size=(56, 56),
                gateway_size=(70, 70),
                start=(80, 80),
                canvas_width=2800,
            )
        except Exception as e:
            return ErrorResponse(msg=f'Layout computation failed: {str(e)}')

        return DetailResponse(data={'positions': positions}, msg='Layout computed')

    @action(methods=['POST'], detail=True, url_path='validate')
    def validate_structure(self, request, pk=None):
        """校验流程结构，返回逐项检测结果"""
        instance = self.get_object()
        states_data, transitions_data = _build_validation_data(instance)
        lang = get_request_lang(request)
        result = validate_workflow(states_data, transitions_data, lang=lang)
        return DetailResponse(data=result)

    @action(methods=['POST'], detail=True)
    def deploy(self, request, pk=None):
        """部署 — 创建 WorkflowVersion（含流程校验）"""
        instance = self.get_object()

        states_data, transitions_data = _build_validation_data(instance)
        lang = get_request_lang(request)
        result = validate_workflow(states_data, transitions_data, lang=lang)
        if not result['valid']:
            return ErrorResponse(msg='流程校验未通过，请修正后再部署', data=result, code=4000, status=400)

        message = request.data.get('message', '')
        try:
            version = instance.create_version(
                operator=request.user.id,
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
        # Clean up legacy Field ORM records (deprecated — fields now live in State.fields JSONField)
        Field.objects.filter(state__workflow=workflow).delete()
        state_id_map = {}
        for sid, sdata in old_version.states.items():
            ns = State.objects.create(
                workflow=workflow, name=sdata.get('name', ''),
                type=sdata.get('type', 'NORMAL'),
                node_key=sdata.get('node_key') or '',
                processors_type=sdata.get('processors_type', 'PERSON'),
                processors=sdata.get('processors', ''),
                is_multi=sdata.get('is_multi', False),
                is_sequential=sdata.get('is_sequential', False),
                finish_condition=sdata.get('finish_condition', {}),
                is_allow_skip=sdata.get('is_allow_skip', False),
                fields=sdata.get('fields', []), extras=sdata.get('extras', {}),
                is_builtin=sdata.get('is_builtin', False),
                distribute_type=sdata.get('distribute_type', 'PROCESS'),
                api_instance_id=sdata.get('api_instance_id', 0),
            )
            # Map both node_key (str) and original id (int) for transition lookup
            state_id_map[str(sid)] = ns.id
            db_id = sdata.get('id')
            if db_id is not None:
                state_id_map[str(db_id)] = ns.id
        for tid, tdata in old_version.transitions.items():
            Transition.objects.create(
                workflow=workflow, name=tdata.get('name', ''),
                from_state_id=state_id_map.get(str(tdata.get('from_state_id', ''))),
                to_state_id=state_id_map.get(str(tdata.get('to_state_id', ''))),
                from_node_key=tdata.get('from_node_key') or '',
                to_node_key=tdata.get('to_node_key') or '',
                condition=tdata.get('condition', {}),
                condition_type=tdata.get('condition_type', 'default'),
                direction=tdata.get('direction', 'forward'),
            )
        # Fields are already restored inline in State.fields JSONField (see State.objects.create above).
        # No separate Field ORM recreation needed.
        new_version = workflow.create_version(operator=request.user.id, message=message)
        return DetailResponse(data=WorkflowVersionSerializer(new_version).data, msg='Rolled back v'+old_version.version+', created v'+new_version.version)

class StateViewSet(CustomModelViewSet):
    """节点管理"""
    model = State
    queryset = State.objects.all()
    serializer_class = StateSerializer
    filter_fields = ['workflow', 'type']
    ordering = ['id']
    pagination_class = None  # disable pagination — all states for a workflow must load

    def get_queryset(self):
        qs = super().get_queryset()
        workflow_pk = self.request.query_params.get('workflow') or \
                      self.kwargs.get('workflow_pk')
        if workflow_pk:
            qs = qs.filter(workflow_id=workflow_pk)
        return qs

    @action(methods=['POST'], detail=False)
    def sync(self, request):
        """Full sync of states (auto-save) — upsert by node_key, delete orphans"""
        workflow_id = request.data.get('workflow_id')
        states = request.data.get('states', [])
        if not workflow_id:
            return ErrorResponse(msg='workflow_id required')
        # Resolve preset processors before sync
        states = self._expand_preset_processors(states, workflow_id)
        # Use node_key as stable identifier; fall back to id for backward compat
        existing = {s.node_key: s for s in State.objects.filter(workflow_id=workflow_id) if s.node_key}
        incoming_keys = set()
        for s in states:
            nk = s.get('node_key')
            stype = s.get('type', '?')
            clean = _filter_model_fields(State, s)
            clean.pop('id', None)
            if nk and nk in existing:
                State.objects.filter(id=existing[nk].id).update(**clean)
                incoming_keys.add(nk)
            else:
                clean['workflow_id'] = workflow_id
                if nk:
                    clean['node_key'] = nk
                new_state = State.objects.create(**clean)
                    # Track by node_key if set, otherwise by DB id to prevent purge
                if nk:
                    incoming_keys.add(nk)
                incoming_keys.add(f'__dbid_{new_state.id}')
        # Delete states that no longer exist on canvas + old states without node_key
        to_delete = set(existing.keys()) - incoming_keys
        State.objects.filter(workflow_id=workflow_id, node_key__in=to_delete).delete()
        # Also purge legacy states without node_key (already replaced by node_key versions)
        return DetailResponse(msg='节点全量同步成功')

    @staticmethod
    def _expand_preset_processors(states, workflow_id=None):
        """Expand preset_id → processors text for each state in the sync payload"""
        from itsm.models.preset import Preset
        from itsm.serializers.preset import PresetSerializer

        raw_ids = {s.get('preset_id') for s in states if s.get('preset_id')}
        # Also collect preset_ids from embedded fields
        for s in states:
            for f in (s.get('fields') or []):
                if f.get('preset_id'):
                    raw_ids.add(f['preset_id'])
        if not raw_ids:
            return states
        # Coerce to int — preset_id may arrive as string from JSON; skip invalid values
        preset_ids = set()
        for pid in raw_ids:
            try:
                preset_ids.add(int(pid))
            except (ValueError, TypeError):
                pass
        if not preset_ids:
            return states
        qs = Preset.objects.filter(id__in=preset_ids)
        # Scope to workflow's project to prevent cross-project preset reference
        if workflow_id:
            from itsm.models import Workflow
            try:
                workflow = Workflow.objects.only('project_id').get(id=workflow_id)
                if workflow.project_id:
                    qs = qs.filter(project_id=workflow.project_id)
            except Workflow.DoesNotExist:
                logging.getLogger(__name__).warning(
                    'sync preset expansion: workflow %s not found, skipping project scope', workflow_id
                )
        presets = {p.id: p for p in qs}
        for s in states:
            pid = s.get('preset_id')
            if pid:
                try:
                    int_pid = int(pid)
                except (ValueError, TypeError):
                    continue
                if int_pid in presets:
                    preset = presets[int_pid]
                    # Only expand non-options presets as processors (user_list/role_list/dept_list/text)
                    if preset.preset_type != 'options':
                        s['processors'] = PresetSerializer._expand_value(preset)
            # Expand preset_id → choice for embedded fields in State.fields JSON
            for f in (s.get('fields') or []):
                fid = f.get('preset_id')
                if fid:
                    try:
                        int_fid = int(fid)
                    except (ValueError, TypeError):
                        continue
                    if int_fid in presets and presets[int_fid].preset_type == 'options':
                        f['choice'] = presets[int_fid].value
        return states


class TransitionViewSet(CustomModelViewSet):
    """连线管理"""
    model = Transition
    queryset = Transition.objects.all()
    serializer_class = TransitionSerializer
    filter_fields = ['workflow', 'from_state', 'to_state']
    pagination_class = None  # disable pagination — all transitions for a workflow must load

    def get_queryset(self):
        qs = super().get_queryset()
        workflow_pk = self.request.query_params.get('workflow') or \
                      self.kwargs.get('workflow_pk')
        if workflow_pk:
            qs = qs.filter(workflow_id=workflow_pk)
        return qs

    @action(methods=['POST'], detail=False)
    def sync(self, request):
        """Full sync of transitions (auto-save) — resolve by from_node_key/to_node_key"""
        workflow_id = request.data.get('workflow_id')
        transitions = request.data.get('transitions', [])
        if not workflow_id:
            return ErrorResponse(msg='workflow_id required')
        # Build node_key → State.id lookup
        state_map = {s.node_key: s.id for s in State.objects.filter(workflow_id=workflow_id) if s.node_key}
        existing_ids = set(Transition.objects.filter(workflow_id=workflow_id).values_list('id', flat=True))
        incoming_ids = set()
        for t in transitions:
            tid = t.get('id')
            clean = _filter_model_fields(Transition, t)
            clean.pop('id', None)
            # Always strip old from_state_id/to_state_id — resolve solely from node_key
            clean.pop('from_state_id', None)
            clean.pop('to_state_id', None)
            fnk = t.get('from_node_key', '')
            tnk = t.get('to_node_key', '')
            if fnk and fnk in state_map:
                clean['from_state_id'] = state_map[fnk]
            if tnk and tnk in state_map:
                clean['to_state_id'] = state_map[tnk]
            # Skip transitions that can't resolve source or target
            if 'from_state_id' not in clean or 'to_state_id' not in clean:
                continue
            if tid and Transition.objects.filter(id=tid, workflow_id=workflow_id).exists():
                Transition.objects.filter(id=tid).update(**clean)
                incoming_ids.add(tid)
            else:
                clean['workflow_id'] = workflow_id
                new_t = Transition.objects.create(**clean)
                incoming_ids.add(new_t.id)
        to_delete = existing_ids - incoming_ids
        Transition.objects.filter(id__in=to_delete).delete()
        # Also purge legacy transitions without node_key
        from django.db.models import Q
        Transition.objects.filter(workflow_id=workflow_id).filter(
            Q(from_node_key__isnull=True) | Q(to_node_key__isnull=True)
        ).delete()
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
        """批量更新字段 — writes Rule[] directly to State.fields JSONField."""
        state_id = request.data.get('state_id')
        fields = request.data.get('fields', [])
        if not state_id:
            return ErrorResponse(msg='state_id required')
        # Batch-fetch presets to avoid N+1 queries
        preset_ids = {f.get('itsmPresetId') or f.get('preset_id') for f in fields if f.get('itsmPresetId') or f.get('preset_id')}
        presets_map = {}
        if preset_ids:
            from itsm.models.preset import Preset
            state = State.objects.only('workflow__project_id').select_related('workflow').filter(id=state_id).first()
            qs = Preset.objects.filter(id__in=preset_ids)
            if state and state.workflow.project_id:
                qs = qs.filter(project_id=state.workflow.project_id)
            presets_map = {p.id: p for p in qs}
        for f in fields:
            preset_id = f.get('itsmPresetId') or f.get('preset_id')
            if preset_id:
                try:
                    preset_id = int(preset_id)
                except (ValueError, TypeError):
                    preset_id = None
                preset = presets_map.get(preset_id) if preset_id else None
                if preset and preset.preset_type == 'options':
                    # Write options into form-create Rule format (top-level options)
                    f['options'] = preset.value
                else:
                    f['itsmPresetId'] = None
        # Write the complete Rule[] directly to State.fields JSONField
        State.objects.filter(id=state_id).update(fields=fields)
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
