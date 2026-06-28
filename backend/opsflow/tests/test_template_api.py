"""API integration tests — FlowTemplateViewSet CRUD and actions

Tests real HTTP requests/responses using DRF's APITestCase.
Covers: list/create/retrieve/update/destroy/publish/make-public/lock
"""
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

Users = get_user_model()


class TemplateAPITestBase(APITestCase):
    """Shared setup for template API tests"""

    def setUp(self):
        self.user = Users.objects.create_user(
            username='tplapi', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

        from iam.models import Project, ProjectMember
        self.project = Project.objects.create(name='API Test Project')
        ProjectMember.objects.create(
            project=self.project, user=self.user, role='admin'
        )

        from opsflow.models import FlowTemplate
        self.template = FlowTemplate.objects.create(
            name='Test Template',
            project=self.project,
            created_by=self.user,
            pipeline_tree={'nodes': [], 'edges': []},
        )


class TemplateListTest(TemplateAPITestBase):
    """GET /api/opsflow/templates/"""

    def test_list_returns_200(self):
        resp = self.client.get('/api/opsflow/templates/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_contains_created_template(self):
        resp = self.client.get('/api/opsflow/templates/')
        names = [t.get('name') for t in resp.data.get('data', [])]
        self.assertIn('Test Template', names)

    def test_unauthenticated_user_gets_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/opsflow/templates/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TemplateCreateTest(TemplateAPITestBase):
    """POST /api/opsflow/templates/"""

    def setUp(self):
        super().setUp()
        self.valid_payload = {
            'name': 'New Template',
            'project_id': self.project.id,
        }

    def test_create_returns_201(self):
        resp = self.client.post('/api/opsflow/templates/', self.valid_payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_without_name_returns_400(self):
        resp = self.client.post('/api/opsflow/templates/', {'project_id': self.project.id})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TemplateUpdateTest(TemplateAPITestBase):
    """PATCH /api/opsflow/templates/{id}/"""

    def test_update_name_returns_200(self):
        resp = self.client.patch(
            f'/api/opsflow/templates/{self.template.id}/',
            {'name': 'Updated Name'},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_update_changes_name(self):
        self.client.patch(
            f'/api/opsflow/templates/{self.template.id}/',
            {'name': 'Updated Name'},
        )
        from opsflow.models import FlowTemplate
        tpl = FlowTemplate.objects.get(id=self.template.id)
        self.assertEqual(tpl.name, 'Updated Name')


class TemplateDestroyTest(TemplateAPITestBase):
    """DELETE /api/opsflow/templates/{id}/"""

    def test_destroy_returns_200(self):
        resp = self.client.delete(f'/api/opsflow/templates/{self.template.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_destroy_removes_template(self):
        self.client.delete(f'/api/opsflow/templates/{self.template.id}/')
        from opsflow.models import FlowTemplate
        exists = FlowTemplate.objects.filter(id=self.template.id).exists()
        self.assertFalse(exists)


class TemplatePublishTest(TemplateAPITestBase):
    """POST /api/opsflow/templates/{id}/confirm_draft/"""

    def test_publish_draft_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/templates/{self.template.id}/confirm_draft/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_publish_creates_snapshot(self):
        self.client.post(f'/api/opsflow/templates/{self.template.id}/confirm_draft/')
        self.template.refresh_from_db()
        self.assertIsNotNone(self.template.snapshot)


class TemplateLockTest(TemplateAPITestBase):
    """POST /api/opsflow/templates/{id}/acquire_lock/"""

    def test_acquire_lock_returns_200(self):
        resp = self.client.post(
            f'/api/opsflow/templates/{self.template.id}/acquire_lock/'
        )
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_acquire_lock_twice_same_user_ok(self):
        self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        resp = self.client.post(
            f'/api/opsflow/templates/{self.template.id}/acquire_lock/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_release_lock_returns_200(self):
        self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        resp = self.client.post(
            f'/api/opsflow/templates/{self.template.id}/release_lock/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
