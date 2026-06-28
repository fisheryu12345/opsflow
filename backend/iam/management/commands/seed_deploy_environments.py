"""Seed initial DeployEnvironment records: dev, staging, prod.

Run: python manage.py seed_deploy_environments
Idempotent — skips environments that already exist.
"""
from django.core.management.base import BaseCommand
from iam.models import DeployEnvironment

SEED_ENVIRONMENTS = [
    {'code': 'dev', 'name': 'Development', 'risk_level': 0, 'sort': 1},
    {'code': 'staging', 'name': 'Staging', 'risk_level': 50, 'sort': 2},
    {'code': 'prod', 'name': 'Production', 'risk_level': 100, 'sort': 3},
]


class Command(BaseCommand):
    help = 'Seed default DeployEnvironment records (dev/staging/prod)'

    def handle(self, **options):
        created_count = 0
        for env_data in SEED_ENVIRONMENTS:
            _, created = DeployEnvironment.objects.get_or_create(
                code=env_data['code'],
                defaults={
                    'name': env_data['name'],
                    'risk_level': env_data['risk_level'],
                    'sort': env_data['sort'],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {env_data['name']} ({env_data['code']})")
            else:
                self.stdout.write(f"  Already exists: {env_data['name']} ({env_data['code']})")

        self.stdout.write(self.style.SUCCESS(
            f'DeployEnvironment seeding complete (created {created_count})'
        ))
