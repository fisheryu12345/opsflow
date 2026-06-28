from django.contrib import admin

from iam.models import (
    PermissionRequest, UserDirectPermission,
    BusinessGroup, Business, DeployEnvironment,
    Project, ProjectMember,
    BusinessMember, DeployEnvironmentPermission,
)


@admin.register(PermissionRequest)
class PermissionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'request_type', 'status', 'create_datetime', 'reviewed_at']
    list_filter = ['request_type', 'status']
    search_fields = ['user__username', 'user__name']


@admin.register(UserDirectPermission)
class UserDirectPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'menu', 'menu_button', 'granted_by']
    list_filter = ['user']


# ── Tenant models ──

@admin.register(BusinessGroup)
class BusinessGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'sort', 'is_active']
    search_fields = ['name', 'code']


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'group', 'is_active', 'db_alias', 'created_at']
    list_filter = ['is_active', 'group']
    search_fields = ['name', 'code']


@admin.register(DeployEnvironment)
class DeployEnvironmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'risk_level', 'sort', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']


# ── Project models (migrated from opsflow) ──

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'business']
    search_fields = ['name']


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'role', 'joined_at']
    list_filter = ['role']
    search_fields = ['project__name', 'user__username']


# ── Membership models ──

@admin.register(BusinessMember)
class BusinessMemberAdmin(admin.ModelAdmin):
    list_display = ['business', 'user', 'role', 'joined_at']
    list_filter = ['role']
    search_fields = ['business__name', 'user__username']


@admin.register(DeployEnvironmentPermission)
class DeployEnvironmentPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'environment', 'can_execute', 'granted_by', 'granted_at']
    list_filter = ['can_execute', 'environment']
    search_fields = ['user__username']
