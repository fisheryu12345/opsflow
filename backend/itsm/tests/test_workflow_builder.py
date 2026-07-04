"""ITSMWorkflowBuilder 测试 — 验证 pipeline tree 构建"""
from django.test import TestCase
from itsm.models.workflow import Workflow, WorkflowVersion


def _create_workflow_version(states, transitions):
    wf = Workflow.objects.create(name='test-wf', itsm_type='incident')
    wv = WorkflowVersion.objects.create(
        workflow=wf, version=1,
        states=states, transitions=transitions, fields={},
    )
    return wv


class BuildTreeBasicTests(TestCase):
    """基础节点映射"""

    def test_start_end_only(self):
        """仅 START + END 节点"""
        states = {
            '1': {'id': 1, 'type': 'START', 'name': '开始'},
            '2': {'id': 2, 'type': 'END', 'name': '结束'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2, 'condition': {}, 'condition_type': 'default'},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertIsNotNone(tree)
        self.assertIn('id', tree)
        self.assertIn('activities', tree)
        self.assertEqual(len(element_map), 2)

    def test_approval_flow(self):
        """START → 填单(NORMAL) → 审批(APPROVAL) → END"""
        states = {
            '1': {'id': 1, 'type': 'START', 'name': '开始'},
            '2': {'id': 2, 'type': 'NORMAL', 'name': '填写申请'},
            '3': {'id': 3, 'type': 'APPROVAL', 'name': '主管审批'},
            '4': {'id': 4, 'type': 'END', 'name': '结束'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2, 'condition': {}, 'condition_type': 'default'},
            't2': {'from_state_id': 2, 'to_state_id': 3, 'condition': {}, 'condition_type': 'default'},
            't3': {'from_state_id': 3, 'to_state_id': 4, 'condition': {}, 'condition_type': 'default'},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=42)

        self.assertIsNotNone(tree)
        # Verify all 4 elements are created
        self.assertEqual(len(element_map), 4)
        # Verify ticket_id injection
        activity = element_map.get('2')
        self.assertIsNotNone(activity)
        self.assertEqual(activity.component.inputs['ticket_id'].value, 42)

    def test_sign_node(self):
        """SIGN 节点映射为 ServiceActivity"""
        states = {
            '1': {'id': 1, 'type': 'START', 'name': '开始'},
            '2': {'id': 2, 'type': 'SIGN', 'name': '会签'},
            '3': {'id': 3, 'type': 'END', 'name': '结束'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2, 'condition': {}, 'condition_type': 'default'},
            't2': {'from_state_id': 2, 'to_state_id': 3, 'condition': {}, 'condition_type': 'default'},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertIn('2', element_map)
        sign_el = element_map['2']
        self.assertEqual(sign_el.component.code, 'itsm_sign')

    def test_task_node(self):
        """TASK 节点映射为 skippable=True 的 ServiceActivity"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'TASK', 'name': '自动任务'},
            '3': {'id': 3, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertIn('2', element_map)
        task_el = element_map['2']
        self.assertEqual(task_el.component.code, 'itsm_auto_task')
        # TASK 节点应该 skippable
        self.assertTrue(task_el.skippable)

    def test_conditional_parallel_coverage(self):
        """CONDITIONAL_PARALLEL + COVERAGE 映射为 ConditionalParallelGateway + ConvergeGateway"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'CONDITIONAL_PARALLEL', 'name': '条件分支'},
            '3': {'id': 3, 'type': 'NORMAL', 'name': 'A'},
            '4': {'id': 4, 'type': 'NORMAL', 'name': 'B'},
            '5': {'id': 5, 'type': 'COVERAGE', 'name': '汇聚'},
            '6': {'id': 6, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3, 'condition': {'type': 'default'}},
            't3': {'from_state_id': 2, 'to_state_id': 4, 'condition': {'type': 'default'}},
            't4': {'from_state_id': 3, 'to_state_id': 5},
            't5': {'from_state_id': 4, 'to_state_id': 5},
            't6': {'from_state_id': 5, 'to_state_id': 6},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertEqual(len(element_map), 6)
        # 验证 CONVERGE pairing
        gw = element_map['2']
        self.assertIsNotNone(gw)
        self.assertTrue(hasattr(gw, 'converge'))

    def test_exclusive_gateway(self):
        """EXCLUSIVE 网关 — 2 条条件边 + 默认边"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'EXCLUSIVE', 'name': '判断'},
            '3': {'id': 3, 'type': 'NORMAL', 'name': 'A'},
            '4': {'id': 4, 'type': 'NORMAL', 'name': 'B'},
            '5': {'id': 5, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3, 'condition': {'evaluate': '${_result} == True'}},
            't3': {'from_state_id': 2, 'to_state_id': 4, 'condition': {}, 'condition_type': 'default'},
            't4': {'from_state_id': 4, 'to_state_id': 5},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertEqual(len(element_map), 5)
        from bamboo_engine.builder import ExclusiveGateway
        self.assertIsInstance(element_map['2'], ExclusiveGateway)

    def test_parallel_gateway(self):
        """PARALLEL 网关 — 2 分支 + COVERAGE"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'PARALLEL', 'name': '并行'},
            '3': {'id': 3, 'type': 'NORMAL', 'name': 'A'},
            '4': {'id': 4, 'type': 'NORMAL', 'name': 'B'},
            '5': {'id': 5, 'type': 'COVERAGE', 'name': '汇聚'},
            '6': {'id': 6, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3},
            't3': {'from_state_id': 2, 'to_state_id': 4},
            't4': {'from_state_id': 3, 'to_state_id': 5},
            't5': {'from_state_id': 4, 'to_state_id': 5},
            't6': {'from_state_id': 5, 'to_state_id': 6},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertEqual(len(element_map), 6)
        from bamboo_engine.builder import ParallelGateway
        self.assertIsInstance(element_map['2'], ParallelGateway)

    def test_by_field_condition(self):
        """by_field 条件类型 — 结构化条件转为表达式"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'NORMAL', 'name': '填单', 'fields': [
                {'key': 'amount', 'name': '金额', 'type': 'INT'},
            ]},
            '3': {'id': 3, 'type': 'EXCLUSIVE', 'name': '判断'},
            '4': {'id': 4, 'type': 'NORMAL', 'name': '大额'},
            '5': {'id': 5, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {
                'from_state_id': 2, 'to_state_id': 3,
                'condition': {'expressions': [{'key': 'amount', 'condition': '>', 'value': 1000}], 'type': 'and'},
                'condition_type': 'by_field',
            },
            't3': {'from_state_id': 2, 'to_state_id': 4, 'condition': {}, 'condition_type': 'default'},
            't4': {'from_state_id': 4, 'to_state_id': 5},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertEqual(len(element_map), 5)
        # 验证 tree 包含 data.inputs
        self.assertIn('data', tree)
        self.assertIsNotNone(tree['data'])

    def test_converge_pairing(self):
        """PARALLEL 和 CONDITIONAL_PARALLEL 自动配对下游 COVERAGE"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'PARALLEL', 'name': '并行'},
            '3': {'id': 3, 'type': 'NORMAL', 'name': 'A'},
            '4': {'id': 4, 'type': 'NORMAL', 'name': 'B'},
            '5': {'id': 5, 'type': 'COVERAGE', 'name': '汇聚'},
            '6': {'id': 6, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3},
            't3': {'from_state_id': 2, 'to_state_id': 4},
            't4': {'from_state_id': 3, 'to_state_id': 5},
            't5': {'from_state_id': 4, 'to_state_id': 5},
            't6': {'from_state_id': 5, 'to_state_id': 6},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        # 验证网关的 converge 属性已设置
        gw = element_map['2']
        self.assertTrue(hasattr(gw, 'converge'))
        self.assertIsNotNone(gw._converge_gateway_id)

    def test_no_start_end_raises(self):
        """缺少 START 或 END 时报错"""
        states = {
            '1': {'id': 1, 'type': 'NORMAL', 'name': '填单'},
        }
        transitions = {}
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        with self.assertRaises(ValueError) as ctx:
            ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)
        self.assertIn('START', str(ctx.exception))

    def test_default_type(self):
        """未知 type 默认为 fill_form"""
        states = {
            '1': {'id': 1, 'type': 'START'},
            '2': {'id': 2, 'type': 'UNKNOWN_TYPE', 'name': '未知'},
            '3': {'id': 3, 'type': 'END'},
        }
        transitions = {
            't1': {'from_state_id': 1, 'to_state_id': 2},
            't2': {'from_state_id': 2, 'to_state_id': 3},
        }
        wv = _create_workflow_version(states, transitions)

        from itsm.services.workflow_builder import ITSMWorkflowBuilder
        tree, element_map = ITSMWorkflowBuilder.build_tree(wv, ticket_id=1)

        self.assertIn('2', element_map)
        unknown_el = element_map['2']
        self.assertEqual(unknown_el.component.code, 'itsm_fill_form')
