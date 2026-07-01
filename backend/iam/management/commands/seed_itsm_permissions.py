"""Seed ITSM permission keys — dvadmin Role + MenuButton + RoleMenuButtonPermission"""
from django.core.management.base import BaseCommand


# ITSM permission keys
PERMISSIONS = [
    # (value, name, admin_only)
    ('itsm:workflow:create', 'Create workflow', False),
    ('itsm:workflow:delete', 'Delete workflow', True),
    ('itsm:ticket:create', 'Create ticket', False),
    ('itsm:ticket:approve', 'Approve ticket', False),
    ('itsm:ticket:assign', 'Assign ticket', False),
    ('itsm:ticket:close', 'Close ticket', False),
    ('itsm:sla:edit', 'Edit SLA', True),
    ('itsm:skillgroup:manage', 'Manage skill groups', False),
    ('itsm:duty:manage', 'Manage on-duty schedules', False),
    ('itsm:rule:manage', 'Manage assign rules', True),
    ('itsm:escalation:manage', 'Manage escalation levels', True),
]

ROLE_DEFS = [
    ('ITSM Admin', 'itsm_admin', PERMISSIONS),   # all 11 permissions
    ('ITSM Editor', 'itsm_editor', [p for p in PERMISSIONS if not p[2]]),  # 7 non-admin-only
    ('ITSM Viewer', 'itsm_viewer', []),  # read-only
]


class Command(BaseCommand):
    help = "Seed ITSM permission keys (MenuButton + Role + RoleMenuButtonPermission)"

    def handle(self, *args, **options):
        from iam.models.page_config import IAMMenu as Menu, MenuButton, Role
        from iam.models.permission import IAMRole as RoleMenuButtonPermission, RoleMenuPermission

        # Find or create the ITSM Menu
        itsm_menu, _ = Menu.objects.get_or_create(
            name='ITSM',
            defaults={
                'name_en': 'ITSM',
                'web_path': '/itsm',
                'component': 'views/apps/itsm/index',
                'component_name': 'itsm',
                'sort': 50,
                'status': 1,
                'visible': 1,
            },
        )
        self.stdout.write(f"  Menu: {itsm_menu.name}")

        # Create MenuButtons + collect by role
        btn_map = {}
        for value, name, admin_only in PERMISSIONS:
            btn, created = MenuButton.objects.get_or_create(
                value=value,
                defaults={'name': name, 'menu': itsm_menu, 'method': 1, 'api': ''},
            )
            btn_map[value] = btn
            if created:
                self.stdout.write(f"  + MenuButton: {value}")

        # Create Roles + bind MenuButtons
        for role_name, role_key, perms in ROLE_DEFS:
            role, created = Role.objects.get_or_create(
                key=role_key,
                defaults={'name': role_name, 'sort': 100, 'status': 1},
            )
            if created:
                self.stdout.write(f"  + Role: {role_name} ({role_key})")

            # Bind Menu
            RoleMenuPermission.objects.get_or_create(role=role, menu=itsm_menu)

            # Bind MenuButtons
            for p_val, _, _ in perms:
                btn = btn_map.get(p_val)
                if btn:
                    RoleMenuButtonPermission.objects.get_or_create(
                        role=role, menu_button=btn,
                    )

        self.stdout.write(self.style.SUCCESS("ITSM permissions seeded!"))
