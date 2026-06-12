from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.template_views import FlowTemplateViewSet
from .views.template_category_views import TemplateCategoryViewSet
from .views.execution_views import FlowExecutionViewSet
from .views.log_views import OpsLogViewSet
from .views.knowledge_views import OpsKnowledgeViewSet
from .views.dashboard_views import (
    dashboard_stats, dashboard_trend, dashboard_schedule_stats,
    dashboard_top_templates, dashboard_user_activity,
    dashboard_status_distribution, dashboard_node_type_distribution,
    dashboard_duration_distribution, dashboard_node_duration_top,
    dashboard_success_rate_trend, dashboard_template_stats,
)
from .views.schedule_views import SchedulePlanViewSet
from .views.plugin_views import PluginViewSet
from .views.node_views import TemplateNodeViewSet, ExecutionNodeViewSet
from .views.mixins.template_dr import create_dr_pipeline, preview_dr_topology
from .views.scheme_views import ExecutionSchemeViewSet
from .views.audit_views import OperationRecordViewSet
from .views.project_views import OpsProjectViewSet

router = DefaultRouter()
router.register(r'templates', FlowTemplateViewSet, basename='opsflow-template')
router.register(r'executions', FlowExecutionViewSet, basename='opsflow-execution')
router.register(r'logs', OpsLogViewSet, basename='opsflow-log')
router.register(r'knowledge', OpsKnowledgeViewSet, basename='opsflow-knowledge')
router.register(r'schedule-plans', SchedulePlanViewSet, basename='opsflow-schedule-plan')
router.register(r'plugins', PluginViewSet, basename='opsflow-plugin')
router.register(r'template-nodes', TemplateNodeViewSet, basename='opsflow-template-node')
router.register(r'execution-nodes', ExecutionNodeViewSet, basename='opsflow-execution-node')
router.register(r'audit', OperationRecordViewSet, basename='opsflow-audit')
router.register(r'projects', OpsProjectViewSet, basename='opsflow-project')
router.register(r'template-categories', TemplateCategoryViewSet, basename='opsflow-template-category')

# 嵌套路由：templates/{id}/schemes/
# --- Project member routes ---
project_members = OpsProjectViewSet.as_view({
    'get': 'members', 'post': 'members',
})
project_remove_member = OpsProjectViewSet.as_view({
    'delete': 'remove_member',
})

scheme_list = ExecutionSchemeViewSet.as_view({
    'get': 'list', 'post': 'create',
})
scheme_detail = ExecutionSchemeViewSet.as_view({
    'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy',
})
scheme_preview = ExecutionSchemeViewSet.as_view({
    'get': 'preview',
})

urlpatterns = [
    path('projects/<int:pk>/members/', project_members, name='opsflow-project-members'),
    path('projects/<int:pk>/members/<int:member_id>/', project_remove_member, name='opsflow-project-remove-member'),
    path('templates/<int:template_pk>/schemes/', scheme_list, name='opsflow-template-scheme-list'),
    path('templates/<int:template_pk>/schemes/<int:pk>/', scheme_detail, name='opsflow-template-scheme-detail'),
    path('templates/<int:template_pk>/schemes/<int:pk>/preview/', scheme_preview, name='opsflow-template-scheme-preview'),
    path('templates/preview_dr_topology/', preview_dr_topology, name='opsflow-template-preview-dr-topology'),
    path('templates/create_dr_pipeline/', create_dr_pipeline, name='opsflow-template-create-dr-pipeline'),
    path('dashboard/stats/', dashboard_stats, name='opsflow-dashboard-stats'),
    path('dashboard/trend/', dashboard_trend, name='opsflow-dashboard-trend'),
    path('dashboard/schedule-stats/', dashboard_schedule_stats, name='opsflow-dashboard-schedule-stats'),
    path('dashboard/top-templates/', dashboard_top_templates, name='opsflow-dashboard-top-templates'),
    path('dashboard/user-activity/', dashboard_user_activity, name='opsflow-dashboard-user-activity'),
    path('dashboard/status-distribution/', dashboard_status_distribution, name='opsflow-dashboard-status-distribution'),
    path('dashboard/node-type-distribution/', dashboard_node_type_distribution, name='opsflow-dashboard-node-type-distribution'),
    path('dashboard/duration-distribution/', dashboard_duration_distribution, name='opsflow-dashboard-duration-distribution'),
    path('dashboard/node-duration-top/', dashboard_node_duration_top, name='opsflow-dashboard-node-duration-top'),
    path('dashboard/success-rate-trend/', dashboard_success_rate_trend, name='opsflow-dashboard-success-rate-trend'),
    path('dashboard/template-stats/', dashboard_template_stats, name='opsflow-dashboard-template-stats'),
] + router.urls
