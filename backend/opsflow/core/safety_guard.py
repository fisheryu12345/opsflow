"""Pipeline Tree 安全校验器 — 原子白名单从 atom_registry 动态加载"""

from .atom_registry import get_whitelist, get_high_risk_atoms, get_backup_required_atoms

MAX_RETRIES = 10

# 兼容旧代码的模块级引用（惰性加载）
def WHITELIST_ATOMS():
    return get_whitelist()

def HIGH_RISK_ATOMS():
    return get_high_risk_atoms()

def BACKUP_REQUIRED_ATOMS():
    return get_backup_required_atoms()


def validate_pipeline(pipeline: dict) -> dict:
    """
    校验 Pipeline Tree JSON。
    返回 {'valid': bool, 'errors': [str], 'warnings': [str]}
    """
    if not isinstance(pipeline, dict):
        return {'valid': False, 'errors': ['pipeline 必须为 dict'], 'warnings': []}

    nodes = pipeline.get('nodes', [])
    edges = pipeline.get('edges', [])
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

    # 孤儿节点检测
    for nid in node_ids:
        if nid != start_node_id and nid not in edge_to:
            warnings.append(f"节点 '{nid}' 可能是孤儿节点（无入边）")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
    }
