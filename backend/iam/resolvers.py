"""Permission resolution functions for all sub-products.

These functions are the canonical way to check multi-tenant permissions.
All sub-product ViewSets should use these instead of directly querying
ProjectMember/BusinessMember tables.

Key principles:
- Business Admin inherits equivalent Project Admin access (no need for
  explicit ProjectMember records)
- Environment permissions are never inherited — must be explicitly granted
"""
from django.db.models import Q
from iam.models import Project, ProjectMember, Business, BusinessMember
from iam.models import DeployEnvironment, DeployEnvironmentPermission

ROLE_ORDER = {'viewer': 0, 'editor': 1, 'admin': 2}


def get_visible_projects(user) -> set:
    """Return all project IDs visible to the user

    Combines direct ProjectMember entries with inherited access from
    BusinessMember roles (Business Admin/Editor see all projects in their business).
    """
    if user.is_superuser:
        return set(Project.objects.values_list('id', flat=True))

    direct = set(ProjectMember.objects.filter(
        user=user
    ).values_list('project_id', flat=True))

    biz_ids = BusinessMember.objects.filter(
        user=user
    ).values_list('business_id', flat=True)
    biz_projects = set(Project.objects.filter(
        business_id__in=biz_ids
    ).values_list('id', flat=True))

    return direct | biz_projects


def get_visible_businesses(user) -> set:
    """Return all business IDs visible to the user"""
    if user.is_superuser:
        return set(Business.objects.values_list('id', flat=True))
    return set(BusinessMember.objects.filter(
        user=user
    ).values_list('business_id', flat=True))


def get_project_role(user, project_id) -> str | None:
    """Return the user's role (admin/editor/viewer) on a project.

    Checks direct ProjectMember first, then BusinessMember inheritance.
    Returns None if user has no access to the project.
    """
    if user.is_superuser:
        return 'admin'

    pm = ProjectMember.objects.filter(project_id=project_id, user=user).first()
    if pm:
        return pm.role

    try:
        project = Project.objects.only('business_id').get(id=project_id)
        if project.business_id:
            bm = BusinessMember.objects.filter(
                business_id=project.business_id, user=user
            ).first()
            if bm:
                return bm.role
    except Project.DoesNotExist:
        pass
    return None


def has_project_role(user, project_id, min_role='editor') -> bool:
    """Check if user has at least min_role on a project

    Checks both:
    1. Direct ProjectMember record
    2. Inherited from BusinessMember (cascades down to all projects)
    """
    if user.is_superuser:
        return True

    min_level = ROLE_ORDER.get(min_role, 0)

    # 1. Direct ProjectMember
    pm = ProjectMember.objects.filter(
        project_id=project_id, user=user
    ).first()
    if pm and ROLE_ORDER.get(pm.role, -1) >= min_level:
        return True

    # 2. BusinessMember inheritance
    try:
        project = Project.objects.only('business_id').get(id=project_id)
        if project.business_id:
            bm = BusinessMember.objects.filter(
                business_id=project.business_id, user=user
            ).first()
            if bm and ROLE_ORDER.get(bm.role, -1) >= min_level:
                return True
    except Project.DoesNotExist:
        pass

    return False


def has_business_role(user, business_id, min_role='editor') -> bool:
    """Check if user has at least min_role in a business"""
    if user.is_superuser:
        return True

    min_level = ROLE_ORDER.get(min_role, 0)
    bm = BusinessMember.objects.filter(
        business_id=business_id, user=user
    ).first()
    return bm is not None and ROLE_ORDER.get(bm.role, -1) >= min_level


def can_execute_in_environment(user, environment_id, project_id=None) -> bool:
    """Check if user can execute operations in given environment

    Two-step check:
    1. User must have explicit DeployEnvironmentPermission with can_execute=True
    2. For high-risk environments (prod, risk_level >= 100), user must also
       have at least Editor role on the project (if project_id provided)
    """
    # 1. Explicit environment execution permission
    if not DeployEnvironmentPermission.objects.filter(
        user=user, environment_id=environment_id, can_execute=True
    ).exists():
        return False

    # 2. High-risk environment: require project editor+
    env = DeployEnvironment.objects.get(id=environment_id)
    if env.risk_level >= 100 and project_id is not None:
        if not has_project_role(user, project_id, min_role='editor'):
            return False

    return True


def get_visible_operation_records(user):
    """Filter operation records to user's visible businesses

    Business Admin sees records of their businesses. Superuser sees all.
    Uses lazy import to avoid circular dependency.
    """
    from opsflow.models import OperationRecord
    if user.is_superuser:
        return OperationRecord.objects.all()
    biz_ids = get_visible_businesses(user)
    return OperationRecord.objects.filter(business_id__in=biz_ids)


def get_user_project_ids(user):
    """Legacy compat — returns list of visible project IDs"""
    return list(get_visible_projects(user))
