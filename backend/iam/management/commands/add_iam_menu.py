from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register IAM menus in the RBAC system'

    def handle(self, *args, **options):
        catalog, _ = Menu.objects.get_or_create(
            name="权限管理",
            web_path="/iam",
            defaults={
                "icon": "iconfont icon-safe",
                "sort": 5,
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

        # --- IAM 首页 ---
        main, created = Menu.objects.get_or_create(
            name="权限申请",
            web_path="",
            component="apps/iam/index",
            component_name="iam",
            defaults={
                "icon": "iconfont icon-safe",
                "sort": 1,
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
            f'  {"Created" if created else "Found"} menu: {main.name} (id={main.id})'
        ))
