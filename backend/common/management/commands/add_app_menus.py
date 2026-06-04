"""
Seed menu entries for all new Phase 1 apps in the RBAC system

Usage:
    python manage.py add_app_menus

Creates catalog + menu items for integration, cmdb, itsm, monitor,
job_platform, portal, and open_api modules.
"""

from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = 'Register Phase 1 app menus in the RBAC system'

    def handle(self, *args, **options):
        # ─── Main catalog: 运维平台 ───
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

        # ─── 1. Portal 运维门户 ───
        self._add_menu('运维门户', '/portal', 'apps/portal/index', 'portal',
                       'iconfont icon-home', 1, catalog)

        # ─── 2. CMDB ───
        self._add_menu('配置管理(CMDB)', '/cmdb', 'apps/cmdb/index', 'cmdb',
                       'iconfont icon-server', 2, catalog)

        # ─── 3. ITSM ───
        self._add_menu('服务管理(ITSM)', '/itsm', 'apps/itsm/index', 'itsm',
                       'iconfont icon-file-text', 3, catalog)

        # ─── 4. Monitor ───
        self._add_menu('监控告警', '/monitor', 'apps/monitor/index', 'monitor',
                       'iconfont icon-alert', 4, catalog)

        # ─── 5. Job Platform ───
        self._add_menu('作业平台', '/job-platform', 'apps/job-platform/index', 'job-platform',
                       'iconfont icon-play', 5, catalog)

        # ─── 6. Integration ───
        self._add_menu('集成中心', '/integration', 'apps/integration/index', 'integration',
                       'iconfont icon-connection', 6, catalog)

        # ─── 7. Open API ───
        self._add_menu('开放 API', '/open-api', 'apps/open-api/index', 'open-api',
                       'iconfont icon-key', 7, catalog)

        self.stdout.write(self.style.SUCCESS('\nAll Phase 1 app menus registered successfully.'))

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
            f'  {"Created" if created else "Found"} menu: {menu.name} (id={menu.id})'
        ))
