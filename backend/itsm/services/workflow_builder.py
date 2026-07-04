# -*- coding: utf-8 -*-
"""ITSMWorkflowBuilder — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树

映射关系:
  START                → EmptyStartEvent
  NORMAL               → ServiceActivity(code=itsm_fill_form)
  APPROVAL             → ServiceActivity(code=itsm_approval)
  SIGN                 → ServiceActivity(code=itsm_sign)
  TASK                 → ServiceActivity(code=itsm_auto_task)
  CONDITIONAL_PARALLEL → ConditionalParallelGateway   # 原 ROUTER_P
  EXCLUSIVE            → ExclusiveGateway              # 新增
  PARALLEL             → ParallelGateway               # 新增
  COVERAGE             → ConvergeGateway
  END                  → EmptyEndEvent
"""

import logging
from collections import deque

logger = logging.getLogger(__name__)


class ITSMWorkflowBuilder:
    """将 ITSM WorkflowVersion 快照转换为 bamboo-engine pipeline tree"""

    @staticmethod
    def build_tree(workflow_version, ticket_id):
        """构建 bamboo-engine pipeline tree

        Args:
            workflow_version: WorkflowVersion instance (含 states / transitions JSON)
            ticket_id: 工单 ID，注入到 ServiceActivity 的 inputs 中

        Returns:
            (tree_dict, element_map): bamboo pipeline tree + 节点元素映射
        """
        from bamboo_engine.builder import (
            Var, Data, ServiceActivity, EmptyStartEvent, EmptyEndEvent,
            ConvergeGateway, ConditionalParallelGateway,
            ExclusiveGateway, ParallelGateway,
            build_tree,
        )
        from bamboo_engine.builder.flow.data import NodeOutput
        from itsm.services.condition_utils import _collect_condition_refs

        states = workflow_version.states
        transitions = workflow_version.transitions

        # Build adjacency and element maps
        element_map = {}
        transition_map = {}  # from_state_id → [(to_state_id, condition_data)]

        for tid, trans in transitions.items():
            from_id = str(trans.get('from_state_id'))
            to_id = str(trans.get('to_state_id'))
            transition_map.setdefault(from_id, []).append({
                'to_id': to_id,
                'condition': trans.get('condition', {}),
                'condition_type': trans.get('condition_type', 'default'),
            })

        # Data 对象 — 承载 NodeOutput 注册，必须传入 build_tree()
        data = Data()
        all_node_ids = set()

        # Create pipeline elements
        for sid, state in states.items():
            sid_str = str(sid)
            stype = state.get('type', 'START')
            all_node_ids.add(sid_str)

            if stype == 'START':
                el = EmptyStartEvent(id=sid_str)
            elif stype == 'END':
                el = EmptyEndEvent(id=sid_str)
            elif stype == 'NORMAL':
                el = ServiceActivity(
                    component_code='itsm_fill_form',
                    id=sid_str,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state)
            elif stype == 'APPROVAL':
                el = ServiceActivity(
                    component_code='itsm_approval',
                    id=sid_str,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state)
            elif stype == 'SIGN':
                el = ServiceActivity(
                    component_code='itsm_sign',
                    id=sid_str,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state)
            elif stype == 'TASK':
                el = ServiceActivity(
                    component_code='itsm_auto_task',
                    id=sid_str,
                    skippable=True,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state)
            elif stype == 'CONDITIONAL_PARALLEL':
                el = ConditionalParallelGateway(id=sid_str)
            elif stype == 'EXCLUSIVE':
                el = ExclusiveGateway(id=sid_str)
            elif stype == 'PARALLEL':
                el = ParallelGateway(id=sid_str)
            elif stype == 'COVERAGE':
                el = ConvergeGateway(id=sid_str)
            else:
                # Unknown type fallback
                el = ServiceActivity(
                    component_code='itsm_fill_form',
                    id=sid_str,
                    skippable=True,
                )
                el.name = state.get('name', '')

            element_map[sid_str] = el

        # Connect elements via transitions
        for from_id, outgoing in transition_map.items():
            from_el = element_map.get(from_id)
            if not from_el:
                continue
            for i, edge in enumerate(outgoing):
                to_el = element_map.get(edge['to_id'])
                if not to_el:
                    continue
                if hasattr(from_el, 'outgoing'):
                    from_el.outgoing.append(to_el)
                    # 网关条件设置
                    if hasattr(from_el, 'add_condition'):
                        cond_type = edge.get('condition_type', 'default')

                        if cond_type == 'by_field':
                            cond = edge.get('condition', {})
                            expr = _build_by_field_expr(cond, from_id)
                            expr = _collect_condition_refs(expr, data, all_node_ids)
                        else:
                            expr = cond.get('evaluate', cond.get('expression', True))
                            if isinstance(expr, str):
                                expr = _collect_condition_refs(expr, data, all_node_ids)

                        from_el.add_condition(i, {'evaluate': expr})

        # ConvergeGateway 配对 — PARALLEL / CONDITIONAL_PARALLEL 需要与下游 COVERAGE 配对
        for sid_str, el in element_map.items():
            stype = states.get(sid_str, {}).get('type', '')
            if stype not in ('PARALLEL', 'CONDITIONAL_PARALLEL'):
                continue
            cg = _find_downstream_converge(sid_str, transition_map, element_map)
            if cg:
                el.converge(cg)

        # Build tree — find start/end by state type
        start_event = None
        end_event = None
        for sid_str, el in element_map.items():
            sdata = states.get(sid_str, {})
            stype = sdata.get('type', '')
            if stype == 'START':
                start_event = el
            elif stype == 'END':
                end_event = el

        if not start_event or not end_event:
            raise ValueError('Workflow must have START and END states')

        tree = build_tree(start_event, data=data)
        return tree, element_map


def _register_field_outputs(data, sid_str, state):
    """注册表单字段为 NodeOutput，供网关条件引用

    字段路径格式: ${sid_str.field_{key}} — _collect_condition_refs 会自动解析
    """
    from bamboo_engine.builder.flow.data import NodeOutput
    from bamboo_engine.builder import Var

    for field in state.get('fields', []):
        field_key = field.get('key', '')
        if field_key:
            var_name = f"{sid_str}_field_{field_key}"
            ctx_key = f"${{{var_name}}}"
            if ctx_key not in data.inputs:
                data.inputs[ctx_key] = NodeOutput(
                    type=Var.SPLICE,
                    source_act=sid_str,
                    source_key=f"field_{field_key}",
                )


def _build_by_field_expr(condition: dict, from_id: str) -> str:
    """将结构化条件转换为 bamboo 条件表达式字符串

    输出示例: "${STATE_1.field_amount} > 1000 and ${STATE_1.field_department} == 'IT'"
    _EXPR_PATTERN 捕获 "STATE_1.field_amount"，
    _VAR_REF_PATTERN 拆分为 node_id=STATE_1, key=field_amount，
    然后自动注册 NodeOutput 到 data.inputs。

    Args:
        condition: 结构化条件，如 {"expressions": [...], "type": "and"}
        from_id: 源节点 ID（表单字段所在节点）
    Returns:
        bamboo 表达式字符串
    """
    expr_type = condition.get('type', 'and')
    exprs = condition.get('expressions', [])
    parts = []
    for e in exprs:
        key = e.get('key', '')
        op = e.get('condition', '==')
        val = e.get('value', '')
        if isinstance(val, str):
            val = f"'{val}'"
        var_ref = f"${{{from_id}.field_{key}}}"
        parts.append(f"{var_ref} {op} {val}")
    joiner = ' and ' if expr_type == 'and' else ' or '
    return joiner.join(parts)


def _find_downstream_converge(gw_id, transition_map, element_map):
    """BFS 从网关出发查找下游第一个 ConvergeGateway"""
    from bamboo_engine.builder import ConvergeGateway

    visited = {gw_id}
    q = deque()
    for edge in transition_map.get(gw_id, []):
        q.append(edge['to_id'])
    while q:
        nid = q.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        el = element_map.get(nid)
        if isinstance(el, ConvergeGateway):
            return el
        for edge in transition_map.get(nid, []):
            if edge['to_id'] not in visited:
                q.append(edge['to_id'])
    return None
