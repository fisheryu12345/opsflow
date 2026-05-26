from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register opsagent frontend menus in the RBAC system'

    def handle(self, *args, **options):
        catalog, created = Menu.objects.get_or_create(
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
        self.stdout.write(self.style.SUCCESS(
            f'{"Created" if created else "Found"} catalog: {catalog.name} (id={catalog.id})'
        ))

        children = [
            {
                "name": "运维控制台",
                "icon": "iconfont icon-cpu",
                "sort": 1,
                "web_path": "/ops/console",
                "component": "apps/opsagent/Console",
                "component_name": "ConsoleView",
            },
            {
                "name": "会话历史",
                "icon": "iconfont icon-time",
                "sort": 2,
                "web_path": "/ops/sessions",
                "component": "apps/opsagent/Sessions",
                "component_name": "SessionsView",
            },
        ]

        for child in children:
            obj, created = Menu.objects.get_or_create(
                name=child["name"],
                web_path=child["web_path"],
                component=child["component"],
                component_name=child["component_name"],
                defaults={
                    "icon": child["icon"],
                    "sort": child["sort"],
                    "is_link": False,
                    "is_catalog": False,
                    "status": True,
                    "cache": False,
                    "visible": True,
                    "is_iframe": False,
                    "is_affix": False,
                    "parent": catalog,
                },
            )
            self.stdout.write(self.style.SUCCESS(
                f'  {"Created" if created else "Found"} menu: {child["name"]} (id={obj.id})'
            ))
