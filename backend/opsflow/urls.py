from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.template_views import FlowTemplateViewSet
from .views.execution_views import FlowExecutionViewSet
from .views.log_views import OpsLogViewSet
from .views.knowledge_views import OpsKnowledgeViewSet
from .views.dashboard_views import (
    dashboard_stats, dashboard_trend, dashboard_schedule_stats,
    dashboard_top_templates, dashboard_user_activity,
    dashboard_status_distribution, dashboard_node_type_distribution,
)
from .views.schedule_views import SchedulePlanViewSet
from .views.plugin_views import PluginViewSet

router = DefaultRouter()
router.register(r'templates', FlowTemplateViewSet, basename='opsflow-template')
router.register(r'executions', FlowExecutionViewSet, basename='opsflow-execution')
router.register(r'logs', OpsLogViewSet, basename='opsflow-log')
router.register(r'knowledge', OpsKnowledgeViewSet, basename='opsflow-knowledge')
router.register(r'schedule-plans', SchedulePlanViewSet, basename='opsflow-schedule-plan')
router.register(r'plugins', PluginViewSet, basename='opsflow-plugin')

urlpatterns = [
    path('dashboard/stats/', dashboard_stats, name='opsflow-dashboard-stats'),
    path('dashboard/trend/', dashboard_trend, name='opsflow-dashboard-trend'),
    path('dashboard/schedule-stats/', dashboard_schedule_stats, name='opsflow-dashboard-schedule-stats'),
    path('dashboard/top-templates/', dashboard_top_templates, name='opsflow-dashboard-top-templates'),
    path('dashboard/user-activity/', dashboard_user_activity, name='opsflow-dashboard-user-activity'),
    path('dashboard/status-distribution/', dashboard_status_distribution, name='opsflow-dashboard-status-distribution'),
    path('dashboard/node-type-distribution/', dashboard_node_type_distribution, name='opsflow-dashboard-node-type-distribution'),
] + router.urls
