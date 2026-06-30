"""IAM RBAC integration tests — 权限申请/审批/赋权 全链路"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class TestPermissionRequestModel(TestCase):
    """PermissionRequest 模型测试"""

    def setUp(self):
        from iam.models.menu_rbac import Role, Menu
        self.user = User.objects.create_user(username='testuser', password='test')
        self.role = Role.objects.create(name='Test Role', key='test_role', sort=1, status=True)
        self.menu = Menu.objects.create(name='Test Menu', sort=1, status=True, visible=True)

    def test_create_role_request(self):
        """创建 role 类型权限申请"""
        from iam.models.rbac import PermissionRequest
        req = PermissionRequest.objects.create(
            user=self.user, request_type='role', target_role=self.role,
            reason='Need access', status='pending',
        )
        self.assertEqual(req.request_type, 'role')
        self.assertEqual(req.status, 'pending')
        self.assertEqual(str(req), f'{self.user} - 角色 - 待审批')

    def test_create_menu_request_with_buttons(self):
        """创建 menu 类型申请 + 选中特定按钮"""
        from iam.models.rbac import PermissionRequest
        from iam.models.menu_rbac import MenuButton
        btn = MenuButton.objects.create(name='Create', value='test:create', menu=self.menu, method=1, api='')
        req = PermissionRequest.objects.create(
            user=self.user, request_type='menu', target_menu=self.menu,
            selected_buttons=[btn.id], reason='Need menu', status='pending',
        )
        self.assertEqual(req.selected_buttons, [btn.id])

    def test_create_project_role_request(self):
        """创建 project_role 类型申请"""
        from iam.models.rbac import PermissionRequest
        from iam.models import Project, Business
        biz = Business.objects.create(name='Test Biz', code='test-biz')
        project = Project.objects.create(name='Test Project', business=biz)
        req = PermissionRequest.objects.create(
            user=self.user, request_type='project_role',
            target_project=project, target_project_role='editor',
            reason='Need project access', status='pending',
        )
        self.assertEqual(req.request_type, 'project_role')
        self.assertEqual(req.target_project_role, 'editor')

    def test_status_transitions(self):
        """状态流转: pending → approved → rejected"""
        from iam.models.rbac import PermissionRequest
        req = PermissionRequest.objects.create(
            user=self.user, request_type='role', target_role=self.role,
            reason='test', status='pending',
        )
        req.status = 'approved'
        req.save(update_fields=['status'])
        self.assertEqual(req.status, 'approved')

        req.status = 'rejected'
        req.save(update_fields=['status'])
        self.assertEqual(req.status, 'rejected')


class TestRoleTemplate(TestCase):
    """RoleTemplate 模型测试"""

    def test_create_and_apply_template(self):
        from iam.models.role_template import RoleTemplate
        from iam.models.menu_rbac import Role, Menu, MenuButton, RoleMenuPermission, RoleMenuButtonPermission

        role = Role.objects.create(name='Apply Role', key='apply_role', sort=1, status=True)
        menu = Menu.objects.create(name='App', sort=1, status=True, visible=True)
        btn = MenuButton.objects.create(name='Action', value='app:action', menu=menu, method=1, api='')

        tpl = RoleTemplate.objects.create(
            name='Test Template', code='test_tpl', source_role=role,
            menus=[{'menu_id': menu.id, 'button_ids': [btn.id]}], is_system=False,
        )

        # Apply template
        new_role = Role.objects.create(name='New Role', key='new_role', sort=2, status=True)
        tpl.apply_to_role(new_role)

        self.assertTrue(RoleMenuPermission.objects.filter(role=new_role, menu=menu).exists())
        self.assertTrue(RoleMenuButtonPermission.objects.filter(role=new_role, menu_button=btn).exists())


class TestMyPermissionsAPI(TestCase):
    """my_permissions API 端点测试"""

    def setUp(self):
        from iam.models import Project, Business
        self.user = User.objects.create_user(username='permuser', password='test')
        biz = Business.objects.create(name='Perm Biz', code='perm-biz')
        self.project = Project.objects.create(name='Perm Project', business=biz)

    def test_my_permissions_missing_project_id(self):
        """缺少 project_id 参数返回错误"""
        self.client.force_login(self.user)
        resp = self.client.get('/api/iam/my_permissions/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('msg', str(data))

    def test_my_permissions_viewer(self):
        """viewer 用户查看自己的权限"""
        from iam.models import ProjectMember
        ProjectMember.objects.create(project=self.project, user=self.user, role='viewer')
        self.client.force_login(self.user)
        resp = self.client.get(f'/api/iam/my_permissions/?project_id={self.project.id}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('data', {}).get('role'), 'viewer')
        self.assertIn('pages', data.get('data', {}))
        self.assertIn('permissions', data.get('data', {}))

    def test_my_permissions_admin(self):
        """admin 用户查看自己的权限"""
        from iam.models import ProjectMember
        ProjectMember.objects.create(project=self.project, user=self.user, role='admin')
        self.client.force_login(self.user)
        resp = self.client.get(f'/api/iam/my_permissions/?project_id={self.project.id}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get('data', {}).get('role'), 'admin')
