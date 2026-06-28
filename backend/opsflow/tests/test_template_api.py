"""API integration tests — FlowTemplate edit lock"""
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

Users = get_user_model()


class TemplateLockTest(APITestCase):
    """TemplateLock acquire/release actions (do not use ProjectFilteredViewset)"""

    def setUp(self):
        self.user = Users.objects.create_user(username='tplapi', password='testpass123')
        self.client.force_authenticate(user=self.user)
        from iam.models import Project, ProjectMember
        self.project = Project.objects.create(name='API Test Project')
        ProjectMember.objects.create(project=self.project, user=self.user, role='admin')
        from opsflow.models import FlowTemplate
        self.template = FlowTemplate.objects.create(
            name='Test Template', project=self.project, created_by=self.user,
            pipeline_tree={'nodes': [], 'edges': []},
        )

    def test_acquire_lock_returns_200(self):
        resp = self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        self.assertIn(resp.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_acquire_lock_twice_same_user_ok(self):
        self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        resp = self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_release_lock_returns_200(self):
        self.client.post(f'/api/opsflow/templates/{self.template.id}/acquire_lock/')
        resp = self.client.post(f'/api/opsflow/templates/{self.template.id}/release_lock/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
