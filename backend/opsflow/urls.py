from rest_framework.routers import DefaultRouter

from .views.template_views import FlowTemplateViewSet
from .views.execution_views import FlowExecutionViewSet
from .views.log_views import OpsLogViewSet
from .views.knowledge_views import OpsKnowledgeViewSet

router = DefaultRouter()
router.register(r'templates', FlowTemplateViewSet, basename='opsflow-template')
router.register(r'executions', FlowExecutionViewSet, basename='opsflow-execution')
router.register(r'logs', OpsLogViewSet, basename='opsflow-log')
router.register(r'knowledge', OpsKnowledgeViewSet, basename='opsflow-knowledge')

urlpatterns = router.urls
