from django.urls import path
from rest_framework.routers import DefaultRouter

from iam.views import (
    PermissionRequestViewSet, UserDirectPermissionViewSet,
    BusinessGroupViewSet, BusinessViewSet,
    DeployEnvironmentViewSet, IamProjectViewSet,
    search_users, my_permissions,
)
# RBAC views migrated from dvadmin.system.views
from iam.views import (
    RoleViewSet, MenuViewSet, MenuButtonViewSet,
    MenuFieldViewSet, RoleMenuPermissionViewSet,
    RoleMenuButtonPermissionViewSet,
)

router = DefaultRouter()
# Existing IAM routes
router.register(r'requests', PermissionRequestViewSet, basename='permission-request')
router.register(r'direct-permissions', UserDirectPermissionViewSet, basename='direct-permission')
# Tenant management
router.register(r'business-groups', BusinessGroupViewSet, basename='iam-business-group')
router.register(r'businesses', BusinessViewSet, basename='iam-business')
router.register(r'environments', DeployEnvironmentViewSet, basename='iam-environment')
router.register(r'projects', IamProjectViewSet, basename='iam-project')
# RBAC routes (migrated from dvadmin/system)
router.register(r'role', RoleViewSet, basename='iam-role')
router.register(r'menu', MenuViewSet, basename='iam-menu')
router.register(r'menu_button', MenuButtonViewSet, basename='iam-menu-button')
router.register(r'column', MenuFieldViewSet, basename='iam-menu-field')
router.register(r'role_menu_permission', RoleMenuPermissionViewSet, basename='iam-role-menu-permission')
router.register(r'role_menu_button_permission', RoleMenuButtonPermissionViewSet, basename='iam-role-menu-button-permission')

urlpatterns = router.urls + [
    path('users/search/', search_users, name='user-search'),
    path('my_permissions/', my_permissions, name='my-permissions'),
]
