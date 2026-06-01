"""插件退役管理 — 检测已弃用插件在模板中的引用

参考 bk_sops pipeline_web/plugin_management/models.py + utils.py
"""

import logging

logger = logging.getLogger(__name__)


def check_deprecated_plugins_in_template(template) -> dict:
    """递归扫描模板 pipeline_tree，检测已弃用的插件引用

    Args:
        template: FlowTemplate 实例

    Returns:
        dict: {
            "found": bool,
            "plugins": [
                {
                    "node_id": "...",
                    "node_label": "...",
                    "plugin_code": "...",
                    "plugin_version": "...",
                    "phase": 1 or 2,
                    "phase_label": "即将弃用" or "已弃用",
                    "subprocess": "subprocess_name or None",
                }
            ]
        }
    """
    from opsflow.models import PluginMeta

    # 获取已弃用的插件
    deprecated_phases = [PluginMeta.PHASE_DEPRECATED, PluginMeta.PHASE_WILL_BE_DEPRECATED]
    deprecated = PluginMeta.objects.filter(phase__in=deprecated_phases)
    if not deprecated.exists():
        return {"found": False, "plugins": []}

    # 构建 (code, version) 集合
    deprecated_map = {}
    for pm in deprecated:
        key = (pm.code, pm.version)
        deprecated_map[key] = pm.phase

    found = []

    def walk(nodes, subprocess_name=None):
        for node in (nodes or []):
            node_type = node.get('node_type', '')
            if node_type == 'subprocess':
                # 递归检查子流程
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    try:
                        from opsflow.models import FlowTemplate
                        target = FlowTemplate.objects.get(id=target_id)
                        target_tree = target.pipeline_tree or {}
                        walk(target_tree.get('nodes', []),
                             subprocess_name=node.get('label', node['id']))
                    except FlowTemplate.DoesNotExist:
                        pass

            atom = node.get('atom_type', '')
            if not atom:
                continue

            version = node.get('plugin_version') or node.get('_plugin_version', '')
            if not version:
                # 默认使用最新版本检测
                query = PluginMeta.objects.filter(code=atom, phase__in=deprecated_phases)
                if query.exists():
                    for pm in query:
                        found.append({
                            "node_id": node['id'],
                            "node_label": node.get('label', node['id']),
                            "plugin_code": pm.code,
                            "plugin_version": pm.version,
                            "phase": pm.phase,
                            "phase_label": dict(PluginMeta.PHASE_CHOICES).get(pm.phase, ''),
                            "subprocess": subprocess_name,
                        })
                continue

            if (atom, version) in deprecated_map:
                phase = deprecated_map[(atom, version)]
                found.append({
                    "node_id": node['id'],
                    "node_label": node.get('label', node['id']),
                    "plugin_code": atom,
                    "plugin_version": version,
                    "phase": phase,
                    "phase_label": dict(PluginMeta.PHASE_CHOICES).get(phase, ''),
                    "subprocess": subprocess_name,
                })

    pipeline_tree = template.pipeline_tree or {}
    walk(pipeline_tree.get('nodes', []))

    return {"found": bool(found), "plugins": found}
