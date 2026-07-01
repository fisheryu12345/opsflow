"""Seed: initialize IAM permission models (data already migrated, clean one-shot)
Run: python manage.py seed_iam_unified
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed unified IAM permission models (one-shot initialization)"

    def handle(self, *args, **options):
        self._init_default_role()
        self._assign_default_role_to_users()
        self.stdout.write(self.style.SUCCESS("Unified RBAC seed complete!"))

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
        User = get_user_model()

        default_role = IAMRole.objects.filter(key='authenticated').first()
        if not default_role:
            self.stdout.write("  ! Default role not found, skip")
            return

        assigned = 0
        for u in User.objects.filter(iam_user_roles__isnull=True):
            IAMUserRole.objects.get_or_create(user=u, role=default_role)
            assigned += 1
        self.stdout.write(f"  Default role assigned to {assigned} users")
