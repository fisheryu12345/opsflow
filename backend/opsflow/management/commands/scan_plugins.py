"""扫描插件目录并注册新插件

用法:
    python manage.py scan_plugins
"""
from django.core.management.base import BaseCommand

from opsflow.plugins.registry import refresh_plugins, PLUGIN_REGISTRY


class Command(BaseCommand):
    help = "Scan plugins directory and register new plugins"

    def handle(self, *args, **options):
        count = refresh_plugins()
        total = len(PLUGIN_REGISTRY)
        if count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Found {count} new plugin(s) — {total} total registered"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Plugins scanned successfully ({total} registered)"
            ))
