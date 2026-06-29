from rest_framework.routers import DefaultRouter

from django.urls import path
from rest_framework.routers import DefaultRouter

from iam.views import (
    PermissionRequestViewSet, UserDirectPermissionViewSet,
    BusinessGroupViewSet, BusinessViewSet,
    DeployEnvironmentViewSet, IamProjectViewSet,
    search_users,
)

router = DefaultRouter()
# Existing
router.register(r'requests', PermissionRequestViewSet, basename='permission-request')
router.register(r'direct-permissions', UserDirectPermissionViewSet, basename='direct-permission')
# Tenant management
router.register(r'business-groups', BusinessGroupViewSet, basename='iam-business-group')
router.register(r'businesses', BusinessViewSet, basename='iam-business')
router.register(r'environments', DeployEnvironmentViewSet, basename='iam-environment')
router.register(r'projects', IamProjectViewSet, basename='iam-project')

urlpatterns = router.urls + [
    path('users/search/', search_users, name='user-search'),
]
