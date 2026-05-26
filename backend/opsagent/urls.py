# backend/opsagent/urls.py
from rest_framework.routers import DefaultRouter
from .views.audit import AuditRecordViewSet
from .views.session import SessionViewSet

router = DefaultRouter()
router.register(r'audit', AuditRecordViewSet, basename='ops-audit')
router.register(r'session', SessionViewSet, basename='ops-session')

urlpatterns = router.urls
