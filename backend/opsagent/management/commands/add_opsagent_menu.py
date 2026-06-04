"""
[DEPRECATED] Use unified command instead: python manage.py add_app_menus

This file is kept for backward compatibility only.
All menu registration has been consolidated into
common/management/commands/add_app_menus.py
"""

from django.core.management.base import BaseCommand
from dvadmin.system.models import Menu


class Command(BaseCommand):
    help = '[DEPRECATED] Use "python manage.py add_app_menus" instead'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            '╔══════════════════════════════════════════════════════════╗\n'
            '║  [DEPRECATED] This command is deprecated.              ║\n'
            '║  Use the unified command instead:                      ║\n'
            '║                                                         ║\n'
            '║      python manage.py add_app_menus                     ║\n'
            '║                                                         ║\n'
            '║  All platform menus are registered through a single     ║\n'
            '║  command under the "运维平台" catalog.                  ║\n'
            '╚══════════════════════════════════════════════════════════╝'
        ))
        # Delegate to the unified command
        from common.management.commands.add_app_menus import Command as UnifiedCmd
        UnifiedCmd().handle(*args, **options)
