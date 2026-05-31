from rest_framework.routers import DefaultRouter

from iam.views import PermissionRequestViewSet, UserDirectPermissionViewSet

router = DefaultRouter()
router.register(r'requests', PermissionRequestViewSet, basename='permission-request')
router.register(r'direct-permissions', UserDirectPermissionViewSet, basename='direct-permission')

urlpatterns = router.urls
