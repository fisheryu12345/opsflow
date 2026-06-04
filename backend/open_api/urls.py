"""URL configuration for Open API Gateway

内部管理路由: /api/open-api/     (管理后台)
外部开放路由: /api/v2/open/      (第三方系统调用)
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import ApiAppViewSet, OpenApiTokenViewSet, WebhookSubscriptionViewSet, OpenApiLogViewSet
from .views.external import health, cmdb_sync, create_incident, query_incident, trigger_execution

# 管理后台路由
router = routers.SimpleRouter()
router.register(r'apps', ApiAppViewSet)
router.register(r'tokens', OpenApiTokenViewSet)
router.register(r'webhooks', WebhookSubscriptionViewSet)
router.register(r'call-logs', OpenApiLogViewSet)

# 内部管理 URL
admin_urls = [
    path('', include(router.urls)),
]

# 对外开放 URL (第三方系统调用)
external_urls = [
    path('health/', health, name='open-health'),
    path('cmdb/sync/', cmdb_sync, name='open-cmdb-sync'),
    path('incidents/', create_incident, name='open-create-incident'),
    path('incidents/<str:incident_id>/', query_incident, name='open-query-incident'),
    path('executions/trigger/', trigger_execution, name='open-trigger-execution'),
]

urlpatterns = admin_urls
