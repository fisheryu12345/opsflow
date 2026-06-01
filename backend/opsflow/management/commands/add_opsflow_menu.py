from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register opsflow frontend menus in the RBAC system (under 运维管理 catalog)'

    def handle(self, *args, **options):
        catalog, _ = Menu.objects.get_or_create(
            name="运维管理",
            web_path="/ops",
            defaults={
                "icon": "iconfont icon-cpu",
                "sort": 4,
                "is_link": False,
                "is_catalog": True,
                "component": "",
                "component_name": "",
                "status": True,
                "cache": False,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": None,
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Catalog: {catalog.name} (id={catalog.id})'))

        # --- 流程仪表盘 (Dashboard) ---
        dashboard_menu, created = Menu.objects.get_or_create(
            name="流程仪表盘",
            web_path="/opsflow/dashboard",
            component="apps/opsflow-dashboard/index",
            component_name="opsflowDashboard",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 2,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {dashboard_menu.name} (id={dashboard_menu.id})'
        ))

        # --- 运维编排 (template design) ---
        design, created = Menu.objects.get_or_create(
            name="运维编排",
            web_path="/opsflow",
            component="apps/opsflow/index",
            component_name="opsflow",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 3,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {design.name} (id={design.id})'
        ))

        # --- 流程执行 (execution management) ---
        exec_menu, created = Menu.objects.get_or_create(
            name="流程执行",
            web_path="/opsflow/executions",
            component="apps/opsflow-execution/index",
            component_name="opsflowExecutions",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 4,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {exec_menu.name} (id={exec_menu.id})'
        ))

        # --- 审计日志 ---
        log_menu, created = Menu.objects.get_or_create(
            name="审计日志",
            web_path="/opsflow/logs",
            component="apps/opsflow-log/index",
            component_name="opsflowLogs",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 5,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {log_menu.name} (id={log_menu.id})'
        ))

        # --- 知识库 ---
        knowledge_menu, created = Menu.objects.get_or_create(
            name="知识库",
            web_path="/opsflow/knowledge",
            component="apps/opsflow-knowledge/index",
            component_name="opsflowKnowledge",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 6,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {knowledge_menu.name} (id={knowledge_menu.id})'
        ))

        # --- 模板管理 ---
        template_menu, created = Menu.objects.get_or_create(
            name="模板管理",
            web_path="/opsflow/templates",
            component="apps/opsflow-template/index",
            component_name="opsflowTemplates",
            defaults={
                "icon": "iconfont icon-flow",
                "sort": 7,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {template_menu.name} (id={template_menu.id})'
        ))

        # --- 调度管理 ---
        schedule_menu, created = Menu.objects.get_or_create(
            name="调度管理",
            web_path="/ops/schedules",
            component="apps/opsflow-template/schedule",
            component_name="opsflowSchedules",
            defaults={
                "icon": "iconfont icon-time",
                "sort": 8,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {schedule_menu.name} (id={schedule_menu.id})'
        ))

        # --- 审批管理 (Approvals) ---
        approval_menu, created = Menu.objects.get_or_create(
            name="审批管理",
            web_path="/opsflow/approval",
            component="apps/opsflow-approval/index",
            component_name="opsflowApproval",
            defaults={
                "icon": "iconfont icon-check",
                "sort": 9,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {approval_menu.name} (id={approval_menu.id})'
        ))

        # --- Webhook 管理 (Webhook) ---
        webhook_menu, created = Menu.objects.get_or_create(
            name="Webhook 管理",
            web_path="/opsflow/webhooks",
            component="apps/opsflow-webhook/index",
            component_name="opsflowWebhooks",
            defaults={
                "icon": "iconfont icon-rizhi",
                "sort": 10,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {webhook_menu.name} (id={webhook_menu.id})'
        ))

        # --- 项目管理 (Project) ---
        project_menu, created = Menu.objects.get_or_create(
            name="项目管理",
            web_path="/opsflow/projects",
            component="apps/opsflow-project/index",
            component_name="opsflowProjects",
            defaults={
                "icon": "iconfont icon-configure",
                "sort": 11,
                "is_link": False,
                "is_catalog": False,
                "status": True,
                "cache": True,
                "visible": True,
                "is_iframe": False,
                "is_affix": False,
                "parent": catalog,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f'  {"Created" if created else "Found"} menu: {project_menu.name} (id={project_menu.id})'
        ))
