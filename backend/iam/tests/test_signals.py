"""IAM signal handler tests — dvadmin Role auto-sync"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from iam.models.menu_rbac import Role

from iam.models import Business, Project, BusinessMember

User = get_user_model()


class TestRoleSyncSignals(TestCase):
    """BusinessMember/ProjectMember save/delete → dvadmin Role sync"""

    def setUp(self):
        self.user = User.objects.create_user(username='synctest', password='test')
        self.biz = Business.objects.create(name='SyncBiz', code='syncbiz')
        self.project = Project.objects.create(name='SyncProj', business=self.biz)
        # Ensure ITSM roles exist
        self.admin_role, _ = Role.objects.get_or_create(key='itsm_admin', defaults={'name': 'ITSM Admin'})
        self.editor_role, _ = Role.objects.get_or_create(key='itsm_editor', defaults={'name': 'ITSM Editor'})
        self.viewer_role, _ = Role.objects.get_or_create(key='itsm_viewer', defaults={'name': 'ITSM Viewer'})

    def test_business_member_save_syncs_admin_role(self):
        """Creating BusinessMember(admin) → user gets itsm_admin Role"""
        from iam.signals import _sync_dvadmin_role
        bm = BusinessMember.objects.create(business=self.biz, user=self.user, role='admin')
        self.user.refresh_from_db()
        role_keys = set(self.user.role.values_list('key', flat=True))
        self.assertIn('itsm_admin', role_keys)

    def test_business_member_save_syncs_editor_role(self):
        """Creating BusinessMember(editor) → user gets itsm_editor Role"""
        BusinessMember.objects.create(business=self.biz, user=self.user, role='editor')
        self.user.refresh_from_db()
        role_keys = set(self.user.role.values_list('key', flat=True))
        self.assertIn('itsm_editor', role_keys)

    def test_business_member_delete_removes_role(self):
        """Deleting BusinessMember → ITSM Role removed"""
        bm = BusinessMember.objects.create(business=self.biz, user=self.user, role='admin')
        self.user.refresh_from_db()
        self.assertIn('itsm_admin', set(self.user.role.values_list('key', flat=True)))
        bm.delete()
        self.user.refresh_from_db()
        role_keys = set(self.user.role.values_list('key', flat=True))
        self.assertNotIn('itsm_admin', role_keys)
