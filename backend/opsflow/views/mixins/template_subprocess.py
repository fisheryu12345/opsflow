"""Template Subprocess — 子流程版本追踪端点 Mixin"""

from rest_framework.decorators import action
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response

from opsflow.models import FlowTemplate


class TemplateSubprocessMixin:
    """子流程版本追踪端点混入"""

    @action(detail=True, methods=['get'], url_path='subprocess-status')
    def subprocess_status(self, request, pk=None):
        """检查子流程引用版本是否过期

        从 snapshot.subprocess_refs 读取引用版本，对比目标模板当前版本。
        """
        template = self.get_object()
        snapshot = template.snapshot or {}
        subprocess_refs = snapshot.get('subprocess_refs', {})

        # fallback: 实时扫描 pipeline_tree
        if not subprocess_refs:
            subprocess_refs = self._extract_subprocess_refs(template)

        details = []
        for node_id, ref in subprocess_refs.items():
            target_id = ref.get('target_template_id')
            ref_version = ref.get('target_version')
            try:
                target = FlowTemplate.objects.get(id=target_id)
                current_version = target.version or 1
                stale = (ref_version is not None and
                         current_version is not None and
                         ref_version != current_version)
            except FlowTemplate.DoesNotExist:
                current_version = None
                stale = True

            details.append({
                'node_id': node_id,
                'target_template_id': target_id,
                'target_name': ref.get('target_name', ''),
                'referenced_version': ref_version,
                'current_version': current_version,
                'stale': stale,
            })

        stale_count = sum(1 for d in details if d['stale'])
        return DetailResponse(data={
                'total': len(details),
                'stale': stale_count,
                'details': details,
            },
        })

    @action(detail=True, methods=['post'], url_path='update-subprocess-refs')
    def update_subprocess_refs(self, request, pk=None):
        """批量更新所有子流程引用为最新版本"""
        template = self.get_object()
        tree = template.pipeline_tree or {}
        nodes = tree.get('nodes', [])

        updated = []
        for node in nodes:
            if node.get('node_type') != 'subprocess':
                continue
            params = node.get('params', {}) or {}
            target_id = params.get('target_template_id')
            if not target_id:
                continue
            try:
                target = FlowTemplate.objects.get(id=target_id)
                current_version = target.version or 1
                params['_referenced_version'] = current_version
                node['params'] = params
                updated.append({
                    'node_id': node['id'],
                    'target_template_id': target_id,
                    'new_version': current_version,
                })
            except FlowTemplate.DoesNotExist:
                continue

        template.pipeline_tree = tree
        template.save(update_fields=['pipeline_tree'])
        return DetailResponse(data={
                'total': len(updated),
                'updated_nodes': updated,
                'message': f'已更新 {len(updated)} 个子流程引用',
            },
        })

    def _extract_subprocess_refs(self, template) -> dict:
        """从 pipeline_tree 实时提取子流程引用（fallback）"""
        refs = {}
        tree = template.pipeline_tree or {}
        for node in tree.get('nodes', []):
            if node.get('node_type') == 'subprocess':
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    refs[node['id']] = {
                        'target_template_id': target_id,
                        'target_version': None,
                        'target_name': '',
                    }
        return refs
