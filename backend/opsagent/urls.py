from rest_framework.routers import DefaultRouter
from .views.audit import AuditRecordViewSet
from .views.session import SessionViewSet
from .views.run import TaskRunViewSet
from .views.environment import EnvironmentContextViewSet
from .views.memory import AgentMemoryViewSet

router = DefaultRouter()
router.register(r'audit', AuditRecordViewSet, basename='ops-audit')
router.register(r'session', SessionViewSet, basename='ops-session')
router.register(r'run', TaskRunViewSet, basename='ops-run')
router.register(r'environment', EnvironmentContextViewSet, basename='ops-environment')
router.register(r'memory', AgentMemoryViewSet, basename='ops-memory')

urlpatterns = router.urls
