"""Seed complete IAM RBAC — all app MenuButtons + Roles + RoleTemplates."""
from django.core.management.base import BaseCommand

PERMISSIONS = {
    'ITSM': [
        ('itsm:workflow:create', 'Create Workflow', False),
        ('itsm:workflow:delete', 'Delete Workflow', True),
        ('itsm:ticket:create', 'Create Ticket', False),
        ('itsm:ticket:approve', 'Approve Ticket', False),
        ('itsm:ticket:assign', 'Assign Ticket', False),
        ('itsm:ticket:close', 'Close Ticket', False),
        ('itsm:sla:edit', 'Edit SLA', True),
        ('itsm:skillgroup:manage', 'Manage Skill Groups', False),
        ('itsm:duty:manage', 'Manage On-Duty', False),
        ('itsm:rule:manage', 'Manage Rules', True),
        ('itsm:escalation:manage', 'Manage Escalation', True),
    ],
    'OPSflow': [
        ('opsflow:template:create', 'Create Template', False),
        ('opsflow:template:delete', 'Delete Template', True),
        ('opsflow:template:publish', 'Publish Template', False),
        ('opsflow:execution:run', 'Run Execution', False),
        ('opsflow:execution:cancel', 'Cancel Execution', False),
        ('opsflow:schedule:manage', 'Manage Schedule', True),
        ('opsflow:webhook:manage', 'Manage Webhook', False),
    ],
    'CMDB': [
        ('cmdb:model:create', 'Create Model', False),
        ('cmdb:model:delete', 'Delete Model', True),
        ('cmdb:instance:create', 'Create Instance', False),
        ('cmdb:instance:delete', 'Delete Instance', True),
        ('cmdb:instance:edit', 'Edit Instance', False),
    ],
}

TEMPLATES = [
    {
        'name': 'ITSM Admin', 'code': 'itsm_admin',
        'app': 'ITSM', 'admin_only': True,
    },
    {
        'name': 'ITSM Editor', 'code': 'itsm_editor',
        'app': 'ITSM', 'admin_only': False,
    },
    {
        'name': 'ITSM Viewer', 'code': 'itsm_viewer',
        'app': 'ITSM', 'admin_only': None,  # no buttons
    },
    {
        'name': 'OPSflow Admin', 'code': 'opsflow_admin',
        'app': 'OPSflow', 'admin_only': True,
    },
    {
        'name': 'OPSflow Editor', 'code': 'opsflow_editor',
        'app': 'OPSflow', 'admin_only': False,
    },
    {
        'name': 'CMDB Admin', 'code': 'cmdb_admin',
        'app': 'CMDB', 'admin_only': True,
    },
    {
        'name': 'CMDB Viewer', 'code': 'cmdb_viewer',
        'app': 'CMDB', 'admin_only': None,
    },
]


class Command(BaseCommand):
    help = "Seed complete IAM RBAC permissions for all apps"

    def handle(self, *args, **options):
        from iam.models.page_config import IAMMenu as Menu, MenuButton, RoleMenuPermission, RoleMenuButtonPermission, Role
        from iam.models.role_template import RoleTemplate

        # Find or create menus for each app
        app_menus = {}
        for app_name in ['ITSM', 'OPSflow', 'CMDB']:
            menu, _ = Menu.objects.get_or_create(
                name=app_name,
                defaults={'sort': 50, 'status': 1, 'visible': 1, 'web_path': f'/{app_name.lower()}'},
            )
            app_menus[app_name] = menu
            self.stdout.write(f"  Menu: {app_name}")

        # Create MenuButtons
        btn_map = {}
        for app_name, perms in PERMISSIONS.items():
            menu = app_menus[app_name]
            for value, name, admin_only in perms:
                btn, created = MenuButton.objects.get_or_create(
                    value=value,
                    defaults={'name': name, 'menu': menu, 'method': 1, 'api': ''},
                )
                btn_map[value] = btn
                if created:
                    self.stdout.write(f"  + Button: {value}")

        # Create Roles + bind buttons
        for tpl in TEMPLATES:
            role, created = Role.objects.get_or_create(
                key=tpl['code'],
                defaults={'name': tpl['name'], 'sort': 100, 'status': 1},
            )
            if created:
                self.stdout.write(f"  + Role: {tpl['name']}")

            # Bind menu
            menu = app_menus[tpl['app']]
            RoleMenuPermission.objects.get_or_create(role=role, menu=menu)

            # Bind buttons
            if tpl['admin_only'] is not None:
                perms = PERMISSIONS[tpl['app']]
                for p_val, _, p_admin in perms:
                    if tpl['admin_only'] and not p_admin:
                        continue  # editor skips admin-only
                    if not tpl['admin_only'] and p_admin:
                        continue  # editor doesn't get admin buttons
                    btn = btn_map.get(p_val)
                    if btn:
                        RoleMenuButtonPermission.objects.get_or_create(role=role, menu_button=btn)

            # Create RoleTemplate
            menus_data = []
            if tpl['admin_only'] is not None:
                btn_ids = []
                for p_val, _, p_admin in PERMISSIONS[tpl['app']]:
                    if tpl['admin_only'] and not p_admin:
                        continue
                    if not tpl['admin_only'] and p_admin:
                        continue
                    if p_val in btn_map:
                        btn_ids.append(btn_map[p_val].id)
                menus_data.append({'menu_id': menu.id, 'button_ids': btn_ids})

            RoleTemplate.objects.get_or_create(
                code=tpl['code'],
                defaults={
                    'name': tpl['name'],
                    'source_role': role,
                    'menus': menus_data,
                    'is_system': True,
                },
            )

        self.stdout.write(self.style.SUCCESS("IAM permissions seeded!"))
