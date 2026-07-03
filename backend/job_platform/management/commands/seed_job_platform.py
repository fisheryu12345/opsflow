"""Seed job_platform built-in data — dangerous command rules."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed built-in dangerous command rules"

    def handle(self, *args, **options):
        from job_platform.services.dangerous_detector import sync_builtin_rules
        sync_builtin_rules()
        self.stdout.write(self.style.SUCCESS("内置高危规则同步完成"))
