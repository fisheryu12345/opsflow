from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer
from opsflow.core.llm_service import generate_pipeline, optimize_layout, analyze_pipeline, refine_pipeline
from opsflow.core.safety_guard import validate_pipeline
from opsflow.core.bamboo_builder import validate_bamboo_compatibility
from dvadmin.utils.json_response import DetailResponse


class FlowTemplateViewSet(viewsets.ModelViewSet):
    queryset = FlowTemplate.objects.all()
    serializer_class = FlowTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_draft', 'created_by']
    search_fields = ['name']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    @action(detail=False, methods=['post'])
    def create_from_ai(self, request):
        """接收自然语言描述，调用 DeepSeek 生成 Pipeline Tree，保存为草稿"""
        nl_input = request.data.get('input', '')
        target_hosts = request.data.get('target_hosts', [])
        global_vars = request.data.get('global_vars', {})

        if not nl_input:
            return Response({'code': 4000, 'msg': 'input is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            pipeline = generate_pipeline(nl_input, target_hosts)
            validation = validate_pipeline(pipeline)
            bamboo_check = validate_bamboo_compatibility(pipeline)

            template = FlowTemplate.objects.create(
                name=f"AI: {nl_input[:50]}",
                pipeline_tree=pipeline,
                target_hosts=target_hosts,
                global_vars=global_vars,
                ai_original_tree=pipeline.copy(),
                is_draft=True,
                created_by=request.user,
            )
            return Response({
                'code': 2000, 'msg': 'success',
                'data': {
                    'template': FlowTemplateSerializer(template).data,
                    'validation': validation,
                    'bamboo_check': bamboo_check,
                }
            })
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def confirm_draft(self, request, pk=None):
        """用户确认草稿，标记 is_draft=False 正式入库"""
        template = self.get_object()
        if not template.is_draft:
            return Response({'code': 4000, 'msg': '不是草稿状态', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        # 重新校验 SafetyGuard
        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '安全校验失败',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        # bamboo-engine 兼容性校验
        bamboo_check = validate_bamboo_compatibility(template.pipeline_tree)
        if not bamboo_check.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程不兼容 bamboo-engine',
                'data': {'bamboo_check': bamboo_check}
            }, status=status.HTTP_400_BAD_REQUEST)

        template.is_draft = False
        template.save()
        return Response({'code': 2000, 'msg': 'success', 'data': FlowTemplateSerializer(template).data})

    @action(detail=False, methods=['post'])
    def ai_layout(self, request):
        """接收画布节点和连线，调用 AI 进行布局优化"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return Response({'code': 4000, 'msg': 'nodes is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            positions = optimize_layout(nodes, edges)
            return Response({'code': 2000, 'msg': 'success', 'data': {'positions': positions}})
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        """返回 AI 原稿 vs 当前修改，供前端 Diff 弹窗使用"""
        template = self.get_object()
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'ai_original': template.ai_original_tree,
                'current': template.pipeline_tree,
            }
        })

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """AI 分析流程：描述流程目的、步骤及潜在风险"""
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        if not nodes:
            return Response({'code': 4000, 'msg': 'nodes is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            result = analyze_pipeline(nodes, edges)
            return Response({'code': 2000, 'msg': 'success', 'data': result})
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def refine(self, request):
        """多轮对话：根据用户新指令修改现有 Pipeline Tree"""
        nl_input = request.data.get('input', '')
        nodes = request.data.get('nodes', [])
        edges = request.data.get('edges', [])
        target_hosts = request.data.get('target_hosts', [])

        if not nl_input:
            return Response({'code': 4000, 'msg': 'input is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            pipeline = refine_pipeline(nl_input, nodes, edges, target_hosts)
            validation = validate_pipeline(pipeline)
            bamboo_check = validate_bamboo_compatibility(pipeline)
            return Response({
                'code': 2000, 'msg': 'success',
                'data': {
                    'pipeline_tree': pipeline,
                    'validation': validation,
                    'bamboo_check': bamboo_check,
                }
            })
        except Exception as e:
            return Response({'code': 4000, 'msg': str(e), 'data': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
