"""Pipeline Tree 构建器 — 将 FlowTemplate 的自定义 pipeline_tree 转换为 bamboo-engine 可执行格式

Bamboo-engine 原生风格：Data 提前构建，元素创建时直接注册 NodeOutput 引用。
"""
from collections import deque

from bamboo_engine.builder import (
    Data, Var, ServiceActivity,
    EmptyStartEvent, EmptyEndEvent,
    ExclusiveGateway, ParallelGateway, ConvergeGateway, SubProcess, build_tree,
)
from bamboo_engine.builder.flow.data import NodeOutput

from opsflow.core.variable_resolver import get_global_vars_values, resolve_project_variables
from opsflow.core.pipeline_builder.elements import _create_element
from opsflow.core.pipeline_builder.validation import _detect_circular_ref


import logging

logger = logging.getLogger(__name__)


def _empty_pipeline(flow_template, global_vars=None):
    """返回空的 pipeline（只有 start → end）- 保持向后兼容"""
    data = _build_data_inputs(flow_template, global_vars)
    start = EmptyStartEvent()
    end = EmptyEndEvent()
    start.extend(end)
    return build_tree(start, data=data)


def _get_node_type(nodes: list, nid: str) -> str:
    return next((n.get('node_type', '') for n in nodes if n['id'] == nid), '')


def _filter_nodes_and_edges(tree, excluded_nodes):
    nodes = tree.get('nodes', []) or []
    edges = tree.get('edges', []) or []
    excluded = set(excluded_nodes or [])
    if excluded and nodes:
        original_count = len(nodes)
        nodes = [n for n in nodes if n.get('id') not in excluded]
        edges = [e for e in edges if e.get('from') not in excluded and e.get('to') not in excluded]
        if len(nodes) < original_count:
            logger.info("[ExcludedNodes] 过滤了 %d 个节点（%s），剩余 %d 个",
                        original_count - len(nodes), excluded, len(nodes))
    visual_start_id = next((n['id'] for n in nodes if n.get('node_type') == 'start_event'), None)
    visual_end_id = next((n['id'] for n in nodes if n.get('node_type') == 'end_event'), None)
    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]
    return effective_nodes, effective_edges, visual_start_id, visual_end_id


def _build_adjacency_lists(effective_nodes, effective_edges):
    out_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    in_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    for e in effective_edges:
        out_edges.setdefault(e['from'], []).append(e)
        in_edges.setdefault(e['to'], []).append(e)
    return out_edges, in_edges


def _create_all_elements(effective_nodes, out_edges, in_edges, data, execution_id=None):
    """创建所有 bamboo-engine 元素，NodeOutput 直接注册到 data.inputs"""
    elem_map: dict[str, object] = {}
    for node in effective_nodes:
        nid = node['id']
        elem = _create_element(
            node, out_edges.get(nid, []),
            effective_nodes=effective_nodes, in_edges=in_edges,
            data=data, execution_id=execution_id,
        )
        elem_map[nid] = elem
    return elem_map


def _register_auto_result(data: Data, node_id: str, label: str) -> str:
    """为非网关节点的 success/failure 标签注册 NodeOutput 并返回条件表达式"""
    var_name = f"_result_{node_id}"
    ctx_key = f"${{{var_name}}}"
    if ctx_key not in data.inputs:
        data.inputs[ctx_key] = NodeOutput(
            type=Var.SPLICE, source_act=node_id, source_key='_result',
        )
    if label == 'success':
        return f"${{{var_name}}} == True"
    else:
        return f"${{{var_name}}} == False"


def _topological_connect(start, end_elem, elem_map, out_edges, in_edges, effective_nodes, data):
    """按拓扑序连接所有节点，自动创建隐式 ExclusiveGateway + 注册 NodeOutput"""
    _synth_counter = [0]

    def _auto_id():
        _synth_counter[0] += 1
        return _synth_counter[0]

    gateway_ids = {n['id'] for n in effective_nodes if n.get('node_type') == 'exclusive_gateway'}

    # Detect gateway loopback edges: gw->target where BFS from target can reach gw
    adj_all = {nid: [e['to'] for e in out_edges.get(nid, [])] for nid in elem_map}
    loopback_targets = set()
    for src_id in gateway_ids:
        for e in out_edges.get(src_id, []):
            visited = {e['to']}
            q = [e['to']]
            while q:
                n = q.pop(0)
                if n == e['from']:
                    loopback_targets.add(e['to'])
                    break
                for nb in adj_all.get(n, []):
                    if nb not in visited:
                        visited.add(nb)
                        q.append(nb)

    # Calculate indegree, excluding loopback edges
    in_deg = {}
    for nid in elem_map:
        incoming = in_edges.get(nid, [])
        filtered = [e for e in incoming
                    if not (e.get('from') in gateway_ids and nid in loopback_targets)]
        in_deg[nid] = len(filtered)
    queue = [nid for nid in elem_map if in_deg[nid] == 0]

    if len(queue) == 1:
        start.extend(elem_map[queue[0]])
    elif len(queue) > 1:
        pg = ParallelGateway(id=f'_auto_root_pg_{_auto_id()}')
        start.extend(pg)
        for rid in queue:
            pg.connect(elem_map[rid])

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
            node_type = _get_node_type(effective_nodes, nid)
            if node_type in ('exclusive_gateway', 'parallel_gateway', 'conditional_parallel_gateway', 'converge_gateway'):
                for s in successors:
                    elem.connect(elem_map[s['to']])
            else:
                labels = {s.get('label', '') for s in successors}
                if labels == {'success', 'failure'}:
                    gw = ExclusiveGateway(id=f'_auto_gw_{nid}_{_auto_id()}')
                    for i, s in enumerate(successors):
                        cond = _register_auto_result(data, nid, s.get('label', ''))
                        gw.add_condition(i, cond)
                    elem.extend(gw)
                    for s in successors:
                        gw.connect(elem_map[s['to']])
                else:
                    pg = ParallelGateway(id=f'_auto_split_pg_{nid}_{_auto_id()}')
                    elem.extend(pg)
                    for s in successors:
                        pg.connect(elem_map[s['to']])

        for s in successors:
            target_id = s['to']
            # Mechanism B: skip in-degree decrement for loopback edges
            nt = nid if nid in gateway_ids else _get_node_type(effective_nodes, nid)
            if nt == 'exclusive_gateway' and target_id in processed:
                continue
            in_deg[target_id] -= 1
            if in_deg[target_id] <= 0 and target_id not in processed:
                queue.append(target_id)


def _find_converge(gw_id, out_edges, effective_nodes):
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


def _pair_converge_gateways(effective_nodes, elem_map, out_edges, end_elem):
    for node in effective_nodes:
        nt = node.get('node_type', '')
        if nt not in ('parallel_gateway', 'conditional_parallel_gateway'):
            continue
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
            cg_id = _find_converge(node['id'], out_edges, effective_nodes)
            if cg_id and cg_id in elem_map:
                pg_elem.converge(elem_map[cg_id])


def _build_data_inputs(flow_template, global_vars=None, execution_id=None):
    """构建 bamboo-engine Data 输入，含 global_vars 展开 + 执行 ID"""
    raw_vars = global_vars if global_vars is not None else (flow_template.global_vars or {})
    vars_ = get_global_vars_values(raw_vars)
    if flow_template.project_id:
        project_env = resolve_project_variables(flow_template.project_id)
        vars_ = {**project_env, **vars_}
    input_map = {}
    for k, v in vars_.items():
        input_map[f'${{{k}}}'] = Var(type=Var.PLAIN, value=v)
    if execution_id:
        input_map['_execution_id'] = Var(type=Var.PLAIN, value=execution_id)
    return Data(inputs=input_map)


def _apply_timeout_configs(tree, effective_nodes):
    timeout_configs = {}
    for node in effective_nodes:
        timeout_seconds = node.get('timeout_seconds')
        if timeout_seconds and timeout_seconds > 0:
            timeout_configs[node['id']] = {
                "enable": True, "action": "forced_fail", "seconds": timeout_seconds,
            }
    if timeout_configs:
        try:
            from pipeline.contrib.node_timeout import apply_node_timout_configs
            apply_node_timout_configs(tree, timeout_configs)
        except ImportError:
            pass


def build_bamboo_pipeline(flow_template, pipeline_tree=None,
                          global_vars=None, execution_id=None, excluded_nodes=None):
    """将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict"""
    tree = pipeline_tree if pipeline_tree is not None else flow_template.pipeline_tree

    effective_nodes, effective_edges, visual_start_id, visual_end_id = \
        _filter_nodes_and_edges(tree, excluded_nodes)

    if not effective_nodes:
        data = _build_data_inputs(flow_template, global_vars, execution_id)
        start = EmptyStartEvent(id=visual_start_id) if visual_start_id else EmptyStartEvent()
        end = EmptyEndEvent(id=visual_end_id) if visual_end_id else EmptyEndEvent()
        start.extend(end)
        return build_tree(start, data=data)

    out_edges, in_edges = _build_adjacency_lists(effective_nodes, effective_edges)
    data = _build_data_inputs(flow_template, global_vars, execution_id)
    elem_map = _create_all_elements(effective_nodes, out_edges, in_edges, data, execution_id)

    start = EmptyStartEvent(id=visual_start_id) if visual_start_id else EmptyStartEvent()
    end_elem = EmptyEndEvent(id=visual_end_id) if visual_end_id else EmptyEndEvent()

    _topological_connect(start, end_elem, elem_map, out_edges, in_edges, effective_nodes, data)
    _pair_converge_gateways(effective_nodes, elem_map, out_edges, end_elem)

    pipeline = build_tree(start, data=data)
    _apply_timeout_configs(pipeline, effective_nodes)

    # -- Mechanism A: inject loop_config into pipeline dict --
    for node in effective_nodes:
        loop_config = node.get('params', {}).get('loop_config', {})
        if loop_config.get('enable'):
            nid = node['id']
            if nid in pipeline.get('activities', {}):
                pipeline['activities'][nid]['loop_config'] = {
                    "enable": True,
                    "loop_times": loop_config.get('loop_times', 1),
                    "fail_skip": loop_config.get('fail_skip', False),
                    "outputs_key": loop_config.get('outputs_key', 'outputs'),
                }

    return pipeline
