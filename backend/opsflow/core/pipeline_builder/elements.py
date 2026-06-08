"""pipeline 构建 - 节点元素创建"""
from bamboo_engine.builder import (
    Var, ServiceActivity,
    EmptyStartEvent,
    SubProcess, build_tree,
)
from opsflow.core.variable_resolver import get_global_vars_values
from opsflow.core.pipeline_builder.conditions import _get_condition
from opsflow.core.pipeline_builder.validation import _detect_circular_ref


def _create_element(node: dict, outgoing_edges: list, edge_conditions: dict = None, execution_id: int = None) -> object:
    """根据 node_type 创建对应的 builder 元素"""
    nid = node['id']
    node_type = node.get('node_type', '')
    edge_conditions = edge_conditions or {}

    if node_type == 'exclusive_gateway':
        from bamboo_engine.builder import ExclusiveGateway
        gw = ExclusiveGateway(id=nid)
        gw.name = nid
        for i, edge in enumerate(outgoing_edges):
            cond = _get_condition(edge_conditions, nid, edge['to'], edge.get('label', ''))
            gw.add_condition(i, cond)
        return gw

    if node_type == 'parallel_gateway':
        from bamboo_engine.builder import ParallelGateway
        gw = ParallelGateway(id=nid)
        gw.name = nid
        return gw

    if node_type == 'conditional_parallel_gateway':
        from bamboo_engine.builder import ConditionalParallelGateway
        cpg = ConditionalParallelGateway(id=nid)
        cpg.name = nid
        for i, edge in enumerate(outgoing_edges):
            cond = _get_condition(edge_conditions, nid, edge['to'], edge.get('label', ''))
            cpg.add_condition(i, cond)
        return cpg

    if node_type == 'converge_gateway':
        from bamboo_engine.builder import ConvergeGateway
        gw = ConvergeGateway(id=nid)
        gw.name = nid
        return gw

    if node_type == 'approval':
        act = ServiceActivity(
            component_code="opsflow_plugin",
            skippable=False,
            retryable=False,
            id=nid,
        )
        act.name = nid
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
        target_id = node.get('params', {}).get('target_template_id')
        independent = node.get('params', {}).get('independent', False)

        if not target_id:
            raise ValueError(f"SubProcess 节点 {nid} 缺少 target_template_id")

        if independent:
            act = ServiceActivity(
                component_code="opsflow_plugin",
                skippable=True,
                retryable=True,
                id=nid,
            )
            act.name = nid
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

        # Embedded 模式
        from opsflow.models import FlowTemplate
        try:
            target = FlowTemplate.objects.get(id=target_id)
        except FlowTemplate.DoesNotExist:
            raise ValueError(f"SubProcess 节点 {nid} 引用了不存在的模板 {target_id}")

        _detect_circular_ref(target)

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

        sp = SubProcess(
            start=child_start,
            data=child_data,
            params=variable_mapping,
            global_outputs=output_mapping,
            id=nid,
        )
        sp.name = nid
        return sp

    # 默认：ServiceActivity 原子
    atom_type = node.get('atom_type', '')
    plugin_version = node.get('_plugin_version', '')
    node_max_retries = node.get('max_retries') or node.get('params', {}).get('max_retries', 0)
    node_retry_delay = node.get('retry_delay') or node.get('params', {}).get('retry_delay', 0)
    act = ServiceActivity(
        component_code="opsflow_plugin",
        skippable=True,
        retryable=True if node_max_retries > 0 else False,
        timeout=node.get('timeout_seconds', 60),
        id=nid,
    )
    act.name = nid
    act.component.inputs['_atom_type'] = Var(type=Var.PLAIN, value=atom_type)
    act.component.inputs['_plugin_version'] = Var(type=Var.PLAIN, value=plugin_version)
    act.component.inputs['_max_retries'] = Var(type=Var.PLAIN, value=node_max_retries)
    act.component.inputs['_retry_delay'] = Var(type=Var.PLAIN, value=node_retry_delay)
    if execution_id:
        act.component.inputs['_execution_id'] = Var(type=Var.PLAIN, value=execution_id)
    for k, v in node.get('params', {}).items():
        act.component.inputs[k] = Var(type=Var.PLAIN, value=v)
    return act
