from django.urls import path
from rest_framework.routers import DefaultRouter

from iam.views import (
    PermissionRequestViewSet, UserDirectPermissionViewSet,
    BusinessGroupViewSet, BusinessViewSet,
    DeployEnvironmentViewSet, IamProjectViewSet,
    search_users, my_permissions, my_full_permissions, page_permissions, permission_catalog,
)
from iam.views import (
    RoleViewSet, MenuViewSet,
)

router = DefaultRouter()
router.register(r'requests', PermissionRequestViewSet, basename='permission-request')
router.register(r'direct-permissions', UserDirectPermissionViewSet, basename='direct-permission')
router.register(r'business-groups', BusinessGroupViewSet, basename='iam-business-group')
router.register(r'businesses', BusinessViewSet, basename='iam-business')
router.register(r'environments', DeployEnvironmentViewSet, basename='iam-environment')
router.register(r'projects', IamProjectViewSet, basename='iam-project')
router.register(r'role', RoleViewSet, basename='iam-role')
router.register(r'menu', MenuViewSet, basename='iam-menu')

urlpatterns = router.urls + [
    path('users/search/', search_users, name='user-search'),
    path('my_permissions/', my_permissions, name='my-permissions'),
    path('my-full-permissions/', my_full_permissions, name='my-full-permissions'),
    path('page-permissions/', page_permissions, name='page-permissions'),
    path('permission-catalog/', permission_catalog, name='permission-catalog'),
]
