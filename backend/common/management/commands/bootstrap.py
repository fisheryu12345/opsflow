"""
Unified bootstrap command — one command to initialize all data for a new environment.

Usage:
    python manage.py bootstrap                     # Full: Phase 0+1+2
    python manage.py bootstrap --essential-only    # Phase 0+1 (system + reference)
    python manage.py bootstrap --demo-only         # Phase 2 only (demo data)
    python manage.py bootstrap --phase 0           # Single phase
    python manage.py bootstrap --force             # Force update demo data
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

PHASES = [
    ("0", "System Core (RBAC: users, roles, menus, dicts)"),
    ("1", "Reference Data (categories, knowledge, menus, CMDB, plugins, connectors)"),
    ("2", "Demo Data (mock templates, executions, ITSM, Neo4j topology)"),
]


class Command(BaseCommand):
    help = "Bootstrap all data for a new environment"

    def add_arguments(self, parser):
        parser.add_argument('--essential-only', action='store_true',
                            help='Only Phase 0+1 (system + reference, no demo data)')
        parser.add_argument('--demo-only', action='store_true',
                            help='Only Phase 2 (demo/mock data)')
        parser.add_argument('--phase', type=str, choices=['0', '1', '2'],
                            help='Run a single phase only')
        parser.add_argument('--force', action='store_true',
                            help='Force update existing demo data')

    def handle(self, *args, **options):
        essential_only = options.get('essential_only', False)
        demo_only = options.get('demo_only', False)
        single_phase = options.get('phase')
        force = options.get('force', False)

        self.stdout.write("=" * 60)
        self.stdout.write("OpsFlow Platform — Bootstrap")
        self.stdout.write("=" * 60)

        phases_to_run = []

        if single_phase:
            phases_to_run.append(single_phase)
        elif demo_only:
            phases_to_run.append("2")
        elif essential_only:
            phases_to_run.extend(["0", "1"])
        else:
            phases_to_run.extend(["0", "1", "2"])

        for phase in phases_to_run:
            self._run_phase(phase, force)

        self.stdout.write(self.style.SUCCESS("\nBootstrap complete!"))

    def _run_phase(self, phase, force):
        label = dict(PHASES).get(phase, f"Phase {phase}")
        self.stdout.write(f"\n{'─' * 60}")
        self.stdout.write(f"Phase {phase}: {label}")
        self.stdout.write(f"{'─' * 60}")

        if phase == "0":
            self._phase0()
        elif phase == "1":
            self._phase1()
        elif phase == "2":
            self._phase2(force)

    def _phase0(self):
        """System Core — RBAC + base data (python manage.py init)"""
        self.stdout.write(">>> Initializing RBAC system ...")
        call_command('init')
        self.stdout.write(self.style.SUCCESS("Phase 0 complete"))

    def _phase1(self):
        """Reference data — all seed_reference content"""
        self.stdout.write(">>> Seeding reference data ...")
        call_command('seed_reference')
        self.stdout.write(self.style.SUCCESS("Phase 1 complete"))

    def _phase2(self, force):
        """Demo data — mock templates, executions, ITSM, Neo4j"""
        self.stdout.write(">>> Generating demo data ...")

        force_flags = ['--force'] if force else []

        self.stdout.write("  → Django ORM mock data (opsflow, opsagent, cmdb, integration)")
        call_command('add_mock_data', *force_flags)

        self.stdout.write("  → ITSM workflow mock data")
        call_command('add_itsm_mock_data', *force_flags)

        self.stdout.write("  → Neo4j CMDB topology (small scale)")
        call_command('add_mock_neo4j', scale='small')

        self.stdout.write(self.style.SUCCESS("Phase 2 complete"))
