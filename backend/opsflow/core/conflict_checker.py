"""冲突检测规则引擎 — 检测节点配置中的语义冲突

参考 bk_sops format.py 中的冲突检查逻辑，检测 6 条规则：

1. timeout + error_ignorable/auto_retry 冲突
2. max_retries + skippable 同时启用
3. timeout < retry_delay
4. 并行网关缺少汇聚网关
5. 排除节点但仍有入边
6. ExclusiveGateway 出边缺少条件
"""

from typing import Any


def check_config_conflicts(pipeline_tree: dict) -> dict:
    """检查 pipeline_tree 中的配置冲突

    Returns:
        {"warnings": [str], "errors": [str]}
    """
    warnings = []
    errors = []

    nodes = pipeline_tree.get('nodes', []) or []
    edges = pipeline_tree.get('edges', []) or []

    # 建立节点查找 map
    node_map = {n.get('id', ''): n for n in nodes}
    out_edges: dict[str, list] = {}
    in_edges: dict[str, list] = {}
    for e in edges:
        f = e.get('from', '')
        t = e.get('to', '')
        out_edges.setdefault(f, []).append(e)
        in_edges.setdefault(t, []).append(e)

    for node in nodes:
        nid = node.get('id', '')
        ntype = node.get('node_type', '')
        params = node.get('params', {}) or {}
        config = node.get('node_config', {}) or {}

        max_retries = params.get('max_retries', config.get('max_retries', 0))
        timeout = params.get('timeout_seconds', config.get('timeout_seconds', 0))
        retry_delay = config.get('retry_delay', 0)
        skippable = config.get('optional', params.get('optional', False))
        error_ignorable = config.get('error_ignorable', False)
        auto_retry = config.get('auto_retry', {})

        # Rule 1: timeout + error_ignorable / auto_retry 冲突
        if timeout and timeout > 0:
            if error_ignorable:
                warnings.append(
                    f'Node "{nid}": timeout and error_ignorable enabled together '
                    f'(bamboo-engine does not support this combination)',
                )
            if auto_retry.get('enable'):
                warnings.append(
                    f'Node "{nid}": timeout and auto_retry enabled together '
                    f'(bamboo-engine does not support this combination)',
                )

        # Rule 2: max_retries + skippable
        if max_retries > 0 and skippable:
            warnings.append(
                f'Node "{nid}": max_retries={max_retries} and skippable enabled together '
                f'(retry will override skip)',
            )

        # Rule 3: timeout < retry_delay
        if timeout > 0 and retry_delay > 0 and timeout < retry_delay:
            errors.append(
                f'Node "{nid}": timeout_seconds({timeout}) < retry_delay({retry_delay})',
            )

        # Rule 4: 网关校验
        if ntype == 'parallel_gateway':
            has_converge = _has_converge_sink(nid, edges, node_map)
            if not has_converge:
                warnings.append(
                    f'Parallel gateway "{nid}" may be missing a converge gateway',
                )

        # Rule 6: ExclusiveGateway 出边条件
        if ntype == 'exclusive_gateway':
            for e in out_edges.get(nid, []):
                if not e.get('condition', '').strip():
                    target = e.get('to', '')
                    target_name = node_map.get(target, {}).get('label', target)
                    warnings.append(
                        f'Edge "{nid}" → "{target_name}" has no condition expression',
                    )

    # Rule 5: 排除节点但仍有入边（需传入 excluded_nodes 列表）
    # 由调用方在执行方案时检查

    return {'warnings': warnings, 'errors': errors}


def _has_converge_sink(node_id: str, edges: list, node_map: dict) -> bool:
    """检查从 node_id 出发的路径是否最终连接到汇聚网关"""
    visited = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        n = node_map.get(current, {})
        if n.get('node_type') == 'converge_gateway':
            return True
        for e in edges:
            if e.get('from') == current:
                stack.append(e.get('to'))
    return False
