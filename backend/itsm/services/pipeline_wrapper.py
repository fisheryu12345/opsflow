# -*- coding: utf-8 -*-
"""PipelineWrapper — 将 ITSM Workflow 转换为 bamboo-pipeline 可执行树

使用 bamboo_engine.builder 构建 pipeline tree（与 opsflow 引擎一致）

映射关系:
  START    → EmptyStartEvent
  NORMAL   → ServiceActivity(code=itsm_fill_form)
  APPROVAL → ServiceActivity(code=itsm_approval)
  SIGN     → ServiceActivity(code=itsm_sign)
  TASK     → ServiceActivity(code=itsm_auto_task)
  ROUTER_P → ConditionalParallelGateway
  COVERAGE → ConvergeGateway
  END      → EmptyEndEvent
"""

import logging

logger = logging.getLogger(__name__)


class PipelineWrapper:
    """ITSM 工作流转 pipeline 执行引擎"""

    def __init__(self, workflow_version):
        self.workflow_version = workflow_version
        self.states_data = workflow_version.states
        self.transitions_data = workflow_version.transitions

    def build_tree(self, ticket_id):
        """构建 bamboo-engine pipeline tree"""
        from bamboo_engine.builder import (
            Var, ServiceActivity, EmptyStartEvent, EmptyEndEvent,
            ExclusiveGateway, ConditionalParallelGateway,
            ConvergeGateway, build_tree,
        )

        states = self.states_data
        transitions = self.transitions_data

        # Build adjacency and element maps
        element_map = {}
        transition_map = {}  # from_state_id → [(to_state_id, condition_data)]
        gateway_map = {}  # from_state_id → gateway_type for auto-gateway insertion

        for tid, trans in transitions.items():
            from_id = str(trans.get('from_state_id'))
            to_id = str(trans.get('to_state_id'))
            transition_map.setdefault(from_id, []).append({
                'to_id': to_id,
                'condition': trans.get('condition', {}),
                'condition_type': trans.get('condition_type', 'default'),
            })

        # Create pipeline elements
        for sid, state in states.items():
            sid_str = str(sid)
            stype = state.get('type', 'START')

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
            elif stype == 'APPROVAL':
                el = ServiceActivity(
                    component_code='itsm_approval',
                    id=sid_str,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
            elif stype == 'SIGN':
                el = ServiceActivity(
                    component_code='itsm_sign',
                    id=sid_str,
                    skippable=False,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
            elif stype == 'TASK':
                el = ServiceActivity(
                    component_code='itsm_auto_task',
                    id=sid_str,
                    skippable=True,
                )
                el.name = state.get('name', '')
                el.component.inputs['ticket_id'] = Var(type=Var.PLAIN, value=ticket_id)
                el.component.inputs['state_id'] = Var(type=Var.PLAIN, value=state.get('id'))
            elif stype == 'ROUTER_P':
                el = ConditionalParallelGateway(id=sid_str)
            elif stype == 'COVERAGE':
                el = ConvergeGateway(id=sid_str)
            else:
                # Default to normal activity
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
            for edge in outgoing:
                to_el = element_map.get(edge['to_id'])
                if not to_el:
                    continue
                cond = edge.get('condition', {})
                cond_type = edge.get('condition_type', 'default')
                # Connect elements via incoming/outgoing lists (build_tree handles edges)
                if hasattr(from_el, 'outgoing'):
                    from_el.outgoing.append(to_el)

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

        tree = build_tree(start_event)
        return tree, element_map

    def run_pipeline(self, ticket_id):
        """创建并启动 pipeline"""
        from bamboo_engine import api
        from pipeline.eri.runtime import BambooDjangoRuntime

        tree, _ = self.build_tree(ticket_id)
        # Pipeline tree is a dict with an 'id' field
        pipeline_id = tree.get('id', '')
        runtime = BambooDjangoRuntime()
        result = api.run_pipeline(runtime, tree)
        if not result.result:
            logger.error(f'Pipeline run failed: {result.message}')
            raise RuntimeError(f'Pipeline run failed: {result.message}')
        return pipeline_id, tree

    @staticmethod
    def resume_pipeline(pipeline_id):
        from bamboo_engine import api
        from pipeline.eri.runtime import BambooDjangoRuntime
        runtime = BambooDjangoRuntime()
        return api.resume_pipeline(runtime, pipeline_id).result

    @staticmethod
    def pause_pipeline(pipeline_id):
        from bamboo_engine import api
        from pipeline.eri.runtime import BambooDjangoRuntime
        runtime = BambooDjangoRuntime()
        return api.pause_pipeline(runtime, pipeline_id).result

    @staticmethod
    def revoke_pipeline(pipeline_id):
        from bamboo_engine import api
        from pipeline.eri.runtime import BambooDjangoRuntime
        runtime = BambooDjangoRuntime()
        return api.revoke_pipeline(runtime, pipeline_id).result

    @staticmethod
    def activity_callback(activity_id, callback_data):
        from bamboo_engine import api
        from pipeline.eri.runtime import BambooDjangoRuntime
        runtime = BambooDjangoRuntime()
        return api.activity_callback(runtime, activity_id, callback_data).result
