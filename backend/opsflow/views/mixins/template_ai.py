"""Template AI — AI 生成/分析/布局端点 Mixin"""

import re
import logging

from rest_framework.decorators import action
from rest_framework import status

from opsflow.core.llm_service import generate_pipeline, analyze_pipeline, refine_pipeline
from opsflow.core.layout import compute_layout
from opsflow.core.safety_guard import validate_pipeline
from opsflow.core.bamboo_validator import validate_bamboo_compatibility
from opsflow.plugins.registry import get_plugin
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

logger = logging.getLogger(__name__)


def _get_request_language(request):
    """Extract language preference from request data, header, or session."""
    # Check request body first (sent by frontend)
    lang = request.data.get('language', '')
    if lang in ('zh-hans', 'en'):
        return lang
    # Fall back to Accept-Language header
    from django.utils.translation import get_language
    lang = get_language() or request.META.get('HTTP_ACCEPT_LANGUAGE', 'zh-hans')
    if lang.startswith('en'):
        return 'en'
    return 'zh-hans'

# Module-level Chinese message constants (used in AI validation responses)
MSG_UNSUPPORTED_OPERATION = '好的，我理解您想要这个功能，但目前系统暂不支持，建议换个方式实现'
MSG_UNSUPPORTED_ATOM = '好的，我理解您的意思，但目前系统还不支持这个操作，咱先试试其他功能吧'


def _enrich_atom_nodes(pipeline: dict) -> dict:
    """Enrich AI-generated atom nodes with group/risk_level from plugin registry

    AI output lacks 'group' on atom nodes, causing frontend updateAtomNode()
    to fall back to default icon (◇) and color (#409EFF). This injects the
    correct group/risk_level so the frontend can resolve proper icon/color/desc.
    """
    for node in pipeline.get('nodes', []):
        atom_type = node.get('atom_type', '')
        if not atom_type:
            continue
        # Only process atom nodes (node_type is '' or 'atom')
        if node.get('node_type', '') not in ('', 'atom'):
            continue
        cls = get_plugin(atom_type)
        if cls is None:
            continue
        if not node.get('group'):
            node['group'] = cls.group
        if not node.get('risk_level'):
            node['risk_level'] = cls.risk_level
    return pipeline


class TemplateAIMixin:
    """AI 生成、分析、布局端点混入"""

    @classmethod
    def _validate_ai_pipeline(cls, pipeline: dict, nl_input: str) -> dict:
        """Validate an AI-generated pipeline, returning a result dict.

        Returns:
            On failure: {'valid': False, 'msg': str, 'data': dict}
            On success: {'valid': True, 'validation': dict, 'bamboo_check': dict}
        """
        # AI reported unsupported request
        errors = pipeline.get('_errors') or pipeline.get('_unsupported')
        if errors:
            return {'valid': False, 'msg': MSG_UNSUPPORTED_OPERATION,
                    'data': {'pipeline_tree': pipeline}}

        # AI should not generate shell atoms — indicates fallback to non-existent feature
        if any(n.get('atom_type') == 'shell' for n in pipeline.get('nodes', [])):
            return {'valid': False, 'msg': MSG_UNSUPPORTED_OPERATION,
                    'data': {'pipeline_tree': pipeline}}

        # Check cross-platform VM misuse: user says VM/虚拟机 but AI uses other platform atoms
        nl_lower = nl_input.lower()
        is_vm_request = any(kw in nl_lower for kw in ['vm', '虚拟机', '虚机', 'esxi'])
        for node in pipeline.get('nodes', []):
            atom = node.get('atom_type', '')
            if is_vm_request and atom.startswith('netapp_'):
                return {'valid': False, 'msg': MSG_UNSUPPORTED_OPERATION,
                        'data': {'pipeline_tree': pipeline}}

        # Enrich atom nodes with group/risk_level from plugin registry
        _enrich_atom_nodes(pipeline)

        # Run validation checks
        validation = validate_pipeline(pipeline)
        bamboo_check = validate_bamboo_compatibility(pipeline)

        # Reject pipelines with unknown atoms or other severe errors
        if not validation.get('valid'):
            unknown_atoms = set()
            for err in validation.get('errors', []):
                m = re.search(r"未知原子类型 '(\w+)'", err)
                if m:
                    unknown_atoms.add(m.group(1))
            if unknown_atoms:
                msg = MSG_UNSUPPORTED_ATOM
            else:
                msg = '流程有一些问题需要调整，请检查后重试'
            return {'valid': False, 'msg': msg,
                    'data': {'validation': validation, 'pipeline_tree': pipeline}}

        return {'valid': True, 'validation': validation, 'bamboo_check': bamboo_check}

    @action(detail=False, methods=['post'])
    def create_from_ai(self, request):
        """接收自然语言描述，调用 DeepSeek 生成 Pipeline Tree，保存为草稿"""
        nl_input = request.data.get('input', '')
        target_hosts = request.data.get('target_hosts', [])
        global_vars = request.data.get('global_vars', {})

        if not nl_input:
            return ErrorResponse(msg='input is required', code=4000)
        try:
            pipeline = generate_pipeline(nl_input, target_hosts, language=_get_request_language(request))

            # Validate the AI-generated pipeline
            result = self._validate_ai_pipeline(pipeline, nl_input)
            if not result['valid']:
                return ErrorResponse(msg=result['msg'], data=result['data'], code=4000)
            validation = result['validation']
            bamboo_check = result['bamboo_check']

            from opsflow.models import FlowTemplate
            from opsflow.serializers import FlowTemplateSerializer
            project_kwargs = self.resolve_project_kwargs(request)
            template = FlowTemplate.objects.create(
                name=f"AI: {nl_input[:50]}",
                pipeline_tree=pipeline,
                target_hosts=target_hosts,
                global_vars=global_vars,
                ai_original_tree=pipeline.copy(),
                is_draft=True,
                created_by=request.user,
                **project_kwargs,
            )
            return DetailResponse(data={
                'template': FlowTemplateSerializer(template).data,
                'validation': validation,
                'bamboo_check': bamboo_check,
            })
        except Exception as e:
            return ErrorResponse(msg=str(e), code=4000, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """AI 分析流程：描述流程目的、步骤及潜在风险"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return ErrorResponse(msg='nodes is required', code=4000)
        try:
            result = analyze_pipeline(nodes, edges, language=_get_request_language(request))
            return DetailResponse(data=result)
        except Exception as e:
            return ErrorResponse(msg=str(e), code=4000, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def refine(self, request):
        """多轮对话：根据用户新指令修改现有 Pipeline Tree"""
        nl_input = request.data.get('input', '')
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        target_hosts = request.data.get('target_hosts', [])
        chat_history = request.data.get('chat_history', [])

        if not nl_input:
            return ErrorResponse(msg='input is required', code=4000)
        try:
            pipeline = refine_pipeline(nl_input, nodes, edges, target_hosts, chat_history, language=_get_request_language(request))

            # Extract AI answer (non-modification scenarios: user question/analysis)
            ai_answer = pipeline.pop('_answer', None)

            # Validate the refined pipeline
            result = self._validate_ai_pipeline(pipeline, nl_input)
            if not result['valid']:
                return ErrorResponse(msg=result['msg'], data=result['data'], code=4000)
            validation = result['validation']
            bamboo_check = result['bamboo_check']

            response_data = {
                'pipeline_tree': pipeline,
                'validation': validation,
                'bamboo_check': bamboo_check,
            }
            if ai_answer:
                response_data['message'] = ai_answer
            return DetailResponse(data=response_data)
        except Exception as e:
            return ErrorResponse(msg=str(e), code=4000, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def ai_layout(self, request):
        """布局优化 — 使用确定性 Sugiyama 分层布局引擎"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return ErrorResponse(msg='nodes is required', code=4000)
        try:
            positions = compute_layout(nodes, edges)
            return DetailResponse(data={'positions': positions})
        except Exception as e:
            logger.exception("Layout failed")
            return ErrorResponse(msg=str(e), code=4000, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        """返回 AI 原稿 vs 当前修改，供前端 Diff 弹窗使用"""
        template = self.get_object()
        return DetailResponse(data={
            'ai_original': template.ai_original_tree,
            'current': template.pipeline_tree,
        })
