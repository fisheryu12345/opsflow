"""Pipeline Tree 安全校验器 — 原子白名单从 PLUGIN_REGISTRY 动态加载"""

from opsflow.plugins.registry import PLUGIN_REGISTRY

MAX_RETRIES = 10

# 兼容旧代码的模块级引用（惰性加载）
def WHITELIST_ATOMS():
    """返回所有已注册插件的 code 集合"""
    return set(PLUGIN_REGISTRY.keys())

def HIGH_RISK_ATOMS():
    """返回 risk_level == 'high' 的插件 code 集合"""
    result = set()
    for code, versions in PLUGIN_REGISTRY.items():
        # 兼容两种格式：{code: class}（旧）或 {code: {version: class}}（多版本）
        if isinstance(versions, dict):
            cls = next(iter(versions.values())) if versions else None
        else:
            cls = versions
        if cls and getattr(cls, 'risk_level', 'low') == 'high':
            result.add(code)
    return result

def BACKUP_REQUIRED_ATOMS():
    """已废弃 — BasePlugin 不再追踪 dependencies，始终返回空集"""
    return set()


def validate_pipeline(pipeline: dict) -> dict:
    """
    校验 Pipeline Tree JSON。
    返回 {'valid': bool, 'errors': [str], 'warnings': [str]}
    """
    if not isinstance(pipeline, dict):
        return {'valid': False, 'errors': ['pipeline 必须为 dict'], 'warnings': []}

    nodes = pipeline.get('nodes', [])
    edges = pipeline.get('edges', [])

    # 空 pipeline 检测
    if not nodes or len(nodes) == 0:
        return {'valid': False, 'errors': ['pipeline 中无节点，请先编辑并保存模板'], 'warnings': []}

    errors = []
    warnings = []
    node_ids = {n['id'] for n in nodes}
    edge_from = {e.get('from') for e in edges}
    edge_to = {e.get('to') for e in edges}

    start_node_id = nodes[0]['id'] if nodes else None

    for node in nodes:
        nid = node.get('id', '')
        atom = node.get('atom_type', '')

        # 原子白名单
        whitelist = WHITELIST_ATOMS()
        if atom and atom not in whitelist:
            errors.append(f"未知原子类型 '{atom}'（节点 {nid}）")

        # 循环上限
        retries = node.get('max_retries', 0)
        if isinstance(retries, (int, float)) and retries > MAX_RETRIES:
            errors.append(f"节点 {nid} 重试次数 {retries} 超过上限 {MAX_RETRIES}")

        # 高危标记：没有回滚路径
        high_risk = HIGH_RISK_ATOMS()
        if atom in high_risk:
            has_rollback = any(
                e.get('label') in ('failure', 'rollback') and e.get('from') == nid
                for e in edges
            )
            if not has_rollback:
                warnings.append(f"高危节点 '{nid}' 没有回滚路径")

        # 备份前置检查：高风险操作前需要有 backup_file 前置节点
        backup_required = BACKUP_REQUIRED_ATOMS()
        if atom in backup_required:
            predecessors = [e.get('from') for e in edges if e.get('to') == nid]
            node_map = {n['id']: n for n in nodes}
            pred_has_backup = any(
                node_map.get(pred, {}).get('atom_type', '') == 'backup_file'
                for pred in predecessors
            )
            if not pred_has_backup:
                warnings.append(f"节点 '{nid}'（{atom}）前缺少 backup_file 步骤")

        # 子流程节点校验
        if atom == '' and node.get('node_type') == 'subprocess':
            sub_params = node.get('params', {}) or {}
            target_id = sub_params.get('target_template_id')
            if not target_id:
                errors.append(f"子流程节点 '{nid}' 缺少 target_template_id")
            else:
                from opsflow.models import FlowTemplate
                try:
                    target = FlowTemplate.objects.get(id=target_id)
                    if target.is_draft:
                        errors.append(f"子流程节点 '{nid}' 引用的模板为草稿，请先发布")
                    elif not target.snapshot:
                        errors.append(f"子流程节点 '{nid}' 引用的模板 '{target.name}' 无发布快照")
                    else:
                        from opsflow.core.pipeline_builder.validation import _detect_circular_ref
                        try:
                            _detect_circular_ref(target)
                        except ValueError as e:
                            errors.append(str(e))

                    # 版本过期检查
                    ref_version = sub_params.get('_referenced_version')
                    current_version = target.version or 1
                    if ref_version and ref_version != current_version:
                        warnings.append(
                            f"子流程节点 '{nid}' 引用模板 '{target.name}' 版本已过时 "
                            f"(引用 V{ref_version}, 当前 V{current_version})"
                        )
                except FlowTemplate.DoesNotExist:
                    errors.append(f"子流程节点 '{nid}' 引用的模板 id={target_id} 不存在")

    # 孤儿节点检测
    for nid in node_ids:
        if nid != start_node_id and nid not in edge_to:
            warnings.append(f"节点 '{nid}' 可能是孤儿节点（无入边）")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
    }
