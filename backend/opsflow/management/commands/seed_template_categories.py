"""初始化模板分类种子数据"""
from django.core.management.base import BaseCommand
from opsflow.models import TemplateCategory

CATEGORIES = [
    {"code": "server",           "name": "服务器管理",       "icon": "server",           "sort_order": 10},
    {"code": "virtualization",   "name": "虚拟化",           "icon": "virtualization",   "sort_order": 20},
    {"code": "storage",          "name": "存储管理",         "icon": "storage",          "sort_order": 30},
    {"code": "network",          "name": "网络管理",         "icon": "network",          "sort_order": 40},
    {"code": "security",         "name": "安全运维",         "icon": "security",         "sort_order": 50},
    {"code": "database",         "name": "数据库运维",       "icon": "database",         "sort_order": 60},
    {"code": "deploy",           "name": "应用发布",         "icon": "deploy",           "sort_order": 70},
    {"code": "backup",           "name": "备份与恢复",       "icon": "backup",           "sort_order": 80},
    {"code": "monitoring",       "name": "监控告警",         "icon": "monitoring",       "sort_order": 90},
    {"code": "inspection",       "name": "巡检与合规",       "icon": "inspection",       "sort_order": 100},
    {"code": "itsm",             "name": "IT服务管理",       "icon": "itsm",             "sort_order": 110},
    {"code": "automation",       "name": "自动化作业",       "icon": "automation",       "sort_order": 120},
    {"code": "notification",     "name": "通知告警",         "icon": "notification",     "sort_order": 130},
    {"code": "integration",      "name": "集成与API",        "icon": "integration",      "sort_order": 140},
    {"code": "maintenance",      "name": "系统维护",         "icon": "maintenance",      "sort_order": 150},
    {"code": "container",        "name": "容器与K8s",        "icon": "container",        "sort_order": 160},
    {"code": "infrastructure",   "name": "基础设施",         "icon": "infrastructure",   "sort_order": 170},
    {"code": "other",            "name": "其他",            "icon": "other",            "sort_order": 999},
]


class Command(BaseCommand):
    help = "初始化模板分类种子数据（18 个标准 IT 分类）"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for cat in CATEGORIES:
            obj, is_new = TemplateCategory.objects.update_or_create(
                code=cat["code"],
                defaults={
                    "name": cat["name"],
                    "icon": cat["icon"],
                    "sort_order": cat["sort_order"],
                    "is_active": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"模板分类种子数据完成: 新建 {created}, 更新 {updated}"
        ))
