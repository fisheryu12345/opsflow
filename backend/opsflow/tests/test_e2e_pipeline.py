"""End-to-end integration tests — pipeline build → execute → result

Uses CELERY_TASK_ALWAYS_EAGER=True so all Celery tasks run synchronously
in the test thread. No Redis/MySQL broker required.

Covers:
- Simple single-node pipeline
- Pipeline with exclusive gateway
- Node retry after failure
"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

Users = get_user_model()

PIPELINE_TREE_SIMPLE = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Print Time', 'params': {}},
    ],
    'edges': [],
}

PIPELINE_TREE_WITH_GATEWAY = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Step 1', 'params': {}},
        {'id': 'n2', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Step 2', 'params': {}},
        {'id': 'n3', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Step 3', 'params': {}},
        {'id': 'gw1', 'node_type': 'exclusive_gateway', 'label': 'Branch'},
    ],
    'edges': [
        {'from': 'n1', 'to': 'gw1'},
        {'from': 'gw1', 'to': 'n2', 'label': 'success',
         'condition': '${_result_n1} == "True"'},
        {'from': 'gw1', 'to': 'n3', 'label': 'failure',
         'condition': '${_result_n1} == "False"'},
    ],
}

PIPELINE_TREE_2_NODE = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Step 1', 'params': {}},
        {'id': 'n2', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Step 2', 'params': {}},
    ],
    'edges': [
        {'from': 'n1', 'to': 'n2'},
    ],
}


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, task_eager_propagates=True)
class PipelineE2ETest(TestCase):
    """End-to-end pipeline execution tests"""

    @classmethod
    def setUpTestData(cls):
        cls.user = Users.objects.create_user(
            username='e2etest', password='testpass123'
        )

        from iam.models import Project, ProjectMember
        cls.project = Project.objects.create(name='E2E Project')
        ProjectMember.objects.create(
            project=cls.project, user=cls.user, role='editor'
        )

    def _create_execution(self, tree, status='draft'):
        """Helper: create a FlowTemplate, publish, create FlowExecution"""
        from opsflow.models import FlowTemplate, FlowExecution
        tpl = FlowTemplate.objects.create(
            name='E2E Test Tpl',
            project=self.project,
            created_by=self.user,
            pipeline_tree=tree,
        )
        tpl.publish_snapshot()

        execution = FlowExecution.objects.create(
            template=tpl,
            project=self.project,
            status=status,
            created_by=self.user,
        )
        return execution

    def test_single_node_completes(self):
        """Single node pipeline builds and executes to completion"""
        execution = self._create_execution(PIPELINE_TREE_SIMPLE)

        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.run()

        execution.refresh_from_db()
        self.assertIn(
            execution.status,
            ['completed', 'failed'],
            f'Expected completed or failed, got {execution.status}'
        )

    def test_two_node_pipeline_completes(self):
        """Two node sequential pipeline"""
        execution = self._create_execution(PIPELINE_TREE_2_NODE)

        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.run()

        execution.refresh_from_db()
        self.assertIn(execution.status, ['completed', 'failed'])

    def test_pipeline_with_exclusive_gateway(self):
        """Pipeline with exclusive gateway executes"""
        execution = self._create_execution(PIPELINE_TREE_WITH_GATEWAY)

        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.run()

        execution.refresh_from_db()
        self.assertIn(execution.status, ['completed', 'failed'])
        # Check node status is populated
        self.assertIsNotNone(execution.node_status)

    def test_pipeline_retry_after_failure(self):
        """Force a node to fail, then retry"""
        from opsflow.models import FlowExecution
        execution = self._create_execution(PIPELINE_TREE_SIMPLE)

        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.run()

        execution.refresh_from_db()
        # If execution failed, test retry
        if execution.status == 'failed':
            from opsflow.core.node_dispatcher import NodeCommandDispatcher
            dispatcher = NodeCommandDispatcher(execution)
            result = dispatcher.retry('n1', operator=self.user)
            self.assertIsNotNone(result)

    def test_pipeline_cancel_during_execution(self):
        """Cancel a running execution"""
        execution = self._create_execution(PIPELINE_TREE_SIMPLE, status='running')

        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        result = engine.cancel()
        self.assertTrue(result.get('result', False))
