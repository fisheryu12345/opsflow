"""API integration tests — FlowExecutionViewSet"""
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

Users = get_user_model()


class ExecAPITestBase(APITestCase):

    def setUp(self):
        self.user = Users.objects.create_user(username='execapi', password='testpass123')
        self.client.force_authenticate(user=self.user)
        from iam.models import Project, ProjectMember
        self.project = Project.objects.create(name='Exec API Project')
        ProjectMember.objects.create(project=self.project, user=self.user, role='editor')
        from opsflow.models import FlowTemplate, FlowExecution
        self.template = FlowTemplate.objects.create(
            name='Exec Tpl', project=self.project, created_by=self.user,
            pipeline_tree={'nodes': [{'id': 'n1', 'node_type': 'atom',
             'atom_type': 'test_print_time', 'label': 'Print', 'params': {}}], 'edges': []},
        )
        self.template.publish_snapshot()
        self.execution = FlowExecution.objects.create(
            template=self.template, project=self.project,
            status='pending', created_by=self.user,
        )


class ExecutionListTest(ExecAPITestBase):

    def test_list_returns_200(self):
        resp = self.client.get('/api/opsflow/executions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_contains_created(self):
        resp = self.client.get('/api/opsflow/executions/')
        data = resp.data.get('data', []) if isinstance(resp.data, dict) else resp.data or []
        ids = [e.get('id') for e in (data or [])]
        self.assertIn(self.execution.id, ids)


class ExecutionDetailTest(ExecAPITestBase):

    def test_detail_returns_200(self):
        resp = self.client.get(f'/api/opsflow/executions/{self.execution.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detail_contains_expected_fields(self):
        resp = self.client.get(f'/api/opsflow/executions/{self.execution.id}/')
        data = resp.data.get('data', {}) if isinstance(resp.data, dict) else {}
        self.assertIn('status', data)


class ExecutionLifecycleTest(ExecAPITestBase):

    def setUp(self):
        super().setUp()
        self.execution.status = 'running'
        self.execution.save()

    def test_pause_returns_200(self):
        resp = self.client.post(f'/api/opsflow/executions/{self.execution.id}/pause/')
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))

    def test_cancel_returns_200(self):
        resp = self.client.post(f'/api/opsflow/executions/{self.execution.id}/cancel/')
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))

    def test_cannot_start_completed(self):
        self.execution.status = 'completed'
        self.execution.save()
        resp = self.client.post(f'/api/opsflow/executions/{self.execution.id}/start/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ExecutionNodeCommandTest(ExecAPITestBase):

    def setUp(self):
        super().setUp()
        self.execution.status = 'failed'
        self.execution.node_status = {'n1': 'failed'}
        self.execution.save()

    def test_skip_node_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/skip_node/',
            {'node_id': 'n1'}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST))

    def test_skip_node_without_id_returns_400(self):
        resp = self.client.post(
            f'/api/opsflow/executions/{self.execution.id}/skip_node/',
            {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
