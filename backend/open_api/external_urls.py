"""External-facing Open API URL patterns

由 application/urls.py 引用: path('api/v2/open/', include('open_api.external_urls'))
"""

from django.urls import path
from .views.external import health, cmdb_sync, create_incident, query_incident, trigger_execution

urlpatterns = [
    path('health/', health, name='open-health'),
    path('cmdb/sync/', cmdb_sync, name='open-cmdb-sync'),
    path('incidents/', create_incident, name='open-create-incident'),
    path('incidents/<str:incident_id>/', query_incident, name='open-query-incident'),
    path('executions/trigger/', trigger_execution, name='open-trigger-execution'),
]
