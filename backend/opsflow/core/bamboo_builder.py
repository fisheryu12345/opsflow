"""使用 bamboo-engine builder 构建标准 Pipeline Tree

将 FlowTemplate 的自定义 pipeline_tree（节点+边）转换为
bamboo-engine 可执行的 Pipeline Tree dict。

支持节点类型：
  - atom（默认）    → ServiceActivity
  - exclusive_gateway → ExclusiveGateway（条件分支）
  - parallel_gateway  → ParallelGateway（并行分支）
  - converge_gateway  → ConvergeGateway（路径汇聚）
  - start_event / end_event → 视觉标记，不生成管道元素
"""

from bamboo_engine.builder import (
    Data, Var, ServiceActivity,
    EmptyStartEvent, EmptyEndEvent,
    ExclusiveGateway, ParallelGateway, ConditionalParallelGateway, ConvergeGateway,
    build_tree,
)
from opsflow.core.atom_registry import get_atom_meta


def build_bamboo_pipeline(flow_template):
    """将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict"""
    pipeline_tree = flow_template.pipeline_tree
    nodes = pipeline_tree.get('nodes', []) or []
    edges = pipeline_tree.get('edges', []) or []

    if not nodes:
        return _empty_pipeline(flow_template)

    # 过滤视觉节点（开始/结束事件仅用于前端展示）
    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]

    if not effective_nodes:
        return _empty_pipeline(flow_template)

    # 构建邻接表
    out_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    in_edges: dict[str, list[dict]] = {n['id']: [] for n in effective_nodes}
    for e in effective_edges:
        out_edges.setdefault(e['from'], []).append(e)
        in_edges.setdefault(e['to'], []).append(e)

    # 1. 创建所有元素（按 node_type 区分）
    elem_map: dict[str, object] = {}
    for node in effective_nodes:
        nid = node['id']
        node_type = node.get('node_type', '')
        elem = _create_element(node, out_edges.get(nid, []))
        elem_map[nid] = elem

    # 2. 创建 start / end
    start = EmptyStartEvent()
    end_elem = EmptyEndEvent()

    # 3. 拓扑排序
    in_deg = {nid: len(in_edges.get(nid, [])) for nid in elem_map}
    queue = [nid for nid in elem_map if in_deg[nid] == 0]

    # 连线：start → root(s)
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
            # 多目标 → 如果节点本身是网关，直接用网关连接
            node_type = _get_node_type([n for n in effective_nodes if n['id'] == nid])
            if node_type in ('exclusive_gateway', 'parallel_gateway', 'conditional_parallel_gateway', 'converge_gateway'):
                for s in successors:
                    elem.connect(elem_map[s['to']])
            else:
                # 原子节点多目标 → 自动插入网关
                labels = {s.get('label', '') for s in successors}
                has_success = 'success' in labels
                has_failure = 'failure' in labels
                if has_success and has_failure and labels <= {'success', 'failure'}:
                    gw = ExclusiveGateway()
                    if has_success:
                        gw.add_condition(0, '${_result == True}')
                    if has_failure:
                        gw.add_condition(1, '${_result == False}')
                    elem.extend(gw)
                    for s in successors:
                        gw.connect(elem_map[s['to']])
                else:
                    pg = ParallelGateway()
                    elem.extend(pg)
                    for s in successors:
                        pg.connect(elem_map[s['to']])

        # 后继节点入队
        for s in successors:
            target_id = s['to']
            in_deg[target_id] -= 1
            if in_deg[target_id] <= 0 and target_id not in processed:
                queue.append(target_id)

    # 5. 建立并行网关 → 汇聚网关配对
    # bamboo-engine 要求 ParallelGateway/ConditionalParallelGateway
    # 必须与 ConvergeGateway 配对，记录汇聚关系
    from collections import deque

    def _find_converge(gw_id: str):
        """BFS 从网关下游查找第一个汇聚网关"""
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
            cg_id = _find_converge(node['id'])
            if cg_id and cg_id in elem_map:
                elem_map[node['id']].converge(elem_map[cg_id])

    # 6. 构建 data
    data = Data(inputs={
        'target_hosts': Var(type=Var.PLAIN, value=flow_template.target_hosts or []),
        'global_vars': Var(type=Var.PLAIN, value=flow_template.global_vars or {}),
    })

    return build_tree(start, data=data)


def _create_element(node: dict, outgoing_edges: list) -> object:
    """根据 node_type 创建对应的 builder 元素"""
    nid = node['id']
    node_type = node.get('node_type', '')

    if node_type == 'exclusive_gateway':
        gw = ExclusiveGateway()
        # 从出边标签设置条件
        labels = sorted({e.get('label', '') for e in outgoing_edges if e.get('label')})
        for i, label in enumerate(labels):
            if label == 'failure':
                gw.add_condition(i, '${_result == False}')
            else:
                gw.add_condition(i, '${_result == True}')
        return gw

    if node_type == 'parallel_gateway':
        return ParallelGateway()

    if node_type == 'conditional_parallel_gateway':
        cpg = ConditionalParallelGateway()
        labels = sorted({e.get('label', '') for e in outgoing_edges if e.get('label')})
        for i, label in enumerate(labels):
            if label == 'failure':
                cpg.add_condition(i, '${_result == False}')
            else:
                cpg.add_condition(i, '${_result == True}')
        return cpg

    if node_type == 'converge_gateway':
        return ConvergeGateway()

    # 默认：ServiceActivity 原子
    act = ServiceActivity(
        component_code=_resolve_component_code(node.get('atom_type', 'shell')),
        skippable=True,
        retryable=True,
        timeout=node.get('timeout_seconds', 60),
    )
    for k, v in node.get('params', {}).items():
        act.component.inputs[k] = Var(type=Var.PLAIN, value=v)
    return act


def _get_node_type(nodes: list) -> str:
    """从节点列表中获取第一个匹配节点的 node_type"""
    return nodes[0].get('node_type', '') if nodes else ''


def validate_bamboo_compatibility(pipeline_tree: dict) -> dict:
    """校验 pipeline_tree 是否能被 bamboo-engine 执行"""
    errors = []
    warnings = []
    nodes = pipeline_tree.get('nodes', []) or []
    edges = pipeline_tree.get('edges', []) or []

    if not nodes:
        return {'valid': True, 'errors': [], 'warnings': ['空流程']}

    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]

    if not effective_nodes:
        return {'valid': True, 'errors': [], 'warnings': ['无有效节点']}

    # 检查节点 ID 唯一性
    ids = [n['id'] for n in effective_nodes]
    if len(ids) != len(set(ids)):
        errors.append('节点 ID 不唯一')

    # 检查边引用
    for e in effective_edges:
        if e.get('from') not in effective_ids:
            errors.append(f"边起始节点 '{e.get('from')}' 不存在")
        if e.get('to') not in effective_ids:
            errors.append(f"边目标节点 '{e.get('to')}' 不存在")

    # 检查环
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
            in_degree[target] -= 1
            if in_degree[target] <= 0:
                queue.append(target)

    if visited != len(effective_nodes):
        errors.append('流程中存在环，bamboo-engine 不支持')

    # 节点出入度合法性校验（bamboo-engine 节点合法性规则）
    # 注意：使用原始 edges（非 effective_edges），因为 start/end 节点
    # 产生的边（start→node、node→end）也计入出入度
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

    # 检查网关出边条件
    for n in effective_nodes:
        node_type = n.get('node_type', '')
        successors = [e for e in effective_edges if e.get('from') == n['id']]
        if node_type in ('exclusive_gateway', 'conditional_parallel_gateway') and len(successors) > 1:
            labels = {e.get('label', '') for e in successors}
            if not labels:
                warnings.append(f"排他网关 '{n.get('label', n['id'])}' 缺少分支标签")
            elif labels - {'success', 'failure'}:
                warnings.append(
                    f"排他网关 '{n.get('label', n['id'])}' 分支标签含非 success/failure 值")

        # 汇聚网关只能有一条出边
        if node_type == 'converge_gateway' and len(successors) > 1:
            warnings.append(f"汇聚网关 '{n.get('label', n['id'])}' 有多条出边，将取第一条")

        # 汇聚网关需有多条入边
        if node_type == 'converge_gateway':
            predecessors = [e for e in effective_edges if e.get('to') == n['id']]
            if len(predecessors) < 2:
                warnings.append(f"汇聚网关 '{n.get('label', n['id'])}' 入边少于 2 条，建议改用直接连接")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
    }


def _resolve_component_code(atom_type: str) -> str:
    meta = get_atom_meta(atom_type)
    if meta and meta.component_code:
        return meta.component_code
    return f"opsflow_{atom_type}"


def _empty_pipeline(flow_template) -> dict:
    start = EmptyStartEvent()
    end = EmptyEndEvent()
    start.extend(end)
    data = Data(inputs={
        'target_hosts': Var(type=Var.PLAIN, value=flow_template.target_hosts or []),
        'global_vars': Var(type=Var.PLAIN, value=flow_template.global_vars or {}),
    })
    return build_tree(start, data=data)
