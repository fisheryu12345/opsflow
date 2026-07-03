"""Seed: initialize IAM permission models (data already migrated, clean one-shot)
Run: python manage.py seed_iam_unified
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed unified IAM permission models (one-shot initialization)"

    def handle(self, *args, **options):
        self._create_users()
        self._init_default_role()
        self._assign_default_role_to_users()
        self.stdout.write(self.style.SUCCESS("Unified RBAC seed complete!"))

    def _create_users(self):
        """Create default admin and test user if they don't exist."""
        from django.contrib.auth import get_user_model
        from iam.models.permission import IAMRole, IAMUserRole
        from django.db import connection

        User = get_user_model()
        users_to_create = []

        if not User.objects.filter(is_superuser=True).exists():
            admin = User.objects.create_superuser(
                username='opsflowadmin', password='admin123456',
                name='Super Admin', email='admin@opsflow.local',
            )
            self.stdout.write(f"  + Superuser: {admin.username} / admin123456")
            users_to_create.append((admin, ['system_admin', 'opsflow_admin']))

        test_user = User.objects.filter(username='testuser').first()
        if not test_user:
            test_user = User.objects.create_user(
                username='testuser', password='test1234',
                name='Test User', email='test@opsflow.local',
            )
            self.stdout.write(f"  + Test user: {test_user.username} / test1234")
            users_to_create.append((test_user, ['opsflow_editor', 'itsm_editor', 'cmdb_editor']))
        else:
            self.stdout.write(f"  + Test user exists, skipping role assignment")

        # Assign roles via ORM
        for user, role_keys in users_to_create:
            roles = IAMRole.objects.filter(key__in=role_keys)
            existing = set(IAMUserRole.objects.filter(
                user=user.id
            ).values_list('role_id', flat=True))
            for role in roles:
                if role.id not in existing:
                    IAMUserRole.objects.create(user=user.id, role=role)
                    self.stdout.write(f"    → {role.name}")

    def _init_default_role(self):
        from iam.models.permission import IAMPermission, IAMRole, IAMRolePermission

        default_role, created = IAMRole.objects.get_or_create(
            key='authenticated',
            defaults={'name': 'Authenticated User', 'is_system': True},
        )
        self.stdout.write(f"  Default role {'created' if created else 'exists'}: {default_role.key}")

        base_perms = [
            ('portal:dashboard:view', '查看仪表盘', 'portal'),
            ('portal:personal:settings', '个人设置', 'portal'),
            ('portal:access', '访问门户', 'portal'),
        ]
        for codename, label, app in base_perms:
            perm, _ = IAMPermission.objects.get_or_create(
                codename=codename,
                defaults={'label': label, 'app': app, 'scope': 'platform'},
            )
            IAMRolePermission.objects.get_or_create(role=default_role, permission=perm)
        self.stdout.write(f"  Default role granted {len(base_perms)} base permissions")

    def _assign_default_role_to_users(self):
        from django.contrib.auth import get_user_model
        from iam.models.permission import IAMRole, IAMUserRole

        default_role = IAMRole.objects.filter(key='authenticated').first()
        if not default_role:
            self.stdout.write("  ! Default role not found, skip")
            return

        User = get_user_model()
        assigned = 0
        existing_ids = set(IAMUserRole.objects.filter(
            role=default_role
        ).values_list('user', flat=True))
        for u in User.objects.exclude(id__in=existing_ids):
            IAMUserRole.objects.create(user=u.id, role=default_role)
            assigned += 1
        self.stdout.write(f"  Default role assigned to {assigned} users")
