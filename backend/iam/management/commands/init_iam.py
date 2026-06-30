"""Comprehensive IAM initialization — replaces dvadmin `python manage.py init`.

Creates all foundation data: admin user, roles, menus, buttons, templates.
Run: python manage.py init_iam
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


# Navigation menu tree
MENU_TREE = [
    {
        'name': 'Dashboard', 'name_en': 'Dashboard', 'icon': 'HomeFilled',
        'web_path': '/dashboard', 'component': 'views/apps/dashboard/index',
        'component_name': 'dashboard', 'sort': 1,
    },
    {
        'name': 'OPSflow', 'name_en': 'OPSflow', 'icon': 'Operation',
        'web_path': '/opsflow', 'component': 'views/apps/opsflow/index',
        'component_name': 'opsflow', 'sort': 10,
    },
    {
        'name': 'ITSM', 'name_en': 'ITSM', 'icon': 'Setting',
        'web_path': '/itsm', 'component': 'views/apps/itsm/index',
        'component_name': 'itsm', 'sort': 20,
    },
    {
        'name': 'CMDB', 'name_en': 'CMDB', 'icon': 'Monitor',
        'web_path': '/cmdb', 'component': 'views/apps/cmdb/index',
        'component_name': 'cmdb', 'sort': 30,
    },
    {
        'name': 'IAM', 'name_en': 'IAM', 'icon': 'Lock',
        'web_path': '/iam', 'component': 'views/apps/iam/index',
        'component_name': 'iam', 'sort': 40,
        'children': [
            {'name': 'Roles', 'name_en': 'Roles', 'icon': 'Avatar',
             'web_path': '/iam?tab=roles', 'component': 'views/apps/iam/index',
             'component_name': 'iam-roles', 'sort': 1, 'is_catalog': False},
        ],
    },
]

DEPT_DEFAULTS = [
    {'name': 'IT Ops', 'key': 'it-ops', 'sort': 1},
    {'name': 'Engineering', 'key': 'engineering', 'sort': 2},
    {'name': 'Security', 'key': 'security', 'sort': 3},
]

ROLE_DEFAULTS = [
    {'name': 'Platform Admin', 'key': 'admin', 'sort': 1},
    {'name': 'Operator', 'key': 'operator', 'sort': 2},
    {'name': 'Viewer', 'key': 'viewer_only', 'sort': 3},
]


class Command(BaseCommand):
    help = "Initialize IAM foundation data (replaces dvadmin `python manage.py init`)"

    def handle(self, *args, **options):
        self._init_depts()
        self._init_roles()
        self._init_menus()
        self._init_admin_user()
        self._init_itsm_opsflow_cmdb_perms()
        self._init_environments()
        self.stdout.write(self.style.SUCCESS("IAM initialization complete!"))

    def _init_depts(self):
        from dvadmin.system.models import Dept
        for d in DEPT_DEFAULTS:
            Dept.objects.get_or_create(key=d['key'], defaults=d)
        self.stdout.write(f"  Depts: {Dept.objects.count()}")

    def _init_roles(self):
        from iam.models.menu_rbac import Role
        for r in ROLE_DEFAULTS:
            Role.objects.get_or_create(key=r['key'], defaults=r)
        self.stdout.write(f"  Roles: {Role.objects.count()}")

    def _init_menus(self):
        from iam.models.menu_rbac import Menu
        for m in MENU_TREE:
            obj, created = Menu.objects.get_or_create(
                web_path=m['web_path'],
                defaults=m,
            )
            if created:
                self.stdout.write(f"  + Menu: {m['name']}")
        # Grant all core menus to every role (regular users need to see navigation)
        from iam.models.menu_rbac import Role, RoleMenuPermission as RMP
        core_menus = Menu.objects.filter(name__in=['Dashboard', 'OPSflow', 'ITSM', 'CMDB', 'IAM'])
        for role in Role.objects.filter(status=1):
            for menu in core_menus:
                RMP.objects.get_or_create(role=role, menu=menu)
        self.stdout.write(f"  Menus: {Menu.objects.count()}, granted to {Role.objects.count()} roles")

    def _init_admin_user(self):
        from django.contrib.auth import get_user_model
        from iam.models.menu_rbac import Role, RoleMenuPermission, RoleMenuButtonPermission, Menu, MenuButton
        from dvadmin.system.models import Dept

        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("  Admin user already exists, skip")
            return

        dept = Dept.objects.first()
        admin = User.objects.create_superuser(
            username='superadmin', password='yupei1986',
            name='Super Admin', email='admin@opsflow.local',
            dept=dept,
        )
        self.stdout.write(f"  + Admin user: {admin.username} / yupei1986")

        # Grant platform admin role with full menu+button access
        admin_role = Role.objects.filter(key='admin').first()
        if not admin_role:
            return
        admin.role.add(admin_role)

        # Bind all menus and buttons to admin role
        for menu in Menu.objects.filter(status=1):
            RoleMenuPermission.objects.get_or_create(role=admin_role, menu=menu)
        for btn in MenuButton.objects.all():
            RoleMenuButtonPermission.objects.get_or_create(role=admin_role, menu_button=btn)
        self.stdout.write(f"  Admin role bound to all menus + buttons")

    def _init_environments(self):
        """Create default deploy environments (dev/staging/prod)."""
        from iam.models import DeployEnvironment, DeployEnvironmentPermission
        from django.contrib.auth import get_user_model
        User = get_user_model()

        envs = [
            ('Development', 'dev', 0, 10),
            ('Staging', 'staging', 50, 20),
            ('Production', 'prod', 100, 30),
        ]
        for name, code, risk, sort in envs:
            DeployEnvironment.objects.get_or_create(code=code, defaults={'name': name, 'risk_level': risk, 'sort': sort})

        # Grant prod permission to superusers
        prod = DeployEnvironment.objects.filter(code='prod').first()
        if prod:
            for user in User.objects.filter(is_superuser=True):
                DeployEnvironmentPermission.objects.get_or_create(
                    user=user, environment=prod, defaults={'can_execute': True},
                )
        self.stdout.write(f"  Environments: {DeployEnvironment.objects.count()}")

    def _init_itsm_opsflow_cmdb_perms(self):
        """Delegate to seed_iam_permissions for app-level permissions."""
        from iam.management.commands.seed_iam_permissions import Command as SeedCmd
        SeedCmd().handle()