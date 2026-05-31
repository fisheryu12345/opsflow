from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.template_views import FlowTemplateViewSet
from .views.execution_views import FlowExecutionViewSet
from .views.log_views import OpsLogViewSet
from .views.knowledge_views import OpsKnowledgeViewSet
from .views.dashboard_views import dashboard_stats, dashboard_trend
from .views.schedule_views import SchedulePlanViewSet

router = DefaultRouter()
router.register(r'templates', FlowTemplateViewSet, basename='opsflow-template')
router.register(r'executions', FlowExecutionViewSet, basename='opsflow-execution')
router.register(r'logs', OpsLogViewSet, basename='opsflow-log')
router.register(r'knowledge', OpsKnowledgeViewSet, basename='opsflow-knowledge')
router.register(r'schedule-plans', SchedulePlanViewSet, basename='opsflow-schedule-plan')

urlpatterns = [
    path('dashboard/stats/', dashboard_stats, name='opsflow-dashboard-stats'),
    path('dashboard/trend/', dashboard_trend, name='opsflow-dashboard-trend'),
] + router.urls
