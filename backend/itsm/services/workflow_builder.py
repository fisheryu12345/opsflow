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
import uuid
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
            (tree_dict, element_map, node_id_map): bamboo pipeline tree + 节点元素映射 + 原始 key → element ID 映射
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
            # Use node_key for mapping if available, fall back to state FK IDs
            from_id = str(trans.get('from_node_key') or trans.get('from_state_id'))
            to_id = str(trans.get('to_node_key') or trans.get('to_state_id'))
            transition_map.setdefault(from_id, []).append({
                'to_id': to_id,
                'condition': trans.get('condition', {}),
                'condition_type': trans.get('condition_type', 'default'),
            })

        # Generate unique suffix per run to avoid Data.node_id collisions
        # across different pipeline runs of the same workflow version
        run_salt = uuid.uuid4().hex[:6]

        # Data 对象 — 承载 NodeOutput 注册，必须传入 build_tree()
        data = Data()
        all_node_ids = set()
        node_id_map = {}  # original key → unique element ID


        # Create pipeline elements with unique IDs per run
        for sid, state in states.items():
            sid_str = str(sid)
            stype = state.get('type', 'START')
            # Append unique salt so repeated runs don't collide on Data.node_id
            elem_id = f"{sid_str}_{run_salt}"
            node_id_map[sid_str] = elem_id
            all_node_ids.add(elem_id)
            all_node_ids.add(sid_str)  # condition expressions reference original keys

            if stype == 'START':
                el = EmptyStartEvent(id=elem_id)
            elif stype == 'END':
                el = EmptyEndEvent(id=elem_id)
            elif stype == 'NORMAL':
                el = ServiceActivity(
                    component_code='itsm_fill_form',
                    id=elem_id,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state, node_id_map)
            elif stype == 'APPROVAL':
                el = ServiceActivity(
                    component_code='itsm_approval',
                    id=elem_id,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state, node_id_map)
            elif stype == 'SIGN':
                el = ServiceActivity(
                    component_code='itsm_sign',
                    id=elem_id,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state, node_id_map)
            elif stype == 'TASK':
                el = ServiceActivity(
                    component_code='itsm_auto_task',
                    id=elem_id,
                    skippable=True,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
                _register_field_outputs(data, sid_str, state, node_id_map)
            elif stype == 'CONDITIONAL_PARALLEL':
                el = ConditionalParallelGateway(id=elem_id)
            elif stype == 'EXCLUSIVE':
                el = ExclusiveGateway(id=elem_id)
            elif stype == 'PARALLEL':
                el = ParallelGateway(id=elem_id)
            elif stype == 'COVERAGE':
                el = ConvergeGateway(id=elem_id)
            else:
                # Unknown type fallback
                el = ServiceActivity(
                    component_code='itsm_fill_form',
                    id=elem_id,
                    skippable=True,
                )
                el.name = state.get('name', '')

            element_map[elem_id] = el
            # Also register by original state key for transition lookup
            element_map[sid_str] = el
            # Also register by DB id for transition lookup fallback
            db_id = state.get('id')
            if db_id is not None:
                element_map[str(db_id)] = el


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
                            expr = _collect_condition_refs(expr, data, all_node_ids, node_id_map)
                        else:
                            cond = edge.get('condition', {})
                            if isinstance(cond, str):
                                expr = cond
                            else:
                                expr = cond.get('evaluate', cond.get('expression', True))
                            if isinstance(expr, str):
                                expr = _collect_condition_refs(expr, data, all_node_ids, node_id_map)

                        from_el.add_condition(i, expr)


        # Pair ParallelGateways with their ConvergeGateways (opsflow-style).
        # First check if branches already reach END (transitions already define
        # the converge path). Only call converge() when NOT already_converged,
        # otherwise converge() creates duplicate edges causing infinite tail().
        # Find END element from states for the already_converged check
        end_elem = None
        for sid_str, state in states.items():
            if state.get('type') == 'END':
                end_elem = element_map.get(sid_str)
                break

        # If there's no END node at all, skip converge linking entirely.
        # A workflow without END is invalid and will fail validation later,
        # but we must not hang here trying to tail-walk a cyclic graph.
        if not end_elem:
            pass

        # Build out_edges once for converge BFS
        converge_out_edges: dict = {}
        for t in transitions.values():
            fk = str(t.get('from_node_key') or t.get('from_state_id') or '')
            tk = str(t.get('to_node_key') or t.get('to_state_id') or '')
            converge_out_edges.setdefault(fk, []).append(tk)

        for sid_str, state in states.items():
            el = element_map.get(sid_str)
            if el is None:
                continue
            stype = state.get('type', '')
            if stype not in ('PARALLEL', 'CONDITIONAL_PARALLEL'):
                continue
            if not end_elem:
                continue  # skip if no END node
            # Check if all branches already converge to END (with cycle guard)
            already_converged = True
            for out_elem in el.outgoing:
                walker = out_elem
                walk_visited = set()
                while len(walker.outgoing) > 0:
                    if walker.id in walk_visited:
                        # Cycle detected — graph is invalid, bail out
                        already_converged = False
                        break
                    walker = walker.outgoing[0]
                if not already_converged:
                    break
                if walker.id != end_elem.id:
                    already_converged = False
                    break
            if already_converged:
                continue
            # BFS to find ConvergeGateway
            visited = {sid_str}
            q = [(nid, 0) for nid in converge_out_edges.get(sid_str, [])]
            cg_id = None
            while q:
                nid, depth = q.pop(0)
                if nid in visited or depth > 20:
                    continue
                visited.add(nid)
                next_el = element_map.get(nid)
                if next_el and isinstance(next_el, ConvergeGateway):
                    cg_id = nid
                    break
                q.extend((n, depth + 1) for n in converge_out_edges.get(nid, []))
            if cg_id and cg_id in element_map:
                el.converge(element_map[cg_id])
            else:
                pass

        # Build tree — find start/end by state type
        # IMPORTANT: first match wins. Safety-net START/END (id < 0) may exist
        # alongside real ones; prefer the real one that has outgoing/incoming.
        start_event = None
        end_event = None
        for sid_str in states.keys():
            el = element_map.get(sid_str)
            if el is None:
                continue
            stype = states[sid_str].get('type', '')
            if stype == 'START':
                if start_event is None or (not start_event.outgoing and el.outgoing):
                    start_event = el
            elif stype == 'END':
                if end_event is None:
                    end_event = el

        if not start_event or not end_event:
            raise ValueError('Workflow must have START and END states')

        # Validate every non-END node has at least one outgoing edge
        # Iterate over state keys (original keys), not element_map (which has
        # both unique IDs and original key aliases)
        for sid_str in states.keys():
            el = element_map.get(sid_str)
            if el is None:
                continue
            stype = states[sid_str].get('type', '')
            if stype == 'END':
                continue
            if len(getattr(el, 'outgoing', [])) == 0:
                name = states[sid_str].get('name', sid_str)
                raise ValueError(
                    f"Node '{name}' (type={stype}, id={sid_str}) "
                    f"has no outgoing transitions — check the workflow diagram"
                )

        tree = build_tree(start_event, data=data)
        return tree, element_map, node_id_map


def _register_field_outputs(data, sid_str, state, node_id_map=None):
    """注册表单字段为 NodeOutput，供网关条件引用

    node_id_map: maps original key → salted element ID (for correct source_act)
    """
    from bamboo_engine.builder.flow.data import NodeOutput
    from bamboo_engine.builder import Var

    salted_id = (node_id_map or {}).get(sid_str, sid_str)
    for field in state.get('fields', []):
        field_key = field.get('key', '')
        if field_key:
            var_name = f"{sid_str}_{field_key}"
            ctx_key = f"${{{var_name}}}"
            if ctx_key not in data.inputs:
                data.inputs[ctx_key] = NodeOutput(
                    type=Var.SPLICE,
                    source_act=salted_id,
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


