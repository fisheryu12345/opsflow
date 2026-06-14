"""pipeline 构建 - 节点元素创建

Bamboo-engine 原生风格：网关条件直接在创建时指定，NodeOutput 直接注册到 Data。
"""
from collections import deque

from bamboo_engine.builder import (
    Var, Data, ServiceActivity,
    EmptyStartEvent,
    SubProcess,
)
from bamboo_engine.builder.flow.data import NodeOutput

from opsflow.core.variable_resolver import get_global_vars_values
from opsflow.core.pipeline_builder.validation import _detect_circular_ref
from opsflow.plugins.registry import get_plugin
from opsflow.core.bamboo_validator import _EXPR_PATTERN, _VAR_REF_PATTERN


def _find_predecessor_activity(gateway_id: str, in_edges: dict, gateway_ids: set) -> str | None:
    """BFS 回溯网关的前驱，找到第一个非网关节点 ID"""
    visited = {gateway_id}
    q = deque(in_edges.get(gateway_id, []))
    while q:
        nid = q.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        if nid not in gateway_ids:
            return nid
        for pred in in_edges.get(nid, []):
            if pred not in visited:
                q.append(pred)
    return None


def _register_node_output(data: Data, var_name: str, source_act: str, source_key: str):
    """向 data.inputs 注册 NodeOutput（幂等：已存在则不重复注册）"""
    ctx_key = f"${{{var_name}}}"
    if ctx_key not in data.inputs:
        data.inputs[ctx_key] = NodeOutput(
            type=Var.SPLICE,
            source_act=source_act,
            source_key=source_key,
        )


def _collect_condition_refs(expr: str, data: Data, known_node_ids: set) -> str:
    """解析条件表达式中的 ${node_id.key} 引用，注册到 data.inputs 并返回重写表达式

    在 ${} 内部将 node_id.key 替换为扁平 var_name，保持外层 ${} 不变。
    如: "${node_7.test1} >= 5" → "${_gwcond_node_7_test1} >= 5"
    """
    def _rewrite(m):
        inner = m.group(1).strip()
        # 在 ${} 内部查找 node_id.key 模式
        rewritten_inner = _VAR_REF_PATTERN.sub(
            lambda rm: _register_and_return(rm.group(1), rm.group(2)),
            inner,
        )
        return f"${{{rewritten_inner}}}"

    def _register_and_return(node_id, key):
        if node_id in known_node_ids:
            var_name = f"_gwcond_{node_id}_{key}"
            _register_node_output(data, var_name, node_id, key)
            return var_name
        return f"{node_id}.{key}"

    return _EXPR_PATTERN.sub(_rewrite, expr)


def _register_result_var(data: Data, node_id: str, label: str) -> str:
    """注册 _result_{node_id} 的 NodeOutput，返回 ${_result_{node_id}} == True/False"""
    var_name = f"_result_{node_id}"
    _register_node_output(data, var_name, node_id, '_result')
    if label == 'success':
        return f"${{{var_name}}} == True"
    else:
        return f"${{{var_name}}} == False"


def _create_element(node: dict, outgoing_edges: list, *,
                     effective_nodes: list = None, in_edges: dict = None,
                     data: Data = None, execution_id: int = None) -> object:
    """根据 node_type 创建对应的 builder 元素

    NodeOutput 引用直接注册到 data.inputs，不再通过中间变量传递。
    """
    nid = node['id']
    node_type = node.get('node_type', '')
    gateway_types = {'exclusive_gateway', 'parallel_gateway', 'conditional_parallel_gateway', 'converge_gateway'}
    all_nodes = effective_nodes or []
    all_node_ids = {n['id'] for n in all_nodes}
    gateway_ids = {n['id'] for n in all_nodes if n.get('node_type') in gateway_types}
    _in_edges = in_edges or {}

    # ── ExclusiveGateway ──
    if node_type == 'exclusive_gateway':
        from bamboo_engine.builder import ExclusiveGateway
        gw = ExclusiveGateway(id=nid)
        gw.name = nid
        for i, edge in enumerate(outgoing_edges):
            label = edge.get('label', '')
            condition = (edge.get('condition') or '').strip()
            if condition:
                if data:
                    rewritten = _collect_condition_refs(condition, data, all_node_ids)
                    gw.add_condition(i, rewritten)
                else:
                    gw.add_condition(i, condition)  # pass through (unit test)
            elif label in ('success', 'failure'):
                if data:
                    pred = _find_predecessor_activity(nid, _in_edges, gateway_ids) if _in_edges else None
                    expr = _register_result_var(data, pred or nid, label)
                else:
                    expr = '${_result} == True' if label == 'success' else '${_result} == False'
                gw.add_condition(i, expr)
        return gw

    # ── ParallelGateway ──
    if node_type == 'parallel_gateway':
        from bamboo_engine.builder import ParallelGateway
        gw = ParallelGateway(id=nid)
        gw.name = nid
        return gw

    # ── ConditionalParallelGateway ──
    if node_type == 'conditional_parallel_gateway':
        from bamboo_engine.builder import ConditionalParallelGateway
        cpg = ConditionalParallelGateway(id=nid)
        cpg.name = nid
        for i, edge in enumerate(outgoing_edges):
            label = edge.get('label', '')
            condition = (edge.get('condition') or '').strip()
            if condition:
                if data:
                    rewritten = _collect_condition_refs(condition, data, all_node_ids)
                    cpg.add_condition(i, rewritten)
                else:
                    cpg.add_condition(i, condition)
            elif label in ('success', 'failure'):
                if data:
                    pred = _find_predecessor_activity(nid, _in_edges, gateway_ids) if _in_edges else None
                    expr = _register_result_var(data, pred or nid, label)
                else:
                    expr = '${_result} == True' if label == 'success' else '${_result} == False'
                cpg.add_condition(i, expr)
        return cpg

    # ── ConvergeGateway ──
    if node_type == 'converge_gateway':
        from bamboo_engine.builder import ConvergeGateway
        gw = ConvergeGateway(id=nid)
        gw.name = nid
        return gw

    # ── Approval ──
    if node_type == 'approval':
        act = ServiceActivity(component_code="opsflow_plugin", skippable=False, retryable=False, id=nid)
        act.name = nid
        act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='approval')
        act.component.inputs['_approvers'] = Var(type=Var.PLAIN, value=node.get('params', {}).get('approvers', []))
        act.component.inputs['_approval_timeout'] = Var(type=Var.PLAIN, value=node.get('params', {}).get('timeout', 86400))
        return act

    # ── SubProcess ──
    if node_type == 'subprocess':
        target_id = node.get('params', {}).get('target_template_id')
        independent = node.get('params', {}).get('independent', False)
        if not target_id:
            raise ValueError(f"SubProcess 节点 {nid} 缺少 target_template_id")
        if independent:
            act = ServiceActivity(component_code="opsflow_plugin", skippable=True, retryable=True, id=nid)
            act.name = nid
            act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value='subprocess_independent')
            act.component.inputs['_target_template_id'] = Var(type=Var.PLAIN, value=target_id)
            act.component.inputs['_variable_mapping'] = Var(type=Var.PLAIN, value=node.get('params', {}).get('variable_mapping', []))
            act.component.inputs['_output_mapping'] = Var(type=Var.PLAIN, value=node.get('params', {}).get('output_mapping', []))
            return act
        from opsflow.models import FlowTemplate
        try:
            target = FlowTemplate.objects.get(id=target_id)
        except FlowTemplate.DoesNotExist:
            raise ValueError(f"SubProcess 节点 {nid} 引用了不存在的模板 {target_id}")
        _detect_circular_ref(target)
        frozen_snapshot = target.snapshot or {}
        child_vars = get_global_vars_values(frozen_snapshot.get('global_vars', target.global_vars or {}))
        variable_mapping = node.get('params', {}).get('variable_mapping', {})
        output_mapping = node.get('params', {}).get('output_mapping', {})
        child_start = EmptyStartEvent()
        child_inputs = {}
        for k, v in child_vars.items():
            child_inputs[f'${{{k}}}'] = Var(type=Var.PLAIN, value=v)
        child_data = Data(inputs=child_inputs)
        sp = SubProcess(start=child_start, data=child_data, params=variable_mapping,
                        global_outputs=output_mapping, id=nid)
        sp.name = nid
        return sp

    # ── 默认：ServiceActivity 原子插件 ──
    atom_type = node.get('atom_type', '')
    plugin_version = node.get('_plugin_version', '')
    node_max_retries = node.get('max_retries') or node.get('params', {}).get('max_retries', 0)
    node_retry_delay = node.get('retry_delay') or node.get('params', {}).get('retry_delay', 0)
    plugin_cls = get_plugin(atom_type) if atom_type else None
    var_types = plugin_cls.get_var_types() if plugin_cls and hasattr(plugin_cls, 'get_var_types') else {}

    act = ServiceActivity(component_code="opsflow_plugin", skippable=True,
                          retryable=True if node_max_retries > 0 else False,
                          timeout=node.get('timeout_seconds', 60), id=nid)
    act.name = nid
    act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value=atom_type)
    act.component.inputs['_plugin_version'] = Var(type=Var.PLAIN, value=plugin_version)
    act.component.inputs['_max_retries'] = Var(type=Var.PLAIN, value=node_max_retries)
    act.component.inputs['_retry_delay'] = Var(type=Var.PLAIN, value=node_retry_delay)
    if execution_id:
        act.component.inputs['_execution_id'] = Var(type=Var.PLAIN, value=execution_id)
    for k, v in node.get('params', {}).items():
        vtype = var_types.get(k, 'splice')
        if vtype == 'plain':
            act.component.inputs[k] = Var(type=Var.PLAIN, value=v)
        elif isinstance(v, str) and '${' in v:
            act.component.inputs[k] = Var(type=Var.SPLICE, value=v)
        elif vtype == 'split' and isinstance(v, str):
            act.component.inputs[k] = Var(type=Var.SPLICE, value=v)
        elif vtype == 'lazy':
            act.component.inputs[k] = Var(type=Var.PLAIN, value=v)
        else:
            act.component.inputs[k] = Var(type=Var.PLAIN, value=v)

    # 注册 output_schema 字段的 NodeOutput，供条件引擎引用
    if data and plugin_cls and hasattr(plugin_cls, 'get_output_schema'):
        schema = plugin_cls.get_output_schema()
        for field in (schema or []):
            field_key = field.get('name') or field.get('key') or ''
            if field_key:
                _register_node_output(data, f"{nid}_{field_key}", nid, field_key)

    return act
