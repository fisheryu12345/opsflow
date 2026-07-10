"""Seed PageTab + PageButton + IAMPermission + IAMRole config for all apps.

Creates tab/button configurations for opsflow, itsm, and cmdb apps,
along with viewer/editor/admin roles and their permission bindings.
Idempotent via get_or_create throughout.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed PageTab, PageButton, IAMPermission, IAMRole configs"

    def handle(self, *args, **options):
        self._seed_permissions()
        self._seed_page_configs()
        self._seed_roles()
        self._seed_role_permissions()
        self.stdout.write(self.style.SUCCESS("IAM page configs seeded!"))

    # ── Permissions ────────────────────────────────────────────────

    def _seed_permissions(self):
        """Create all IAMPermission records referenced by tabs, buttons, and roles."""
        from iam.models.permission import IAMPermission

        perms = [
            # ── OpsFlow tab / button perms ──
            ('opsflow:designer:view', '查看设计器', 'opsflow'),
            ('opsflow:templates:view', '查看模板中心', 'opsflow'),
            ('opsflow:template:create', '创建模板', 'opsflow'),
            ('opsflow:template:delete', '删除模板', 'opsflow'),
            ('opsflow:template:publish', '发布模板', 'opsflow'),
            ('opsflow:executions:view', '查看任务执行', 'opsflow'),
            ('opsflow:execution:run', '执行任务', 'opsflow'),
            ('opsflow:execution:cancel', '取消执行', 'opsflow'),
            ('opsflow:approvals:view', '查看审批', 'opsflow'),
            ('opsflow:knowledge:view', '查看知识库', 'opsflow'),
            ('opsflow:knowledge:create', '创建知识条目', 'opsflow'),
            ('opsflow:knowledge:delete', '删除知识条目', 'opsflow'),
            ('opsflow:webhooks:view', '查看 Webhook', 'opsflow'),
            ('opsflow:webhook:manage', '管理 Webhook', 'opsflow'),
            ('opsflow:schedule:manage', '管理调度', 'opsflow'),
            ('opsflow:project:view', '查看项目管理', 'opsflow'),
            # ── ITSM tab + button perms (sync with seed_itsm_permissions.py) ──
            ('itsm:ticket:create', '创建工单', 'itsm'),
            ('itsm:ticket:approve', '审批工单', 'itsm'),
            ('itsm:ticket:assign', '分配工单', 'itsm'),
            ('itsm:ticket:close', '关闭工单', 'itsm'),
            ('itsm:workflows:view', '查看流程模板', 'itsm'),
            ('itsm:workflow:create', '创建流程', 'itsm'),
            ('itsm:workflow:design', '设计流程', 'itsm'),
            ('itsm:workflow:deploy', '发布流程', 'itsm'),
            ('itsm:workflow:delete', '删除流程', 'itsm'),
            ('itsm:skill_groups:view', '查看技能组', 'itsm'),
            ('itsm:skillgroup:manage', '管理技能组', 'itsm'),
            ('itsm:on_duty:view', '查看排班', 'itsm'),
            ('itsm:duty:manage', '管理排班', 'itsm'),
            ('itsm:assign_rules:view', '查看路由规则', 'itsm'),
            ('itsm:rule:manage', '管理路由', 'itsm'),
            ('itsm:escalation:view', '查看升级配置', 'itsm'),
            ('itsm:escalation:manage', '管理升级', 'itsm'),
            ('itsm:sla:edit', '编辑 SLA', 'itsm'),
            ('itsm:service:admin', '管理服务目录', 'itsm'),
            # ── CMDB tab + button perms ──
            ('cmdb:schema:view', '查看模型', 'cmdb'),
            ('cmdb:schema:create', '创建模型', 'cmdb'),
            ('cmdb:schema:delete', '删除模型', 'cmdb'),
            ('cmdb:sync:view', '查看同步', 'cmdb'),
            ('cmdb:sync:run', '执行同步', 'cmdb'),
            ('cmdb:events:view', '查看事件', 'cmdb'),
            ('cmdb:events:subscribe', '订阅事件', 'cmdb'),
            ('cmdb:events:unsubscribe', '取消订阅', 'cmdb'),
            # ── System admin perms ──
            ('system:user:manage', '用户管理', 'system'),
            ('system:dept:manage', '部门管理', 'system'),
            ('system:log:view', '查看日志', 'system'),
            ('system:file:manage', '文件管理', 'system'),
            # ── OpsAgent tab + button perms ──
            ('opsagent:console:view', '查看控制台', 'opsagent'),
            ('opsagent:console:execute', '执行指令', 'opsagent'),
            ('opsagent:sessions:view', '查看会话', 'opsagent'),
            ('opsagent:session:delete', '删除会话', 'opsagent'),
        ]
        created = 0
        for codename, label, app in perms:
            _, c = IAMPermission.objects.get_or_create(
                codename=codename,
                defaults={'label': label, 'app': app, 'scope': 'platform'},
            )
            if c:
                created += 1
        self.stdout.write(f"  IAMPermissions: {IAMPermission.objects.count()} total, {created} new")

    # ── Page tabs + buttons ────────────────────────────────────────

    def _seed_page_configs(self):
        """Create PageTab and PageButton records for opsflow, itsm, cmdb."""
        from iam.models.page_config import PageTab, PageButton

        # ── OpsFlow ────────────────────────────────────────────────
        opsflow_tabs = [
            {'key': 'dashboard',   'label_zh': '看板',     'label_en': 'Dashboard',  'icon': 'DataAnalysis',  'required_perm': None,                   'is_default': True,  'sort': 10},
            {'key': 'templates',   'label_zh': '模板中心',   'label_en': 'Templates',  'icon': 'Document',      'required_perm': 'opsflow:templates:view',                  'sort': 20},
            {'key': 'executions',  'label_zh': '任务执行',   'label_en': 'Executions', 'icon': 'VideoPlay',     'required_perm': 'opsflow:executions:view',                 'sort': 30},
            {'key': 'approvals',   'label_zh': '审批',      'label_en': 'Approvals',  'icon': 'Clock',         'required_perm': 'opsflow:approvals:view',                  'sort': 40},
            {'key': 'knowledge',   'label_zh': '知识库',     'label_en': 'Knowledge',  'icon': 'Collection',    'required_perm': 'opsflow:knowledge:view',                  'sort': 50},
            {'key': 'logs',        'label_zh': '执行日志',   'label_en': 'Logs',      'icon': 'List',          'required_perm': None,                                     'sort': 60},
            {'key': 'webhooks',    'label_zh': 'Webhook',   'label_en': 'Webhook',    'icon': 'Link',          'required_perm': 'opsflow:webhooks:view',                   'sort': 70},
            {'key': 'project',     'label_zh': '项目管理',   'label_en': 'Project',   'icon': 'Setting',       'required_perm': 'opsflow:project:view',                    'sort': 80},
            {'key': 'designer',    'label_zh': '设计器',     'label_en': 'Designer',  'icon': 'EditPen',       'required_perm': 'opsflow:designer:view',  'visible': True,  'sort': 5},
        ]
        opsflow_buttons = {
            'templates': [
                {'key': 'create', 'label_zh': '新建', 'label_en': 'Create',   'icon': 'Plus',   'required_perm': 'opsflow:template:create', 'style': 'primary', 'sort': 10},
                {'key': 'delete', 'label_zh': '删除', 'label_en': 'Delete',   'icon': 'Delete', 'required_perm': 'opsflow:template:delete', 'style': 'danger',  'sort': 20},
                {'key': 'publish', 'label_zh': '发布', 'label_en': 'Publish',  'icon': 'Upload', 'required_perm': 'opsflow:template:publish', 'style': 'success', 'sort': 30},
            ],
            'executions': [
                {'key': 'run',    'label_zh': '执行',   'label_en': 'Run',    'icon': 'VideoPlay', 'required_perm': 'opsflow:execution:run',    'style': 'primary', 'sort': 10},
                {'key': 'cancel', 'label_zh': '取消',   'label_en': 'Cancel', 'icon': 'Remove',    'required_perm': 'opsflow:execution:cancel', 'style': 'danger',  'sort': 20},
            ],
            'knowledge': [
                {'key': 'create', 'label_zh': '新建',   'label_en': 'Create',  'icon': 'Plus',   'required_perm': 'opsflow:knowledge:create', 'style': 'primary', 'sort': 10},
                {'key': 'delete', 'label_zh': '删除',   'label_en': 'Delete',  'icon': 'Delete', 'required_perm': 'opsflow:knowledge:delete', 'style': 'danger',  'sort': 20},
            ],
            'webhooks': [
                {'key': 'manage', 'label_zh': '管理',   'label_en': 'Manage',  'icon': 'Setting', 'required_perm': 'opsflow:webhook:manage',    'style': 'primary', 'sort': 10},
            ],
            'project': [
                {'key': 'schedule', 'label_zh': '调度管理', 'label_en': 'Schedule', 'icon': 'Timer', 'required_perm': 'opsflow:schedule:manage', 'style': 'primary', 'sort': 10},
            ],
        }

        # ── ITSM ──────────────────────────────────────────────────
        itsm_tabs = [
            {'key': 'service-market', 'label_zh': '服务市场', 'label_en': 'Service Catalog','icon': 'List','required_perm': None,                                        'is_default': True,  'sort': 10},
            {'key': 'tickets',       'label_zh': '工单',      'label_en': 'Tickets',      'icon': 'List',          'required_perm': None,                     'is_default': False, 'sort': 20},
            {'key': 'dashboard',     'label_zh': '看板',      'label_en': 'Dashboard',    'icon': 'DataAnalysis',  'required_perm': None,                     'is_default': False, 'sort': 30},
            {'key': 'workflows',     'label_zh': '流程模板',   'label_en': 'Workflows',    'icon': 'Setting',       'required_perm': 'itsm:workflows:view',                   'sort': 40},
            # ── ITSM 管理 ──
            {'key': 'service-admin',  'label_zh': '服务目录管理','label_en': 'Catalog Admin','icon': 'Setting','required_perm': 'itsm:service:admin',                       'sort': 50},
            {'key': 'sla',           'label_zh': 'SLA',       'label_en': 'SLA',          'icon': 'Clock',         'required_perm': None,                     'sort': 60},
            {'key': 'escalation',    'label_zh': '升级',      'label_en': 'Escalation',   'icon': 'WarningFilled', 'required_perm': 'itsm:escalation:view',     'sort': 70},
            {'key': 'schedule',     'label_zh': '排班表',    'label_en': 'Schedule',     'icon': 'Calendar',      'required_perm': 'itsm:sla:edit',                        'sort': 80},
            {'key': 'delegation',    'label_zh': '委托',      'label_en': 'Delegation',   'icon': 'User',          'required_perm': None,                     'sort': 110},
        ]
        itsm_buttons = {
            'tickets': [
                {'key': 'create', 'label_zh': '新建工单', 'label_en': 'Create Ticket', 'icon': 'Plus',   'required_perm': 'itsm:ticket:create', 'style': 'primary', 'sort': 10},
                {'key': 'approve','label_zh': '审批',     'label_en': 'Approve',        'icon': 'Select', 'required_perm': 'itsm:ticket:approve','style': 'success', 'sort': 20},
                {'key': 'assign', 'label_zh': '分配',     'label_en': 'Assign',         'icon': 'User',   'required_perm': 'itsm:ticket:assign', 'style': 'default', 'sort': 30},
                {'key': 'close',  'label_zh': '关闭',     'label_en': 'Close',          'icon': 'CircleClose','required_perm':'itsm:ticket:close','style':'default','sort': 40},
            ],
            'workflows': [
                {'key': 'create', 'label_zh': '创建',   'label_en': 'Create', 'icon': 'Plus',   'required_perm': 'itsm:workflow:create', 'style': 'primary', 'sort': 10},
                {'key': 'design', 'label_zh': '设计',   'label_en': 'Design', 'icon': 'Edit',   'required_perm': 'itsm:workflow:design', 'style': 'default', 'sort': 20},
                {'key': 'deploy', 'label_zh': '发布',   'label_en': 'Deploy', 'icon': 'Upload', 'required_perm': 'itsm:workflow:deploy', 'style': 'success', 'sort': 30},
                {'key': 'delete', 'label_zh': '删除',   'label_en': 'Delete', 'icon': 'Delete', 'required_perm': 'itsm:workflow:delete', 'style': 'danger',  'sort': 40},
            ],
            'sla': [
                {'key': 'edit', 'label_zh': '编辑 SLA', 'label_en': 'Edit SLA', 'icon': 'Edit', 'required_perm': 'itsm:sla:edit', 'style': 'primary', 'sort': 10},
            ],
        }

        # ── CMDB ──────────────────────────────────────────────────
        cmdb_tabs = [
            {'key': 'schema',     'label_zh': '模型',   'label_en': 'Schema',     'icon': 'Collection',    'required_perm': 'cmdb:schema:view',     'is_default': True,  'sort': 10},
            {'key': 'instances',  'label_zh': '实例',   'label_en': 'Instances',  'icon': 'List',          'required_perm': None,                   'sort': 20},
            {'key': 'sync',       'label_zh': '同步',   'label_en': 'Sync',       'icon': 'Refresh',       'required_perm': 'cmdb:sync:view',       'sort': 30},
            {'key': 'events',     'label_zh': '事件',   'label_en': 'Events',     'icon': 'Bell',          'required_perm': 'cmdb:events:view',     'sort': 40},
        ]
        cmdb_buttons = {
            'schema': [
                {'key': 'create', 'label_zh': '创建模型', 'label_en': 'Create Model', 'icon': 'Plus',   'required_perm': 'cmdb:schema:create', 'style': 'primary', 'sort': 10},
                {'key': 'delete', 'label_zh': '删除模型', 'label_en': 'Delete Model', 'icon': 'Delete', 'required_perm': 'cmdb:schema:delete', 'style': 'danger',  'sort': 20},
            ],
            'sync': [
                {'key': 'run', 'label_zh': '执行同步', 'label_en': 'Run Sync', 'icon': 'Refresh', 'required_perm': 'cmdb:sync:run', 'style': 'primary', 'sort': 10},
            ],
            'events': [
                {'key': 'subscribe',   'label_zh': '订阅',     'label_en': 'Subscribe',   'icon': 'Plus',   'required_perm': 'cmdb:events:subscribe',   'style': 'primary', 'sort': 10},
                {'key': 'unsubscribe', 'label_zh': '取消订阅', 'label_en': 'Unsubscribe', 'icon': 'Delete', 'required_perm': 'cmdb:events:unsubscribe', 'style': 'danger',  'sort': 20},
            ],
        }

        # ── OpsAgent ──────────────────────────────────────────────
        opsagent_tabs = [
            {'key': 'console',  'label_zh': '控制台',   'label_en': 'Console',  'icon': 'Monitor',       'required_perm': 'opsagent:console:view', 'is_default': True,  'sort': 10},
            {'key': 'sessions', 'label_zh': '历史会话', 'label_en': 'Sessions', 'icon': 'Clock',          'required_perm': 'opsagent:sessions:view',                     'sort': 20},
        ]
        opsagent_buttons = {
            'console': [
                {'key': 'execute', 'label_zh': '执行',   'label_en': 'Execute',  'icon': 'VideoPlay',      'required_perm': 'opsagent:console:execute', 'style': 'primary', 'sort': 10},
            ],
            'sessions': [
                {'key': 'delete', 'label_zh': '删除',   'label_en': 'Delete',   'icon': 'Delete',          'required_perm': 'opsagent:session:delete',  'style': 'danger',  'sort': 10},
            ],
        }

        app_configs = [
            ('opsflow', opsflow_tabs, opsflow_buttons),
            ('itsm', itsm_tabs, itsm_buttons),
            ('cmdb', cmdb_tabs, cmdb_buttons),
            ('opsagent', opsagent_tabs, opsagent_buttons),
        ]

        tabs_created = 0
        buttons_created = 0
        for app, tabs, buttons_dict in app_configs:
            for td in tabs:
                tab, c = PageTab.objects.get_or_create(
                    app=app, key=td['key'],
                    defaults={
                        'label_zh': td['label_zh'],
                        'label_en': td['label_en'],
                        'icon': td['icon'],
                        'sort': td.get('sort', 1),
                        'required_perm': td.get('required_perm'),
                        'is_default': td.get('is_default', False),
                        'visible': td.get('visible', True),
                    },
                )
                if c:
                    tabs_created += 1

                # Create buttons for this tab
                for bd in buttons_dict.get(td['key'], []):
                    _, c2 = PageButton.objects.get_or_create(
                        tab=tab, key=bd['key'],
                        defaults={
                            'label_zh': bd['label_zh'],
                            'label_en': bd['label_en'],
                            'icon': bd.get('icon'),
                            'required_perm': bd['required_perm'],
                            'style': bd.get('style', 'default'),
                            'sort': bd.get('sort', 1),
                        },
                    )
                    if c2:
                        buttons_created += 1

        self.stdout.write(f"  PageTabs: {PageTab.objects.count()} total, {tabs_created} new")
        self.stdout.write(f"  PageButtons: {PageButton.objects.count()} total, {buttons_created} new")

    # ── Roles ─────────────────────────────────────────────────────

    def _seed_roles(self):
        """Create IAMRole records for all apps."""
        from iam.models.permission import IAMRole

        roles = [
            # OpsFlow roles
            ('opsflow_viewer', 'OpsFlow Viewer'),
            ('opsflow_editor', 'OpsFlow Editor'),
            ('opsflow_admin', 'OpsFlow Admin'),
            # ITSM roles
            ('itsm_viewer', 'ITSM Viewer'),
            ('itsm_editor', 'ITSM Editor'),
            ('itsm_admin', 'ITSM Admin'),
            # CMDB roles
            ('cmdb_viewer', 'CMDB Viewer'),
            ('cmdb_editor', 'CMDB Editor'),
            ('cmdb_admin', 'CMDB Admin'),
            # System admin role
            ('system_admin', '系统管理员'),
            # OpsAgent roles
            ('opsagent_viewer', 'OpsAgent Viewer'),
            ('opsagent_editor', 'OpsAgent Editor'),
            ('opsagent_admin', 'OpsAgent Admin'),
        ]
        created = 0
        for key, name in roles:
            _, c = IAMRole.objects.get_or_create(
                key=key,
                defaults={'name': name, 'is_system': True},
            )
            if c:
                created += 1
        self.stdout.write(f"  IAMRoles: {IAMRole.objects.count()} total, {created} new")

    # ── Role-Permission bindings ──────────────────────────────────

    def _seed_role_permissions(self):
        """Bind IAMPermissions to each IAMRole."""
        from iam.models.permission import IAMPermission, IAMRole, IAMRolePermission

        role_perm_map = {
            # ── OpsFlow ──────────────────────────────────────────
            'opsflow_viewer': [],
            'opsflow_editor': [
                'opsflow:designer:view',
                'opsflow:templates:view',
                'opsflow:template:create',
                'opsflow:executions:view',
                'opsflow:execution:run',
                'opsflow:approvals:view',
                'opsflow:knowledge:view',
                'opsflow:knowledge:create',
                'opsflow:webhooks:view',
            ],
            'opsflow_admin': [
                'opsflow:designer:view',
                'opsflow:templates:view',
                'opsflow:template:create',
                'opsflow:template:delete',
                'opsflow:template:publish',
                'opsflow:executions:view',
                'opsflow:execution:run',
                'opsflow:execution:cancel',
                'opsflow:approvals:view',
                'opsflow:knowledge:view',
                'opsflow:knowledge:create',
                'opsflow:knowledge:delete',
                'opsflow:webhooks:view',
                'opsflow:webhook:manage',
                'opsflow:schedule:manage',
                'opsflow:project:view',
            ],
            # ── ITSM ────────────────────────────────────────────
            'itsm_viewer': [
                'itsm:workflows:view',
                'itsm:skill_groups:view',
                'itsm:on_duty:view',
                'itsm:assign_rules:view',
                'itsm:escalation:view',
            ],
            'itsm_editor': [
                'itsm:ticket:create',
                'itsm:ticket:assign',
                'itsm:ticket:close',
                'itsm:workflows:view',
                'itsm:workflow:create',
                'itsm:workflow:design',
                'itsm:skill_groups:view',
                'itsm:skillgroup:manage',
                'itsm:on_duty:view',
                'itsm:duty:manage',
                'itsm:assign_rules:view',
                'itsm:escalation:view',
            ],
            'itsm_admin': [
                'itsm:ticket:create',
                'itsm:ticket:approve',
                'itsm:ticket:assign',
                'itsm:ticket:close',
                'itsm:workflows:view',
                'itsm:workflow:create',
                'itsm:workflow:design',
                'itsm:workflow:deploy',
                'itsm:workflow:delete',
                'itsm:skill_groups:view',
                'itsm:skillgroup:manage',
                'itsm:on_duty:view',
                'itsm:duty:manage',
                'itsm:assign_rules:view',
                'itsm:rule:manage',
                'itsm:escalation:view',
                'itsm:escalation:manage',
                'itsm:sla:edit',
            ],
            # ── CMDB ────────────────────────────────────────────
            'cmdb_viewer': [
                'cmdb:schema:view',
                'cmdb:sync:view',
                'cmdb:events:view',
            ],
            'cmdb_editor': [
                'cmdb:schema:view',
                'cmdb:schema:create',
                'cmdb:sync:view',
                'cmdb:sync:run',
                'cmdb:events:view',
                'cmdb:events:subscribe',
            ],
            'cmdb_admin': [
                'cmdb:schema:view',
                'cmdb:schema:create',
                'cmdb:schema:delete',
                'cmdb:sync:view',
                'cmdb:sync:run',
                'cmdb:events:view',
                'cmdb:events:subscribe',
                'cmdb:events:unsubscribe',
            ],
            # ── OpsAgent ──────────────────────────────────────────
            'opsagent_viewer': [
                'opsagent:console:view',
                'opsagent:sessions:view',
            ],
            'opsagent_editor': [
                'opsagent:console:view',
                'opsagent:console:execute',
                'opsagent:sessions:view',
            ],
            'opsagent_admin': [
                'opsagent:console:view',
                'opsagent:console:execute',
                'opsagent:sessions:view',
                'opsagent:session:delete',
            ],
            # ── System ─────────────────────────────────────────────
            'system_admin': [
                'system:user:manage',
                'system:dept:manage',
                'system:log:view',
                'system:file:manage',
            ],
        }

        created = 0
        for role_key, perm_codenames in role_perm_map.items():
            role = IAMRole.objects.filter(key=role_key).first()
            if not role:
                self.stdout.write(f"  ! Role not found: {role_key}")
                continue
            for codename in perm_codenames:
                perm = IAMPermission.objects.filter(codename=codename).first()
                if not perm:
                    self.stdout.write(f"  ! Permission not found: {codename}")
                    continue
                _, c = IAMRolePermission.objects.get_or_create(role=role, permission=perm)
                if c:
                    created += 1
        self.stdout.write(f"  IAMRolePermissions: {IAMRolePermission.objects.count()} total, {created} new")
