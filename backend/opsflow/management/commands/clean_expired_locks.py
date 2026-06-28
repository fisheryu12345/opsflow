"""Clean expired template editing locks — heartbeat > 60s old.

Idempotent — safe to run on any interval.
Recommended: run via scheduler_service or cron every minute.

Usage:
    python manage.py clean_expired_locks
"""
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Clean expired template editing locks"

    def handle(self, **options):
        from opsflow.models import TemplateLock

        cutoff = timezone.now() - timedelta(seconds=60)
        deleted, _ = TemplateLock.objects.filter(heartbeat__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Cleaned {deleted} expired lock(s)"))
