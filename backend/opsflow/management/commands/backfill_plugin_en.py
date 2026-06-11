"""为所有插件自动补齐 name_en / description_en / form_schema name_en

用法:
    python manage.py backfill_plugin_en
"""
import re
from django.core.management.base import BaseCommand
from opsflow.models import PluginMeta

_ABBR_MAP = {
    'esxi': 'ESXi', 'cmdb': 'CMDB', 'pmax': 'PMAX', 'vm': 'VM',
    'ip': 'IP', 'ssh': 'SSH', 'http': 'HTTP', 'https': 'HTTPS',
    'smtp': 'SMTP', 'tls': 'TLS', 'ssl': 'SSL', 'dns': 'DNS',
    'api': 'API', 'url': 'URL', 'json': 'JSON', 'html': 'HTML',
    'csv': 'CSV', 'yaml': 'YAML', 'xml': 'XML', 'cli': 'CLI',
    'ui': 'UI', 'id': 'ID', 'cpu': 'CPU', 'gb': 'GB', 'mb': 'MB',
}


def _snake_to_title(text: str) -> str:
    parts = text.replace('-', '_').split('_')
    return ' '.join(_ABBR_MAP.get(p.lower(), p.capitalize()) for p in parts)


class Command(BaseCommand):
    help = "Backfill empty name_en / description_en / form_schema name_en for all plugins"

    def handle(self, *args, **options):
        updated = 0
        for pm in PluginMeta.objects.all():
            dirty = False
            if not pm.name_en:
                pm.name_en = _snake_to_title(pm.code)
                dirty = True
            if not pm.description_en:
                pm.description_en = _snake_to_title(pm.code)
                dirty = True
            for item in pm.form_schema or []:
                if not item.get('name_en'):
                    item['name_en'] = _snake_to_title(item.get('tag_code', ''))
                    dirty = True
            if dirty:
                pm.save(update_fields=['name_en', 'description_en', 'form_schema'])
                updated += 1
                self.stdout.write(f"  {pm.code:35s} → {pm.name_en}")

        self.stdout.write(self.style.SUCCESS(f"Done. {updated} plugin(s) updated."))
