"""Seed IAMMenu records (snapshot of current DB state).

Run: python manage.py seed_iam_menu

Idempotent via get_or_create(component_name). Matches existing
opsflow_iam_menu table records exactly.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed IAMMenu navigation menus (based on current DB)"

    def handle(self, *args, **options):
        from iam.models.page_config import IAMMenu

        menus = [
            {"name": "系统管理", "name_en": "System Config", "icon": "ele-Cpu", "sort": 0, "web_path": "/config", "component": "system/config/index", "component_name": "config", "app": "system", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "配置管理", "name_en": "CMDB", "icon": "iconfont icon-shuxingtu", "sort": 1, "web_path": "/cmdb", "component": "apps/cmdb/index", "component_name": "cmdb", "app": "cmdb", "visible": True, "status": True, "cache": True, "is_catalog": False, "dept_belong_id": ""},
            {"name": "资产管理", "name_en": "Agent", "icon": "iconfont icon-shoujidiannao", "sort": 1, "web_path": "/agent", "component": "apps/agent/index", "component_name": "agent", "app": "agent_app", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "附件管理", "name_en": "Attachments", "icon": "iconfont icon-file", "sort": 3, "web_path": "/file", "component": "system/fileList/index", "component_name": "file", "app": "system", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "运维控制台", "name_en": "OpsAgent", "icon": "iconfont icon-dianhua", "sort": 6, "web_path": "/opsagent", "component": "apps/opsagent/index", "component_name": "opsagent", "app": "system", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "监控平台", "name_en": "Monitor", "icon": "iconfont icon-zhongduancanshuchaxun", "sort": 10, "web_path": "/monitor", "component": "apps/monitor/index", "component_name": "monitor", "app": "monitor", "visible": True, "status": True, "cache": True, "is_catalog": False, "dept_belong_id": "1"},
            {"name": "集成中心", "name_en": "Integration Hub", "icon": "iconfont icon-step", "sort": 11, "web_path": "/interhub", "component": "apps/integration/index", "component_name": "integration", "app": "integration", "visible": True, "status": True, "cache": True, "is_catalog": False, "dept_belong_id": "1"},
            {"name": "作业平台", "name_en": "Job Platform", "icon": "iconfont icon-siweidaotu", "sort": 12, "web_path": "/job-platform", "component": "apps/job-platform/index", "component_name": "job-platform", "app": "job_platform", "visible": True, "status": True, "cache": True, "is_catalog": False, "dept_belong_id": "1"},
            {"name": "统一接口", "name_en": "Open-api", "icon": "iconfont icon-caozuorizhi", "sort": 13, "web_path": "/open-api", "component": "apps/open-api/index", "component_name": "open-api", "app": "open_api", "visible": True, "status": True, "cache": True, "is_catalog": False, "dept_belong_id": "1"},
            {"name": "Message Center", "name_en": "信息中心", "icon": "iconfont icon-xiaoxizhongxin", "sort": 14, "web_path": "/messageCenter", "component": "system/messageCenter/index", "component_name": "messageCenter", "app": "system", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "IAM", "name_en": "IAM", "icon": "iconfont icon-lock", "sort": 35, "web_path": "/iam", "component": "apps/iam/index", "component_name": "iam", "app": "iam", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "ITSM", "name_en": "", "icon": "iconfont icon-barcode-qr", "sort": 40, "web_path": "/itsm", "component": "apps/itsm/index", "component_name": "itsm", "app": "itsm", "visible": True, "status": True, "cache": False, "is_catalog": False},
            {"name": "OpsFlow", "name_en": "", "icon": "iconfont icon-diannao1", "sort": 50, "web_path": "/opsflow", "component": "apps/opsflow/index", "component_name": "opsflow", "app": "opsflow", "visible": True, "status": True, "cache": False, "is_catalog": False},
        ]

        created = 0
        for m in menus:
            dept = m.pop("dept_belong_id", "")
            obj, is_new = IAMMenu.objects.get_or_create(
                component_name=m["component_name"],
                defaults={**m, "dept_belong_id": dept or None},
            )
            if is_new:
                created += 1
            elif dept and str(obj.dept_belong_id) != dept:
                obj.dept_belong_id = dept
                obj.save(update_fields=["dept_belong_id"])

        self.stdout.write(f"  IAMMenus: {IAMMenu.objects.count()} total, {created} new")
        self.stdout.write(self.style.SUCCESS("IAMMenu seed complete!"))
