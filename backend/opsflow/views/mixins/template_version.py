"""Template Version — 版本管理/发布/回滚端点 Mixin"""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from opsflow.core.safety_guard import validate_pipeline
from opsflow.core.bamboo_validator import validate_bamboo_compatibility
from opsflow.core.audit_logger import log_operation
from opsflow.serializers import FlowTemplateSerializer


class TemplateVersionMixin:
    """版本管理、发布、回滚端点混入"""

    @action(detail=True, methods=['post'])
    def confirm_draft(self, request, pk=None):
        """用户确认草稿，发布为 V1"""
        template = self.get_object()
        if not template.is_draft:
            return Response({'code': 4000, 'msg': '不是草稿状态', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程存在安全风险，请检查后再确认',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        bamboo_check = validate_bamboo_compatibility(template.pipeline_tree)
        if not bamboo_check.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程不兼容 bamboo-engine',
                'data': {'bamboo_check': bamboo_check}
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        # ── 结束 ──

        template.is_draft = False
        version_note = request.data.get('version_note', '')
        template.publish_snapshot(user=request.user, version_note=version_note)
        log_operation(request.user, 'publish', 'template', template.id, template.name, {'version': template.version - 1}, request)
        # ── 节点持久化同步 ──
        from opsflow.core.node_sync import sync_template_nodes
        sync_template_nodes(template)
        # ── 结束 ──
        return Response({'code': 2000, 'msg': f'已发布 V{template.version - 1}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """已发布模板发布新版本"""
        template = self.get_object()
        if template.is_draft:
            return Response({'code': 4000, 'msg': '草稿模板请使用 confirm_draft', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)

        safety = validate_pipeline(template.pipeline_tree)
        if not safety.get('valid'):
            return Response({
                'code': 4000, 'msg': '流程存在安全风险',
                'data': {'validation': safety}
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        template.save(update_fields=['global_vars'])
        # ── 结束 ──

        version_note = request.data.get('version_note', '')
        template.publish_snapshot(user=request.user, version_note=version_note)
        log_operation(request.user, 'publish', 'template', template.id, template.name, {'version': template.version - 1}, request)
        # ── 节点持久化同步 ──
        from opsflow.core.node_sync import sync_template_nodes
        sync_template_nodes(template)
        # ── 结束 ──
        return Response({'code': 2000, 'msg': f'已发布 V{template.version - 1}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['get'], url_path='versions')
    def list_versions(self, request, pk=None):
        """返回版本历史列表"""
        template = self.get_object()
        from opsflow.serializers import TemplateVersionSerializer
        qs = template.versions.all()
        serializer = TemplateVersionSerializer(qs, many=True)
        return Response({'code': 2000, 'msg': 'success', 'data': serializer.data})

    @action(detail=True, methods=['post'])
    def rollback(self, request, pk=None):
        """回滚到指定版本"""
        template = self.get_object()
        version_id = request.data.get('version')
        if not version_id:
            return Response({'code': 4000, 'msg': 'version is required', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            target = template.versions.get(version=version_id)
        except Exception:
            return Response({'code': 4000, 'msg': f'版本 V{version_id} 不存在', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)
        template.pipeline_tree = target.pipeline_tree
        template.global_vars = target.global_vars
        template.is_draft = False
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(template.pipeline_tree or {}, template.global_vars or {})
        template.global_vars = cleaned
        # ── 结束 ──
        template.save()
        log_operation(request.user, 'rollback', 'template', template.id, template.name, {'version': version_id}, request)
        # ── 节点持久化同步（回滚改变了 pipeline_tree） ──
        from opsflow.core.node_sync import sync_template_nodes
        sync_template_nodes(template)
        # ── 结束 ──
        return Response({'code': 2000, 'msg': f'已回滚到 V{version_id}', 'data': FlowTemplateSerializer(template).data})

    @action(detail=True, methods=['post'])
    def version_diff(self, request, pk=None):
        """对比两个版本的 pipeline_tree — 使用 DeepDiff"""
        import json
        from deepdiff import DeepDiff
        template = self.get_object()
        v1 = request.data.get('v1')
        v2 = request.data.get('v2')
        if not v1 or not v2:
            return Response({'code': 4000, 'msg': '需要指定 v1 和 v2 版本号', 'data': None})
        try:
            version1 = template.versions.get(version=v1)
            version2 = template.versions.get(version=v2)
        except Exception:
            return Response({'code': 4000, 'msg': '版本号不存在', 'data': None},
                            status=status.HTTP_404_NOT_FOUND)
        diff = DeepDiff(version1.pipeline_tree, version2.pipeline_tree, ignore_order=True)
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {'v1': v1, 'v2': v2, 'diff': json.loads(diff.to_json())}
        })

    @action(detail=True, methods=['get'])
    def diff_draft(self, request, pk=None):
        """对比当前草稿 vs 已发布版本（snapshot）"""
        import json
        from deepdiff import DeepDiff
        template = self.get_object()
        published = template.snapshot or {}
        published_tree = published.get('pipeline_tree')
        if not published_tree:
            return Response({'code': 4000, 'msg': '尚无已发布版本', 'data': None},
                            status=status.HTTP_400_BAD_REQUEST)
        diff = DeepDiff(published_tree, template.pipeline_tree, ignore_order=True)
        return Response({
            'code': 2000, 'msg': 'success',
            'data': {
                'published_version': template.version - 1,
                'diff': json.loads(diff.to_json()),
            }
        })
