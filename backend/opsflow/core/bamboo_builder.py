"""使用 bamboo-engine builder 构建标准 Pipeline Tree

将 FlowTemplate 的自定义 pipeline_tree（节点+边）转换为
bamboo-engine 可执行的 Pipeline Tree dict。

支持节点类型：
  - atom（默认）    → ServiceActivity
  - exclusive_gateway → ExclusiveGateway（条件分支）
  - parallel_gateway  → ParallelGateway（并行分支）
  - converge_gateway  → ConvergeGateway（路径汇聚）
  - start_event / end_event → 视觉标记，不生成管道元素

网关条件增强:
  边支持 condition 字段（如 "${node_1.cpu_usage > 80}"），
  构建期自动解析 ${node_id.key} 引用并注入 NodeOutput 声明，
  运行时 bamboo-engine 自动从源节点 outputs 取值求值。
"""

import re

from bamboo_engine.builder import (
    Data, Var, ServiceActivity,
    EmptyStartEvent, EmptyEndEvent,
    ExclusiveGateway, ParallelGateway, ConditionalParallelGateway, ConvergeGateway,
    SubProcess, build_tree,
)
from pipeline.builder.flow.data import NodeOutput
from opsflow.core.variable_resolver import get_global_vars_values

# 匹配 ${expr} 整体，再从 expr 中解析 node_id.key 引用
_EXPR_PATTERN = re.compile(r'\$\{([^}]*)\}')
_VAR_REF_PATTERN = re.compile(r'([a-zA-Z_]\w*)\.([a-zA-Z_]\w*)')

# 子流程最大嵌套深度
MAX_SUBPROCESS_DEPTH = 5


def _detect_circular_ref(template, visited=None, depth=0):
    """深度优先检测子流程循环引用

    遍历模板中所有 subprocess 节点，递归检测 A→B→A 循环。
    Raises ValueError 如果检测到循环或超过最大深度。
    """
    if depth > MAX_SUBPROCESS_DEPTH:
        raise ValueError(f"子流程嵌套超过最大深度 {MAX_SUBPROCESS_DEPTH}")

    visited = visited or set()
    if template.id in visited:
        raise ValueError(f"循环引用检测: 模板 '{template.name}' (id={template.id}) 已被引用")
    visited.add(template.id)

    pipeline_tree = template.pipeline_tree or {}
    for node in pipeline_tree.get('nodes', []):
        if node.get('node_type') == 'subprocess':
            target_id = node.get('params', {}).get('target_template_id')
            if not target_id:
                continue
            from opsflow.models import FlowTemplate
            try:
                target = FlowTemplate.objects.get(id=target_id)
            except FlowTemplate.DoesNotExist:
                continue
            _detect_circular_ref(target, visited.copy(), depth + 1)


def _parse_edge_conditions(edges: list[dict]) -> tuple[dict[str, str], dict[str, dict]]:
    """扫描边定义中的自定义条件，提取 ${node_id.key} 引用

    将条件中的 ${node_id.key} 重写为自动生成的 var 名（如 _gwcond_node_1_cpu），
    并返回 NodeOutput 声明，供 build_bamboo_pipeline 在步骤 6 注入 Data.inputs。

    支持表达式：
      - "${node_1.cpu_usage > 80}"  → 条件比较
      - "${node_1.a > 0 && node_2.b < 5}"  → 多变量复合表达式
      - "${node_1.job_id}"  → 简单变量引用

    Returns:
        conditions: {"from->to": "rewritten_condition"}
        auto_vars: {"_gwcond_node_1_cpu": {"source_act": "node_1", "source_key": "cpu"}}
    """
    conditions: dict[str, str] = {}
    auto_vars: dict[str, dict] = {}

    def _replace_in_expr(expr: str) -> str:
        """在 expr 内部替换所有 node_id.key → var_name"""
        result = expr
        for m in reversed(list(_VAR_REF_PATTERN.finditer(expr))):
            node_id = m.group(1)
            output_key = m.group(2)
            # 去重
            var_name = None
            for existing_var, spec in auto_vars.items():
                if spec['source_act'] == node_id and spec['source_key'] == output_key:
                    var_name = existing_var
                    break
            if var_name is None:
                var_name = f"_gwcond_{node_id}_{output_key}"
                auto_vars[var_name] = {'source_act': node_id, 'source_key': output_key}
            result = result[:m.start()] + var_name + result[m.end():]
        return result

    def _replace_block(m):
        expr = m.group(1).strip()
        rewritten = _replace_in_expr(expr)
        return f"${{{rewritten}}}"

    for edge in edges:
        cond = (edge.get('condition') or '').strip()
        if not cond:
            continue

        key = f"{edge['from']}->{edge['to']}"
        rewritten = _EXPR_PATTERN.sub(_replace_block, cond)
        conditions[key] = rewritten

    return conditions, auto_vars


def _get_condition(conditions: dict, from_id: str, to_id: str, label: str = "") -> str:
    """获取边的自定义条件，fallback 到基于 label 的默认条件"""
    key = f"{from_id}->{to_id}"
    custom = conditions.get(key)
    if custom:
        return custom
    # 默认行为：基于 label 使用 _result
    if label == 'failure':
        return '${_result == False}'
    return '${_result == True}'


def build_bamboo_pipeline(flow_template, pipeline_tree=None, target_hosts=None,
                          global_vars=None, execution_id=None, excluded_nodes=None):
    """将 FlowTemplate 转换为 bamboo-engine 标准 Pipeline Tree dict

    Args:
        flow_template: FlowTemplate 实例
        pipeline_tree: 可选，冻结的 pipeline_tree，不传则读 flow_template.pipeline_tree
        target_hosts: 可选，冻结的目标主机列表，不传则读 flow_template.target_hosts
        global_vars: 可选，冻结的全局变量，不传则读 flow_template.global_vars
        execution_id: 可选，当前执行 ID，注入到 pipeline inputs 供运行时访问
        excluded_nodes: 可选，排除的节点 ID 列表（执行方案）
    """
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
            logger.info("[ExcludedNodes] 过滤了 %d 个节点（%s），剩余 %d 个", original_count - len(nodes), excluded, len(nodes))

    if not nodes:
        return _empty_pipeline(flow_template, target_hosts=target_hosts, global_vars=global_vars)

    # 过滤视觉节点（开始/结束事件仅用于前端展示）
    effective_nodes = [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')]
    effective_ids = {n['id'] for n in effective_nodes}
    effective_edges = [e for e in edges if e['from'] in effective_ids and e['to'] in effective_ids]

    if not effective_nodes:
        return _empty_pipeline(flow_template)

    # 扫描边条件，提取 ${node_id.key} 引用
    edge_conditions, auto_vars = _parse_edge_conditions(effective_edges)

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
        elem = _create_element(node, out_edges.get(nid, []), edge_conditions)
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
            pg_elem = elem_map[node['id']]
            # 检查 outgoing 是否已连接到汇聚网关（模板已显式定义边的情况）
            # 如果是，跳过 converge() 避免 tail() 死循环
            already_converged = True
            for out_elem in pg_elem.outgoing:
                # 沿着 outgoing[0] 找 tail，看是否已指向汇聚网关
                walker = out_elem
                while len(walker.outgoing) > 0:
                    walker = walker.outgoing[0]
                # 如果 tail 已经是 end_elem，说明路径已完整，无需 converge
                if walker.id != end_elem.id:
                    already_converged = False
                    break
            if not already_converged:
                cg_id = _find_converge(node['id'])
                if cg_id and cg_id in elem_map:
                    pg_elem.converge(elem_map[cg_id])

    # 6. 构建 data — 优先使用冻结值，fallback 到模板当前值
    hosts = target_hosts if target_hosts is not None else (flow_template.target_hosts or [])
    raw_vars = global_vars if global_vars is not None else (flow_template.global_vars or {})
    vars_ = get_global_vars_values(raw_vars)  # 规范化提取纯值
    input_map = {
        'target_hosts': Var(type=Var.PLAIN, value=hosts),
        'global_vars': Var(type=Var.PLAIN, value=vars_),
    }
    if execution_id:
        input_map['_execution_id'] = Var(type=Var.PLAIN, value=execution_id)
    data = Data(inputs=input_map)
    # 注入网关条件引用的节点输出（NodeOutput 自动从源节点 outputs 取值）
    for var_name, spec in auto_vars.items():
        data.inputs[var_name] = NodeOutput(
            type=Var.SPLICE,
            source_act=spec['source_act'],
            source_key=spec['source_key'],
        )

    tree = build_tree(start, data=data)

    # 应用节点超时配置（pipeline.contrib.node_timeout）
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
            pass  # node_timeout contrib 未安装时静默降级

    return tree


def _create_element(node: dict, outgoing_edges: list, edge_conditions: dict = None) -> object:
    """根据 node_type 创建对应的 builder 元素

    Args:
        node: 节点定义
        outgoing_edges: 该节点的出边列表
        edge_conditions: {"from->to": "rewritten_condition"} 自定义条件映射
    """
    nid = node['id']
    node_type = node.get('node_type', '')
    edge_conditions = edge_conditions or {}

    if node_type == 'exclusive_gateway':
        gw = ExclusiveGateway()
        for i, edge in enumerate(outgoing_edges):
            cond = _get_condition(edge_conditions, nid, edge['to'], edge.get('label', ''))
            gw.add_condition(i, cond)
        return gw

    if node_type == 'parallel_gateway':
        return ParallelGateway()

    if node_type == 'conditional_parallel_gateway':
        cpg = ConditionalParallelGateway()
        for i, edge in enumerate(outgoing_edges):
            cond = _get_condition(edge_conditions, nid, edge['to'], edge.get('label', ''))
            cpg.add_condition(i, cond)
        return cpg

    if node_type == 'converge_gateway':
        return ConvergeGateway()

    if node_type == 'approval':
        # 审批节点 — 构建为 ServiceActivity，执行时暂停等待审批
        act = ServiceActivity(
            component_code="opsflow_plugin",
            skippable=False,
            retryable=False,
        )
        act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='approval')
        act.component.inputs['_approvers'] = Var(
            type=Var.PLAIN,
            value=node.get('params', {}).get('approvers', []),
        )
        act.component.inputs['_approval_timeout'] = Var(
            type=Var.PLAIN,
            value=node.get('params', {}).get('timeout', 86400),
        )
        return act

    if node_type == 'subprocess':
        # 子流程节点 — 支持两种模式：
        #   - embedded (默认): SubProcess 元素，bamboo-engine 内部调度
        #   - independent:     ServiceActivity，PluginService 路由到 SubprocessDispatcher
        target_id = node.get('params', {}).get('target_template_id')
        independent = node.get('params', {}).get('independent', False)

        if not target_id:
            raise ValueError(f"SubProcess 节点 {nid} 缺少 target_template_id")

        if independent:
            # 独立模式：创建 ServiceActivity 委托 PluginService 调度
            act = ServiceActivity(
                component_code="opsflow_plugin",
                skippable=True,
                retryable=True,
            )
            act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='subprocess_independent')
            act.component.inputs['_target_template_id'] = Var(type=Var.PLAIN, value=target_id)
            act.component.inputs['_variable_mapping'] = Var(
                type=Var.PLAIN,
                value=node.get('params', {}).get('variable_mapping', []),
            )
            act.component.inputs['_output_mapping'] = Var(
                type=Var.PLAIN,
                value=node.get('params', {}).get('output_mapping', []),
            )
            return act

        # ── Embedded 模式（默认）────────────────────────────────────────
        from opsflow.models import FlowTemplate
        try:
            target = FlowTemplate.objects.get(id=target_id)
        except FlowTemplate.DoesNotExist:
            raise ValueError(f"SubProcess 节点 {nid} 引用了不存在的模板 {target_id}")

        # 循环引用检测
        _detect_circular_ref(target)

        # 使用发布快照（冻结版本），避免草稿变更影响执行
        frozen_snapshot = target.snapshot or {}
        child_tree = frozen_snapshot.get('pipeline_tree', target.pipeline_tree)
        child_hosts = frozen_snapshot.get('target_hosts', target.target_hosts)
        child_vars = get_global_vars_values(frozen_snapshot.get('global_vars', target.global_vars or {}))

        variable_mapping = node.get('params', {}).get('variable_mapping', {})
        output_mapping = node.get('params', {}).get('output_mapping', {})

        child_start = EmptyStartEvent()
        child_data = Data(inputs={
            'target_hosts': Var(type=Var.PLAIN, value=child_hosts),
            'global_vars': Var(type=Var.PLAIN, value=child_vars),
        })

        return SubProcess(
            start=child_start,
            data=child_data,
            params=variable_mapping,
            global_outputs=output_mapping,
        )

    # 默认：ServiceActivity 原子
    atom_type = node.get('atom_type', '')
    plugin_version = node.get('_plugin_version', '')
    node_max_retries = node.get('max_retries') or node.get('params', {}).get('max_retries', 0)
    act = ServiceActivity(
        component_code="opsflow_plugin",
        skippable=True,
        retryable=True if node_max_retries > 0 else False,
        timeout=node.get('timeout_seconds', 60),
    )
    # 插件类型标识（PluginService 由此路由到正确的 BasePlugin）
    act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value=atom_type)
    # 插件版本（多版本路由用）
    act.component.inputs['_plugin_version'] = Var(type=Var.PLAIN, value=plugin_version)
    # 节点级最大重试次数（PluginService 由此读取并在重试时校验）
    act.component.inputs['_max_retries'] = Var(type=Var.PLAIN, value=node_max_retries)
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

    # 校验自定义网关条件中的 ${node_id.key} 引用
    for e in effective_edges:
        cond = e.get('condition', '').strip()
        if not cond:
            continue
        # 解析所有 ${...} 块中的 node_id.key 引用
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


def _empty_pipeline(flow_template, target_hosts=None, global_vars=None):
    start = EmptyStartEvent()
    end = EmptyEndEvent()
    start.extend(end)
    hosts = target_hosts if target_hosts is not None else (flow_template.target_hosts or [])
    raw_vars = global_vars if global_vars is not None else (flow_template.global_vars or {})
    vars_ = get_global_vars_values(raw_vars)
    data = Data(inputs={
        'target_hosts': Var(type=Var.PLAIN, value=hosts),
        'global_vars': Var(type=Var.PLAIN, value=vars_),
    })
    return build_tree(start, data=data)
