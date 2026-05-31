from django.contrib import admin

from iam.models import PermissionRequest, UserDirectPermission


@admin.register(PermissionRequest)
class PermissionRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'request_type', 'status', 'create_datetime', 'reviewed_at']
    list_filter = ['request_type', 'status']
    search_fields = ['user__username', 'user__name']


@admin.register(UserDirectPermission)
class UserDirectPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'menu', 'menu_button', 'granted_by']
    list_filter = ['user']
