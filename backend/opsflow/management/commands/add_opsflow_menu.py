from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register opsflow frontend menu in the RBAC system (under 运维管理 catalog)'

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

        obj, created = Menu.objects.get_or_create(
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
            f'  {"Created" if created else "Found"} menu: {obj.name} (id={obj.id})'
        ))
