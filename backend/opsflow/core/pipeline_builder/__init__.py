"""Pipeline Tree 构建器 — 将 FlowTemplate 的自定义 pipeline_tree 转换为 bamboo-engine 可执行格式"""
from collections import deque

from bamboo_engine.builder import (
    Data, Var, ServiceActivity,
    EmptyStartEvent, EmptyEndEvent,
    ExclusiveGateway, ParallelGateway, ConvergeGateway, SubProcess, build_tree,
)
from pipeline.builder.flow.data import NodeOutput

from opsflow.core.variable_resolver import get_global_vars_values
from opsflow.core.pipeline_builder.conditions import _parse_edge_conditions, _get_condition
from opsflow.core.pipeline_builder.elements import _create_element
from opsflow.core.pipeline_builder.validation import _detect_circular_ref


def _get_node_type(nodes: list) -> str:
    """从节点列表中获取第一个匹配节点的 node_type"""
    return nodes[0].get('node_type', '') if nodes else ''


def build_bamboo_pipeline(flow_template, pipeline_tree=None, target_hosts=None,
                          global_vars=None, execution_id=None, excluded_nodes=None):
    """将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict"""
    tree = pipeline_tree if pipeline_tree is not None else flow_template.pipeline_tree
    nodes = tree.get('nodes', []) or []
    edges = tree.get('edges', []) or []

    # 过滤排除的节点（执行方案）
    excluded = set(excluded_nodes or [])
    if excluded and nodes:
        original_count = len(nodes)
        nodes = [n for n in nodes if n.get('id') not in excluded]
        edges = [e for e in edges if e.get('from') not in excluded and e.get('to') not in excluded]
        if len(nodes) < original_count:
            import logging
            logger = logging.getLogger(__name__)
            logger.info("[ExcludedNodes] 过滤了 %d 个节点（%s），剩余 %d 个",
                        original_count - len(nodes), excluded, len(nodes))

    if not nodes:
        return _empty_pipeline(flow_template, target_hosts=target_hosts, global_vars=global_vars)

    # 过滤视觉节点
    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]

    if not effective_nodes:
        return _empty_pipeline(flow_template)

    # 扫描边条件
    edge_conditions, auto_vars = _parse_edge_conditions(effective_edges)

    # 构建邻接表
    out_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    in_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    for e in effective_edges:
        out_edges.setdefault(e['from'], []).append(e)
        in_edges.setdefault(e['to'], []).append(e)

    # 1. 创建所有元素
    elem_map: dict[str, object] = {}
    for node in effective_nodes:
        nid = node['id']
        elem = _create_element(node, out_edges.get(nid, []), edge_conditions)
        elem_map[nid] = elem

    # 2. 创建 start / end
    start = EmptyStartEvent()
    end_elem = EmptyEndEvent()

    # 3. 拓扑排序
    in_deg = {nid: len(in_edges.get(nid, [])) for nid in elem_map}
    queue = [nid for nid in elem_map if in_deg[nid] == 0]

    if len(queue) == 1:
        start.extend(elem_map[queue[0]])
    elif len(queue) > 1:
        pg = ParallelGateway()
        start.extend(pg)
        for rid in queue:
            pg.connect(elem_map[rid])

    # 4. 按拓扑序连接节点
    processed = set()
    while queue:
        nid = queue.pop(0)
        if nid in processed:
            continue
        processed.add(nid)

        successors = out_edges.get(nid, [])
        elem = elem_map[nid]

        if not successors:
            elem.connect(end_elem)
        elif len(successors) == 1:
            elem.connect(elem_map[successors[0]['to']])
        else:
            node_type = _get_node_type([n for n in effective_nodes if n['id'] == nid])
            if node_type in ('exclusive_gateway', 'parallel_gateway', 'conditional_parallel_gateway', 'converge_gateway'):
                for s in successors:
                    elem.connect(elem_map[s['to']])
            else:
                labels = {s.get('label', '') for s in successors}
                has_success = 'success' in labels
                has_failure = 'failure' in labels
                if has_success and has_failure and labels <= {'success', 'failure'}:
                    gw = ExclusiveGateway()
                    for i, s in enumerate(successors):
                        cond = _get_condition(edge_conditions, nid, s['to'], s.get('label', ''))
                        gw.add_condition(i, cond)
                    elem.extend(gw)
                    for s in successors:
                        gw.connect(elem_map[s['to']])
                else:
                    pg = ParallelGateway()
                    elem.extend(pg)
                    for s in successors:
                        pg.connect(elem_map[s['to']])

        for s in successors:
            target_id = s['to']
            in_deg[target_id] -= 1
            if in_deg[target_id] <= 0 and target_id not in processed:
                queue.append(target_id)

    # 5. 并行网关 → 汇聚网关配对
    def _find_converge(gw_id: str):
        visited = {gw_id}
        q = deque()
        for e in out_edges.get(gw_id, []):
            q.append(e['to'])
        while q:
            nid = q.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            node = next((n for n in effective_nodes if n['id'] == nid), None)
            if not node:
                continue
            if node.get('node_type') == 'converge_gateway':
                return nid
            for e in out_edges.get(nid, []):
                if e['to'] not in visited:
                    q.append(e['to'])
        return None

    for node in effective_nodes:
        nt = node.get('node_type', '')
        if nt in ('parallel_gateway', 'conditional_parallel_gateway'):
            pg_elem = elem_map[node['id']]
            already_converged = True
            for out_elem in pg_elem.outgoing:
                walker = out_elem
                while len(walker.outgoing) > 0:
                    walker = walker.outgoing[0]
                if walker.id != end_elem.id:
                    already_converged = False
                    break
            if not already_converged:
                cg_id = _find_converge(node['id'])
                if cg_id and cg_id in elem_map:
                    pg_elem.converge(elem_map[cg_id])

    # 6. 构建 data
    hosts = target_hosts if target_hosts is not None else (flow_template.target_hosts or [])
    raw_vars = global_vars if global_vars is not None else (flow_template.global_vars or {})
    vars_ = get_global_vars_values(raw_vars)
    if flow_template.project_id:
        from opsflow.core.variable_resolver import resolve_project_variables
        project_env = resolve_project_variables(flow_template.project_id)
        vars_ = {**project_env, **vars_}
    input_map = {
        'target_hosts': Var(type=Var.PLAIN, value=hosts),
        'global_vars': Var(type=Var.PLAIN, value=vars_),
    }
    if execution_id:
        input_map['_execution_id'] = Var(type=Var.PLAIN, value=execution_id)
    data = Data(inputs=input_map)
    for var_name, spec in auto_vars.items():
        data.inputs[var_name] = NodeOutput(
            type=Var.SPLICE,
            source_act=spec['source_act'],
            source_key=spec['source_key'],
        )

    tree = build_tree(start, data=data)

    # 节点超时配置
    timeout_configs = {}
    for node in effective_nodes:
        timeout_seconds = node.get('timeout_seconds')
        if timeout_seconds and timeout_seconds > 0:
            timeout_configs[node['id']] = {
                "enable": True,
                "action": "forced_fail",
                "seconds": timeout_seconds,
            }
    if timeout_configs:
        try:
            from pipeline.contrib.node_timeout import apply_node_timout_configs
            apply_node_timout_configs(tree, timeout_configs)
        except ImportError:
            pass

    # bamboo UUID → 原始节点 ID 映射
    id_map = {}
    for act_id, act_data in tree.get('activities', {}).items():
        if act_data.get('name'):
            id_map[act_id] = act_data['name']
    for gw_id, gw_data in tree.get('gateways', {}).items():
        if gw_data.get('name'):
            id_map[gw_id] = gw_data['name']

    return tree, id_map


def _empty_pipeline(flow_template, target_hosts=None, global_vars=None):
    """返回空的 pipeline（只有 start → end）"""
    start = EmptyStartEvent()
    end = EmptyEndEvent()
    start.extend(end)
    hosts = target_hosts if target_hosts is not None else (flow_template.target_hosts or [])
    raw_vars = global_vars if global_vars is not None else (flow_template.global_vars or {})
    vars_ = get_global_vars_values(raw_vars)
    if flow_template.project_id:
        from opsflow.core.variable_resolver import resolve_project_variables
        project_env = resolve_project_variables(flow_template.project_id)
        vars_ = {**project_env, **vars_}
    data = Data(inputs={
        'target_hosts': Var(type=Var.PLAIN, value=hosts),
        'global_vars': Var(type=Var.PLAIN, value=vars_),
    })
    return build_tree(start, data=data), {}
