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
        portal_menu = self._add_menu('运维门户',        '/portal',        'apps/portal/index',       'portal',       'iconfont icon-home',       40, catalog)
        cmdb_menu   = self._add_menu('配置管理(CMDB)',  '/cmdb',          'apps/cmdb/index',         'cmdb',         'iconfont icon-server',     41, catalog, is_catalog=True)
        itsm_menu   = self._add_menu('服务管理(ITSM)',  '/itsm',          'apps/itsm/index',         'itsm',         'iconfont icon-file-text',  42, catalog, is_catalog=True)
        monitor_menu = self._add_menu('监控告警',       '/monitor',       'apps/monitor/index',      'monitor',      'iconfont icon-alert',      43, catalog, is_catalog=True)
        job_menu    = self._add_menu('作业平台',        '/job-platform',  'apps/job-platform/index', 'job-platform', 'iconfont icon-play',       44, catalog, is_catalog=True)
        intg_menu   = self._add_menu('集成中心',        '/integration',   'apps/integration/index',  'integration',  'iconfont icon-connection',  45, catalog, is_catalog=True)
        openapi_menu = self._add_menu('开放 API',       '/open-api',      'apps/open-api/index',     'open-api',     'iconfont icon-key',        46, catalog, is_catalog=True)

        # ─── Group 3a: CMDB sub-menus ───
        self._add_menu('模型管理',  '/cmdb/model',     'apps/cmdb/index',     'cmdbModel',     'iconfont icon-server',   411, cmdb_menu)
        self._add_menu('实例管理',  '/cmdb/instance',  'apps/cmdb/index',     'cmdbInstance',  'iconfont icon-server',   412, cmdb_menu)
        self._add_menu('拓扑视图',  '/cmdb/topology',  'apps/cmdb/index',     'cmdbTopology',  'iconfont icon-server',   413, cmdb_menu)

        # ─── Group 3b: ITSM sub-menus ───
        self._add_menu('工单管理',  '/itsm/tickets',    'apps/itsm/index',     'itsmTickets',   'iconfont icon-file-text', 421, itsm_menu)
        self._add_menu('工作流',    '/itsm/workflows',  'apps/itsm/index',     'itsmWorkflows', 'iconfont icon-file-text', 422, itsm_menu)
        self._add_menu('SLA 策略',  '/itsm/sla',        'apps/itsm/index',     'itsmSla',       'iconfont icon-file-text', 423, itsm_menu)

        # ─── Group 3c: Monitor sub-menus ───
        self._add_menu('告警仪表盘', '/monitor/dashboard', 'apps/monitor/index', 'monitorDashboard', 'iconfont icon-alert', 431, monitor_menu)
        self._add_menu('告警事件',   '/monitor/alerts',    'apps/monitor/index', 'monitorAlerts',    'iconfont icon-alert', 432, monitor_menu)
        self._add_menu('告警规则',   '/monitor/rules',     'apps/monitor/index', 'monitorRules',     'iconfont icon-alert', 433, monitor_menu)

        # ─── Group 3d: Job Platform sub-menus ───
        self._add_menu('脚本管理',   '/job-platform/scripts',    'apps/job-platform/index', 'jobScripts',    'iconfont icon-play', 441, job_menu)
        self._add_menu('作业模板',   '/job-platform/templates',  'apps/job-platform/index', 'jobTemplates',  'iconfont icon-play', 442, job_menu)
        self._add_menu('执行记录',   '/job-platform/executions', 'apps/job-platform/index', 'jobExecutions', 'iconfont icon-play', 443, job_menu)
        self._add_menu('定时作业',   '/job-platform/cron',       'apps/job-platform/index', 'jobCron',       'iconfont icon-play', 444, job_menu)

        # ─── Group 3e: Integration sub-menus ───
        self._add_menu('连接器定义', '/integration/definitions',  'apps/integration/index', 'intgDefinitions', 'iconfont icon-connection', 451, intg_menu)
        self._add_menu('连接器实例', '/integration/instances',    'apps/integration/index', 'intgInstances',   'iconfont icon-connection', 452, intg_menu)
        self._add_menu('调用日志',   '/integration/logs',         'apps/integration/index', 'intgLogs',        'iconfont icon-connection', 453, intg_menu)

        # ─── Group 3f: OpenAPI sub-menus ───
        self._add_menu('应用管理',   '/open-api/apps',     'apps/open-api/index', 'openapiApps',     'iconfont icon-key', 461, openapi_menu)
        self._add_menu('Webhook',    '/open-api/webhooks', 'apps/open-api/index', 'openapiWebhooks', 'iconfont icon-key', 462, openapi_menu)

        self.stdout.write(self.style.SUCCESS(
            '\nAll platform menus registered successfully.\n'
            '  Group 1: OpsAgent (sort 10-11)\n'
            '  Group 2: OpsFlow Engine (sort 20-29)\n'
            '  Group 3: Phase 1 Core Modules (sort 40-46)\n'
            '    - CMDB sub-menus (41x)\n'
            '    - ITSM sub-menus (42x)\n'
            '    - Monitor sub-menus (43x)\n'
            '    - Job Platform sub-menus (44x)\n'
            '    - Integration sub-menus (45x)\n'
            '    - OpenAPI sub-menus (46x)'
        ))

    def _add_menu(self, name, web_path, component, component_name, icon, sort, parent, is_catalog=False):
        menu, created = Menu.objects.update_or_create(
            name=name,
            web_path=web_path,
            component=component,
            component_name=component_name,
            defaults={
                'icon': icon,
                'sort': sort,
                'is_link': False,
                'is_catalog': is_catalog,
                'status': True,
                'cache': True,
                'visible': True,
                'is_iframe': False,
                'is_affix': False,
                'parent': parent,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Updated"} menu: {menu.name} (sort={sort}, id={menu.id})'
        ))
