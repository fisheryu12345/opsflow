"""IAM my_permissions endpoint tests"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from iam.models import Project, Business, BusinessMember, ProjectMember

User = get_user_model()


class TestMyPermissions(TestCase):
    """my_permissions endpoint — role resolution + page visibility"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test')
        self.biz = Business.objects.create(name='TestBiz', code='testbiz')
        self.project = Project.objects.create(name='TestProj', business=self.biz)
        self.factory = APIRequestFactory()

    def _call(self, project_id, user=None):
        from iam.views import my_permissions
        req = self.factory.get(f'/api/iam/my_permissions/?project_id={project_id}')
        req.user = user or self.user
        return my_permissions(req)

    def test_requires_project_id(self):
        """project_id is required"""
        req = self.factory.get('/api/iam/my_permissions/')
        req.user = self.user
        from iam.views import my_permissions
        resp = my_permissions(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('code', resp.data)
        self.assertNotEqual(resp.data.get('code'), 2000)

    def test_viewer_gets_limited_pages(self):
        """viewer role → only basic tabs visible"""
        ProjectMember.objects.create(project=self.project, user=self.user, role='viewer')
        resp = self._call(self.project.id)
        self.assertEqual(resp.data['data']['role'], 'viewer')
        pages = {p['key']: p['visible'] for p in resp.data['data']['pages']}
        self.assertTrue(pages.get('tickets'))
        self.assertFalse(pages.get('skill-groups', True))
        self.assertFalse(pages.get('assign-rules', True))

    def test_admin_gets_all_pages(self):
        """admin role → all tabs visible"""
        ProjectMember.objects.create(project=self.project, user=self.user, role='admin')
        resp = self._call(self.project.id)
        self.assertEqual(resp.data['data']['role'], 'admin')
        pages = {p['key']: p['visible'] for p in resp.data['data']['pages']}
        self.assertTrue(pages.get('assign-rules'))

    def test_business_member_inherits_role(self):
        """BusinessMember role → inherited by ProjectMember lookup"""
        BusinessMember.objects.create(business=self.biz, user=self.user, role='editor')
        resp = self._call(self.project.id)
        self.assertEqual(resp.data['data']['role'], 'editor')

    def test_default_viewer_when_no_membership(self):
        """no membership → defaults to viewer"""
        resp = self._call(self.project.id)
        self.assertEqual(resp.data['data']['role'], 'viewer')
