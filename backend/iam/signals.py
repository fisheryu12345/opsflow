"""Signal handlers — auto-sync dvadmin Roles when IAM membership roles change.

When a user is added/removed/role-changed in BusinessMember or ProjectMember,
we automatically assign/remove the corresponding dvadmin Role so that
Menu/MenuButton permissions follow the IAM role hierarchy.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from iam.models import BusinessMember, ProjectMember

logger = logging.getLogger(__name__)

# IAM role → dvadmin Role key mapping
IAM_TO_DVADMIN_ROLE = {
    'admin': 'itsm_admin',
    'editor': 'itsm_editor',
    'viewer': 'itsm_viewer',
}

# All possible dvadmin role keys for ITSM
ALL_ITSM_ROLE_KEYS = set(IAM_TO_DVADMIN_ROLE.values())


def _sync_dvadmin_role(user):
    """Sync user's dvadmin Roles to match their IAM memberships.

    Computes the highest IAM role the user has across all BusinessMembers
    and ProjectMembers, then assigns the corresponding dvadmin Role.
    Lower roles are removed.
    """
    from dvadmin.system.models import Role

    # Find the highest IAM role across all memberships
    highest = 'viewer'
    role_order = {'viewer': 0, 'editor': 1, 'admin': 2}

    for m in BusinessMember.objects.filter(user=user):
        if role_order.get(m.role, -1) > role_order[highest]:
            highest = m.role
    for m in ProjectMember.objects.filter(user=user):
        if role_order.get(m.role, -1) > role_order[highest]:
            highest = m.role

    # Determine which dvadmin Role to assign
    target_key = IAM_TO_DVADMIN_ROLE.get(highest)
    if not target_key:
        return

    target_role = Role.objects.filter(key=target_key, status=1).first()
    if not target_role:
        logger.warning("dvadmin Role '%s' not found — run seed_itsm_permissions", target_key)
        return

    # Assign target role, remove other ITSM roles
    user_roles = set(user.role.values_list('key', flat=True))
    if target_key not in user_roles:
        user.role.add(target_role)
        logger.info("User %s: granted dvadmin Role '%s' (IAM highest=%s)", user.username, target_key, highest)

    for key in ALL_ITSM_ROLE_KEYS - {target_key}:
        if key in user_roles:
            user.role.remove(*Role.objects.filter(key=key))
            logger.info("User %s: revoked dvadmin Role '%s'", user.username, key)


@receiver(post_save, sender=BusinessMember)
def on_business_member_save(sender, instance, **kwargs):
    _sync_dvadmin_role(instance.user)


@receiver(post_delete, sender=BusinessMember)
def on_business_member_delete(sender, instance, **kwargs):
    _sync_dvadmin_role(instance.user)


@receiver(post_save, sender=ProjectMember)
def on_project_member_save(sender, instance, **kwargs):
    _sync_dvadmin_role(instance.user)


@receiver(post_delete, sender=ProjectMember)
def on_project_member_delete(sender, instance, **kwargs):
    _sync_dvadmin_role(instance.user)
