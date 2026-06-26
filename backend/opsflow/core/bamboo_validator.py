"""Bamboo Pipeline Tree 兼容性验证器

从 bamboo_builder.py 提取的独立验证模块，负责校验 pipeline_tree
是否能被 bamboo-engine 正确执行。

包含网关配对检查、出入度校验、环检测、条件引用校验等。
"""

import re
import logging

logger = logging.getLogger(__name__)

# 匹配 ${expr} 整体，再从 expr 中解析 node_id.key 引用
_EXPR_PATTERN = re.compile(r'\$\{([^}]*)\}')
_VAR_REF_PATTERN = re.compile(r'([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)')


def _detect_exclusive_gateway_loops(effective_nodes: list, effective_edges: list) -> list:
    """检测排他网关回环边，返回回环边列表

    对排他网关的每条出边，BFS 从目标节点出发，看是否能回到网关自身。
    """
    gateway_ids = {n['id'] for n in effective_nodes if n.get('node_type') == 'exclusive_gateway'}
    adj = {n['id']: [] for n in effective_nodes}
    for e in effective_edges:
        adj.setdefault(e['from'], []).append(e['to'])

    def _bfs_reaches(start: str, target: str, max_depth: int = 100) -> bool:
        visited = {start}
        q = [start]
        depth = 0
        while q and depth < max_depth:
            node = q.pop(0)
            if node == target:
                return True
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
            depth += 1
        return False

    loop_edges = []
    for e in effective_edges:
        if e['from'] in gateway_ids and _bfs_reaches(e['to'], e['from']):
            loop_edges.append(e)
    return loop_edges


def _has_loop_edges(pipeline_tree: dict) -> bool:
    """快速判断 pipeline_tree 是否有排他网关回环边"""
    nodes = pipeline_tree.get('nodes', []) or []
    edges = pipeline_tree.get('edges', []) or []
    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_edges = [e for e in edges if e.get('from') and e.get('to')]
    return bool(_detect_exclusive_gateway_loops(effective_nodes, effective_edges))


def validate_bamboo_compatibility(pipeline_tree: dict, skip_schema=False) -> dict:
    """校验 pipeline_tree 是否能被 bamboo-engine 执行

    Args:
        pipeline_tree: 流程树 dict
        skip_schema: True=跳过 JSON Schema 验证（如内部调用已在外层验证过）
    """
    errors = []
    warnings = []

    # JSON Schema 结构验证（参考 bk_sops Draft4Validator + WEB_PIPELINE_SCHEMA）
    if not skip_schema:
        from opsflow.core.pipeline_schema import validate_pipeline_schema
        schema_errors = validate_pipeline_schema(pipeline_tree)
        if schema_errors:
            errors.extend(schema_errors)
            # Schema 级别错误说明数据结构有误，直接返回不继续后续校验
            return {'valid': False, 'errors': errors, 'warnings': warnings}

    nodes = pipeline_tree.get('nodes', []) or []
    edges = pipeline_tree.get('edges', []) or []

    if not nodes:
        return {'valid': True, 'errors': [], 'warnings': ['空流程']}

    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]

    if not effective_nodes:
        return {'valid': True, 'errors': [], 'warnings': ['无有效节点']}

    # -----------------------------------------------------------
    # 前端 X6 已前置校验项（useGraphValidator.ts + validateConnection）
    # 保留后端检查作防御性校验，但用户提交前错误已被前端拦截
    # -----------------------------------------------------------
    # 检查节点 ID 唯一性（X6 原生保证 graph 内 ID 唯一）
    ids = [n['id'] for n in effective_nodes]
    if len(ids) != len(set(ids)):
        errors.append('节点 ID 不唯一')

    # 检查边引用（X6 边只能从实际节点 port 拖出/连入，已原生保证）
    for e in effective_edges:
        if e.get('from') not in effective_ids:
            errors.append(f"边起始节点 '{e.get('from')}' 不存在")
        if e.get('to') not in effective_ids:
            errors.append(f"边目标节点 '{e.get('to')}' 不存在")

    # Check cycle (tolerate exclusive gateway loopback edges)
    gateway_ids = {n['id'] for n in effective_nodes if n.get('node_type') == 'exclusive_gateway'}
    loop_edges = _detect_exclusive_gateway_loops(effective_nodes, effective_edges)
    loop_target_ids = {e['to'] for e in loop_edges}

    out_degree = {n['id']: [] for n in effective_nodes}
    in_degree = {n['id']: 0 for n in effective_nodes}
    for e in effective_edges:
        out_degree.setdefault(e['from'], []).append(e['to'])
        in_degree.setdefault(e['to'], 0)
        in_degree[e['to']] += 1

    queue = [nid for nid in effective_ids if in_degree.get(nid, 0) == 0]
    visited = 0
    while queue:
        nid = queue.pop(0)
        visited += 1
        for target in out_degree.get(nid, []):
            if nid in gateway_ids and target in loop_target_ids:
                continue
            in_degree[target] -= 1
            if in_degree[target] <= 0:
                queue.append(target)

    if visited != len(effective_nodes):
        if loop_edges:
            logger.info("Tolerating %d loop edges from exclusive gateways", len(loop_edges))
        else:
            errors.append('bamboo-engine does not support cycles')

    # 节点出入度合法性校验（前端 edge:connected 时已拦截超限连接 + label 检查）
    in_count: dict[str, int] = {n['id']: 0 for n in effective_nodes}
    out_count: dict[str, int] = {n['id']: 0 for n in effective_nodes}
    for e in edges:
        if e.get('from') in effective_ids:
            out_count[e['from']] = out_count.get(e['from'], 0) + 1
        if e.get('to') in effective_ids:
            in_count[e['to']] = in_count.get(e['to'], 0) + 1

    def _check_degree(n: dict, label: str, min_in: int, max_out: int | None):
        nid = n['id']
        name = n.get('label', nid)
        ic = in_count.get(nid, 0)
        oc = out_count.get(nid, 0)
        if ic < min_in:
            errors.append(f"{label} '{name}' 入度={ic}，要求 >= {min_in}")
        if max_out is not None and oc > max_out:
            errors.append(f"{label} '{name}' 出度={oc}，要求 <= {max_out}")

    for n in effective_nodes:
        nt = n.get('node_type', '')
        if nt in ('', 'atom'):
            ic = in_count.get(n['id'], 0)
            oc = out_count.get(n['id'], 0)
            name = n.get('label', n['id'])
            if ic < 1:
                errors.append(f"活动 '{name}' 入度={ic}，要求 >= 1（没有入边的活动永远不会被执行）")
            if oc > 2:
                errors.append(f"活动 '{name}' 出度={oc}，最多允许 2 条（success/failure）")
            if oc == 2:
                labels = {e.get('label', '') for e in edges if e.get('from') == n['id']}
                if labels != {'success', 'failure'}:
                    errors.append(f"活动 '{name}' 两条出边标签必须是 success 和 failure")
        elif nt == 'parallel_gateway':
            _check_degree(n, '并行网关', min_in=1, max_out=None)
        elif nt == 'conditional_parallel_gateway':
            _check_degree(n, '条件并行网关', min_in=1, max_out=None)
        elif nt == 'exclusive_gateway':
            _check_degree(n, '分支网关', min_in=1, max_out=None)
        elif nt == 'converge_gateway':
            _check_degree(n, '汇聚网关', min_in=1, max_out=1)

    # 检查网关出边条件（前端 edge:connected 时已 Prompt 选择标签 + save 前校验）
    for n in effective_nodes:
        node_type = n.get('node_type', '')
        successors = [e for e in effective_edges if e.get('from') == n['id']]
        if node_type in ('exclusive_gateway', 'conditional_parallel_gateway') and len(successors) > 1:
            labels = {e.get('label', '') for e in successors}
            if not labels:
                errors.append(f"排他网关 '{n.get('label', n['id'])}' 必须为每条出边设置 success 或 failure 标签")
            elif labels - {'success', 'failure'}:
                warnings.append(
                    f"排他网关 '{n.get('label', n['id'])}' 分支标签含非 success/failure 值")

        if node_type == 'converge_gateway' and len(successors) > 1:
            warnings.append(f"汇聚网关 '{n.get('label', n['id'])}' 有多条出边，将取第一条")

        if node_type == 'converge_gateway':
            predecessors = [e for e in effective_edges if e.get('to') == n['id']]
            if len(predecessors) < 2:
                warnings.append(f"汇聚网关 '{n.get('label', n['id'])}' 入边少于 2 条，建议改用直接连接")

    # 校验自定义网关条件中的 ${node_id.key} 引用（前端 PropertyPanel 编辑 + save 前已校验）
    for e in effective_edges:
        cond = e.get('condition', '').strip()
        if not cond:
            continue
        for block_match in _EXPR_PATTERN.finditer(cond):
            expr = block_match.group(1)
            for var_match in _VAR_REF_PATTERN.finditer(expr):
                ref_node_id = var_match.group(1)
                if ref_node_id not in effective_ids:
                    errors.append(
                        f"边 {e.get('from')}→{e.get('to')} 的条件引用不存在的节点 '{ref_node_id}'"
                    )

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
    }
