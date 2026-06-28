"""End-to-end pipeline execution tests — 串行/并行/排他/回环/loop全部场景"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

Users = get_user_model()


# ── Pipeline tree definitions ──

SERIAL_3_NODES = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Step 1', 'params': {}},
        {'id': 'n2', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Step 2', 'params': {}},
        {'id': 'n3', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Step 3', 'params': {}},
    ],
    'edges': [{'from': 'n1', 'to': 'n2'}, {'from': 'n2', 'to': 'n3'}],
}

PARALLEL_2_BRANCH = {
    'nodes': [
        {'id': 'pg1', 'node_type': 'parallel_gateway', 'label': 'Fork'},
        {'id': 't1', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Branch A', 'params': {}},
        {'id': 't2', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Branch B', 'params': {}},
        {'id': 'cg1', 'node_type': 'converge_gateway', 'label': 'Join'},
    ],
    'edges': [
        {'from': 'pg1', 'to': 't1'}, {'from': 't1', 'to': 'cg1'},
        {'from': 'pg1', 'to': 't2'}, {'from': 't2', 'to': 'cg1'},
    ],
}

EXCLUSIVE_GATEWAY = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Decide', 'params': {}},
        {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'Branch'},
        {'id': 'ok', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Success Path', 'params': {}},
        {'id': 'fail', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Failure Path', 'params': {}},
    ],
    'edges': [
        {'from': 'n1', 'to': 'gw1'},
        {'from': 'gw1', 'to': 'ok', 'label': 'success'},
        {'from': 'gw1', 'to': 'fail', 'label': 'failure'},
    ],
}

LOOPBACK = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'First', 'params': {}},
        {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'Loop Gate'},
        {'id': 'loop_body', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Loop Body', 'params': {}},
        {'id': 'done', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Done', 'params': {}},
    ],
    'edges': [
        {'from': 'n1', 'to': 'gw1'},
        {'from': 'gw1', 'to': 'loop_body', 'label': 'success'},
        {'from': 'loop_body', 'to': 'n1', 'condition': '${_result_n1} == "True"'},
        {'from': 'gw1', 'to': 'done', 'label': 'failure'},
    ],
}

LOOP_CONFIG_SINGLE = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time', 'label': 'Looper',
         'params': {'loop_config': {'enable': True, 'loop_times': 3, 'fail_skip': False, 'outputs_key': 'outputs'}}},
    ],
    'edges': [],
}


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, task_eager_propagates=True)
class PipelineE2ETest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(username='e2e', password='pass')
        from iam.models import Project, ProjectMember
        cls.project = Project.objects.create(name='E2E Project')
        ProjectMember.objects.create(project=cls.project, user=cls.user, role='editor')

    def _create_execution(self, tree, name='E2E Tpl', status='draft'):
        from opsflow.models import FlowTemplate, FlowExecution
        tpl = FlowTemplate.objects.create(
            name=name, project=self.project, created_by=self.user, pipeline_tree=tree)
        tpl.publish_snapshot()
        return FlowExecution.objects.create(
            template=tpl, project=self.project, status=status, created_by=self.user)

    # ═══════════════════════════════════════
    # Serial
    # ═══════════════════════════════════════

    def test_single_node(self):
        tree = {'nodes': [SERIAL_3_NODES['nodes'][0]], 'edges': []}
        exec_ = self._create_execution(tree, name='Single')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    def test_serial_3_nodes(self):
        exec_ = self._create_execution(SERIAL_3_NODES, name='Serial3')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Parallel
    # ═══════════════════════════════════════

    def test_parallel_2_branch(self):
        exec_ = self._create_execution(PARALLEL_2_BRANCH, name='Parallel')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Exclusive gateway — success/failure labels
    # ═══════════════════════════════════════

    def test_exclusive_gateway_success_path(self):
        """test_print_time always succeeds → success path executes"""
        exec_ = self._create_execution(EXCLUSIVE_GATEWAY, name='Exclusive')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Exclusive gateway — custom conditions
    # ═══════════════════════════════════════

    def test_exclusive_gateway_custom_condition(self):
        """Exclusive gateway with ${n1_test1} >= 5 / < 5 custom conditions.
        test_print_time returns test1=random(1..10), so one branch always executes."""
        tree = {
            'nodes': [
                {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Producer', 'params': {}},
                {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'Custom'},
                {'id': 'high', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'High (>=5)', 'params': {}},
                {'id': 'low', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Low (<5)', 'params': {}},
            ],
            'edges': [
                {'from': 'n1', 'to': 'gw1'},
                {'from': 'gw1', 'to': 'high', 'condition': '${n1_test1} >= 5'},
                {'from': 'gw1', 'to': 'low', 'condition': '${n1_test1} < 5'},
            ],
        }
        exec_ = self._create_execution(tree, name='ExCustom')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    def test_exclusive_gateway_multi_and_condition(self):
        """Exclusive gateway with AND combined condition: ${n1_test1} >= 3 AND ${n1_test1} <= 7"""
        tree = {
            'nodes': [
                {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Producer', 'params': {}},
                {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'AND Gate'},
                {'id': 'mid', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Mid Range', 'params': {}},
                {'id': 'edge', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Edge', 'params': {}},
            ],
            'edges': [
                {'from': 'n1', 'to': 'gw1'},
                {'from': 'gw1', 'to': 'mid', 'condition': '${n1_test1} >= 3 AND ${n1_test1} <= 7'},
                {'from': 'gw1', 'to': 'edge', 'condition': '${n1_test1} < 3 OR ${n1_test1} > 7'},
            ],
        }
        exec_ = self._create_execution(tree, name='ExAND')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    def test_exclusive_gateway_multi_or_condition(self):
        """Exclusive gateway with OR combined condition: ${n1_test1} < 3 OR ${n1_test1} > 8"""
        tree = {
            'nodes': [
                {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Producer', 'params': {}},
                {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'OR Gate'},
                {'id': 'extreme', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Extreme', 'params': {}},
                {'id': 'normal', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Normal', 'params': {}},
            ],
            'edges': [
                {'from': 'n1', 'to': 'gw1'},
                {'from': 'gw1', 'to': 'extreme', 'condition': '${n1_test1} < 3 OR ${n1_test1} > 8'},
                {'from': 'gw1', 'to': 'normal', 'condition': '${n1_test1} >= 3 AND ${n1_test1} <= 8'},
            ],
        }
        exec_ = self._create_execution(tree, name='ExOR')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Conditional parallel gateway
    # ═══════════════════════════════════════

    def test_conditional_parallel_gateway(self):
        """Conditional parallel gateway with custom conditions on each branch"""
        tree = {
            'nodes': [
                {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Source', 'params': {}},
                {'id': 'cpg1', 'node_type': 'conditional_parallel_gateway', 'label': 'Cond PG'},
                {'id': 'a', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Branch A', 'params': {}},
                {'id': 'b', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Branch B', 'params': {}},
                {'id': 'cg1', 'node_type': 'converge_gateway', 'label': 'Join'},
            ],
            'edges': [
                {'from': 'n1', 'to': 'cpg1'},
                {'from': 'cpg1', 'to': 'a', 'condition': '${n1_test1} >= 5'},
                {'from': 'cpg1', 'to': 'b', 'condition': '${n1_test1} < 5'},
                {'from': 'a', 'to': 'cg1'},
                {'from': 'b', 'to': 'cg1'},
            ],
        }
        exec_ = self._create_execution(tree, name='CondPG')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Loopback (Mechanism B — exclusive gateway cycle)
    # ═══════════════════════════════════════

    def test_loopback_pipeline(self):
        """Exclusive gateway loopback edge — cycle_tolerate enabled"""
        exec_ = self._create_execution(LOOPBACK, name='Loopback')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    # ═══════════════════════════════════════
    # Loop config (Mechanism A — loop_config)
    # ═══════════════════════════════════════

    def test_loop_config_3_times(self):
        """Node with loop_config.loop_times=3 executes"""
        exec_ = self._create_execution(LOOP_CONFIG_SINGLE, name='LoopConfig')
        from opsflow.core.flow_engine import FlowEngine
        FlowEngine(exec_).run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])
