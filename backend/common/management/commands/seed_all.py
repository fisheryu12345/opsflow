"""Master seed orchestrator — runs all sub-app seed commands in dependency order.

Usage:
    python manage.py seed_all    # Run all seed commands
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


SEED_COMMANDS = [
    # Layer 1: IAM + dvadmin (base infrastructure)
    ('iam', 'seed_deploy_environments'),
    # Layer 2: Sub-product seed commands
    ('opsflow', 'seed_opsflow'),
    ('opsflow', 'seed_template_presets'),
    ('cmdb', 'seed_cmdb'),
    ('cmdb', 'seed_dr_models'),
    ('cmdb', 'seed_cmdb_mock'),
    ('monitor', 'seed_monitor'),
    ('integration', 'seed_integration'),
    ('itsm', 'seed_itsm'),
    ('opsagent', 'seed_opsagent'),
]


class Command(BaseCommand):
    help = "Run all sub-app seed commands in dependency order"

    def add_arguments(self, parser):
        parser.add_argument('--skip', nargs='+', help='Skip specific commands (app.command_name)')

    def handle(self, *args, **options):
        skip_set = set(options.get('skip', []) or [])
        all_ok = True
        for app, cmd_name in SEED_COMMANDS:
            key = f'{app}.{cmd_name}'
            if key in skip_set:
                self.stdout.write(f'[{key}] SKIPPED')
                continue
            try:
                call_command(cmd_name)
                self.stdout.write(self.style.SUCCESS(f'[{key}] OK'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[{key}] FAILED: {e}'))
                all_ok = False
        if all_ok:
            self.stdout.write(self.style.SUCCESS('\nAll seed commands completed successfully!'))
        else:
            self.stdout.write(self.style.WARNING('\nSome seed commands failed. Check errors above.'))
