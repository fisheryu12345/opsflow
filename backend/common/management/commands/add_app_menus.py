"""
Unified RBAC menu registration for all platform apps

Usage:
    python manage.py add_app_menus

Registers all frontend menu entries under a single "运维平台" catalog,
covering opsflow, opsagent, and all Phase 1 modules (integration, cmdb,
itsm, monitor, job_platform, portal, open_api).

This replaces the old per-app commands:
  - opsflow/management/commands/add_opsflow_menu.py  (DEPRECATED)
  - opsagent/management/commands/add_opsagent_menu.py (DEPRECATED)
"""

from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register all platform menu entries in the RBAC system'

    def handle(self, *args, **options):
        # ─── Root catalog: 运维平台 ───
        catalog, _ = Menu.objects.get_or_create(
            name='运维平台',
            web_path='/apps',
            defaults={
                'icon': 'iconfont icon-CPU',
                'sort': 4,
                'is_link': False,
                'is_catalog': True,
                'component': '',
                'component_name': '',
                'status': True,
                'cache': False,
                'visible': True,
                'is_iframe': False,
                'is_affix': False,
                'parent': None,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Catalog: {catalog.name} (id={catalog.id})'))

        # ════════════════════════════════════════════
        #  Group 1: OpsAgent (AI 运维助手)
        # ════════════════════════════════════════════
        self._add_menu('运维控制台',     '/ops/console',    'apps/opsagent/Console',   'ConsoleView',   'iconfont icon-cpu',   10, catalog)
        self._add_menu('会话历史',       '/ops/sessions',   'apps/opsagent/Sessions',  'SessionsView',  'iconfont icon-time',  11, catalog)

        # ════════════════════════════════════════════
        #  Group 2: OpsFlow 编排引擎
        # ════════════════════════════════════════════
        self._add_menu('流程仪表盘',     '/opsflow/dashboard',  'apps/opsflow-dashboard/index',  'opsflowDashboard',  'iconfont icon-flow',     20, catalog)
        self._add_menu('运维编排',       '/opsflow',            'apps/opsflow/index',            'opsflow',           'iconfont icon-flow',     21, catalog)
        self._add_menu('流程执行',       '/opsflow/executions',  'apps/opsflow-execution/index',  'opsflowExecutions', 'iconfont icon-flow',     22, catalog)
        self._add_menu('审计日志',       '/opsflow/logs',       'apps/opsflow-log/index',        'opsflowLogs',       'iconfont icon-flow',     23, catalog)
        self._add_menu('知识库',         '/opsflow/knowledge',  'apps/opsflow-knowledge/index',  'opsflowKnowledge',  'iconfont icon-flow',     24, catalog)
        self._add_menu('模板管理',       '/opsflow/templates',  'apps/opsflow-template/index',   'opsflowTemplates',  'iconfont icon-flow',     25, catalog)
        self._add_menu('调度管理',       '/ops/schedules',      'apps/opsflow-template/schedule', 'opsflowSchedules', 'iconfont icon-time',     26, catalog)
        self._add_menu('审批管理',       '/opsflow/approval',   'apps/opsflow-approval/index',   'opsflowApproval',   'iconfont icon-check',    27, catalog)
        self._add_menu('Webhook 管理',   '/opsflow/webhooks',   'apps/opsflow-webhook/index',    'opsflowWebhooks',   'iconfont icon-rizhi',    28, catalog)
        self._add_menu('项目管理',       '/opsflow/projects',   'apps/opsflow-project/index',    'opsflowProjects',   'iconfont icon-configure', 29, catalog)

        # ════════════════════════════════════════════
        #  Group 3: Phase 1 — 核心运维模块
        # ════════════════════════════════════════════
        self._add_menu('运维门户',        '/portal',        'apps/portal/index',       'portal',       'iconfont icon-home',       40, catalog)
        self._add_menu('配置管理(CMDB)',  '/cmdb',          'apps/cmdb/index',         'cmdb',         'iconfont icon-server',     41, catalog)
        self._add_menu('服务管理(ITSM)',  '/itsm',          'apps/itsm/index',         'itsm',         'iconfont icon-file-text',  42, catalog)
        self._add_menu('监控告警',        '/monitor',       'apps/monitor/index',      'monitor',      'iconfont icon-alert',      43, catalog)
        self._add_menu('作业平台',        '/job-platform',  'apps/job-platform/index', 'job-platform', 'iconfont icon-play',       44, catalog)
        self._add_menu('集成中心',        '/integration',   'apps/integration/index',  'integration',  'iconfont icon-connection',  45, catalog)
        self._add_menu('开放 API',        '/open-api',      'apps/open-api/index',     'open-api',     'iconfont icon-key',        46, catalog)

        self.stdout.write(self.style.SUCCESS(
            '\nAll platform menus registered successfully.\n'
            '  Group 1: OpsAgent (sort 10-11)\n'
            '  Group 2: OpsFlow Engine (sort 20-29)\n'
            '  Group 3: Phase 1 Core Modules (sort 40-46)'
        ))

    def _add_menu(self, name, web_path, component, component_name, icon, sort, parent):
        menu, created = Menu.objects.get_or_create(
            name=name,
            web_path=web_path,
            component=component,
            component_name=component_name,
            defaults={
                'icon': icon,
                'sort': sort,
                'is_link': False,
                'is_catalog': False,
                'status': True,
                'cache': True,
                'visible': True,
                'is_iframe': False,
                'is_affix': False,
                'parent': parent,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {menu.name} (sort={sort}, id={menu.id})'
        ))
