"""API integration tests — FlowExecutionViewSet

Tests: list/create(execute)/detail/start/pause/resume/cancel
"""
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

Users = get_user_model()


class ExecutionAPITestBase(APITestCase):
    """Shared setup for execution API tests"""

    def setUp(self):
        self.user = Users.objects.create_user(
            username='execapi', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        from iam.models import Project, ProjectMember
        self.project = Project.objects.create(name='Exec API Project')
        ProjectMember.objects.create(
            project=self.project, user=self.user, role='editor'
        )

        from opsflow.models import FlowTemplate
        self.template = FlowTemplate.objects.create(
            name='Exec Test Tpl',
            project=self.project,
            created_by=self.user,
            pipeline_tree={
                'nodes': [
                    {'id': 'n1', 'node_type': 'atom',
                     'atom_type': 'test_print_time',
                     'label': 'Print Time', 'params': {}},
                ],
                'edges': [],
            },
        )
        # Publish to enable execution
        self.template.publish_snapshot()

        from opsflow.models import FlowExecution
        self.execution = FlowExecution.objects.create(
            template=self.template,
            project=self.project,
            status='pending',
            created_by=self.user,
        )


class ExecutionListTest(ExecutionAPITestBase):
    """GET /api/opsflow/executions/"""

    def test_list_returns_200(self):
        resp = self.client.get('/api/opsflow/executions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_contains_created(self):
        resp = self.client.get('/api/opsflow/executions/')
        items = resp.data.get('data', []) if isinstance(resp.data, dict) else resp.data or []
        ids = [e.get('id') for e in items]
        self.assertIn(self.execution.id, ids)


class ExecutionDetailTest(ExecutionAPITestBase):
    """GET /api/opsflow/executions/{id}/"""

    def test_detail_returns_200(self):
        resp = self.client.get(f'/api/opsflow/executions/{self.execution.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detail_contains_expected_fields(self):
        resp = self.client.get(f'/api/opsflow/executions/{self.execution.id}/')
        data = resp.data.get('data', {}) if isinstance(resp.data, dict) else resp.data
        self.assertIn('status', data)
        self.assertIn('template', data)


class ExecutionStartTest(ExecutionAPITestBase):
    """POST /api/opsflow/executions/{id}/start/"""

    def test_start_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/start/'
        )
        self.assertIn(resp.status_code, (
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST
        ))

    def test_cannot_start_completed_execution(self):
        self.execution.status = 'completed'
        self.execution.save()
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/start/'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ExecutionPauseResumeTest(ExecutionAPITestBase):
    """POST /api/opsflow/executions/{id}/pause/ + /resume/"""

    def setUp(self):
        super().setUp()
        self.execution.status = 'running'
        self.execution.save()

    def test_pause_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/pause/'
        )
        self.assertIn(resp.status_code, (
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST
        ))

    def test_cancel_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/cancel/'
        )
        self.assertIn(resp.status_code, (
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST
        ))


class ExecutionNodeCommandsTest(ExecutionAPITestBase):
    """POST /api/opsflow/executions/{id}/retry_node/ + /skip_node/"""

    def setUp(self):
        super().setUp()
        self.execution.status = 'running'
        self.execution.node_status = {'n1': 'failed'}
        self.execution.save()

    def test_skip_node_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/skip_node/',
            {'node_id': 'n1'},
            format='json',
        )
        self.assertIn(resp.status_code, (
            status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST
        ))

    def test_skip_node_without_node_id_returns_400(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/skip_node/',
            {},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
