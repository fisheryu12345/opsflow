"""Grant dev + staging DeployEnvironmentPermission to all active users.

Run: python manage.py grant_default_env_permissions

Idempotent — skips users who already have the permission.
Prod permission is intentionally NOT auto-granted; it must be manually assigned.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from iam.models import DeployEnvironment, DeployEnvironmentPermission

Users = get_user_model()


class Command(BaseCommand):
    help = 'Grant dev + staging execute permission to all active users'

    def handle(self, **options):
        try:
            dev = DeployEnvironment.objects.get(code='dev')
            staging = DeployEnvironment.objects.get(code='staging')
        except DeployEnvironment.DoesNotExist:
            self.stderr.write(
                'DeployEnvironment records not found. '
                'Run seed_deploy_environments first.'
            )
            return

        users = Users.objects.filter(is_active=True)
        granted_count = 0
        skipped_count = 0

        for user in users:
            for env in (dev, staging):
                _, created = DeployEnvironmentPermission.objects.get_or_create(
                    user=user, environment=env,
                    defaults={'can_execute': True},
                )
                if created:
                    granted_count += 1
                else:
                    skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Complete: {granted_count} granted, {skipped_count} already existed '
            f'across {users.count()} users for dev+staging'
        ))
        self.stdout.write(
            'Note: Production (prod) permission must be granted manually.'
        )
