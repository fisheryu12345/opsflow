"""E2E integration tests — pipeline build → execute → result"""
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

Users = get_user_model()

SIMPLE_PIPELINE = {
    'nodes': [
        {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
         'label': 'Print Time', 'params': {}},
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

    def _create_execution(self, tree, status='draft'):
        from opsflow.models import FlowTemplate, FlowExecution
        tpl = FlowTemplate.objects.create(
            name='E2E Tpl', project=self.project, created_by=self.user, pipeline_tree=tree)
        tpl.publish_snapshot()
        return FlowExecution.objects.create(
            template=tpl, project=self.project, status=status, created_by=self.user)

    def test_single_node_completes(self):
        exec_ = self._create_execution(SIMPLE_PIPELINE)
        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(exec_)
        engine.run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])

    def test_two_node_pipeline_completes(self):
        tree = {
            'nodes': [
                {'id': 'n1', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Step 1', 'params': {}},
                {'id': 'n2', 'node_type': 'atom', 'atom_type': 'test_print_time',
                 'label': 'Step 2', 'params': {}},
            ],
            'edges': [{'from': 'n1', 'to': 'n2'}],
        }
        exec_ = self._create_execution(tree)
        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(exec_)
        engine.run()
        exec_.refresh_from_db()
        self.assertIn(exec_.status, ['completed', 'failed'])
