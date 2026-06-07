"""External-facing Open API URL patterns

由 application/urls.py 引用: path('api/v2/open/', include('open_api.external_urls'))
"""

from django.urls import path
from .views.external import health, cmdb_sync, create_incident, query_incident, trigger_execution
from .views.external import trigger_pipeline, query_execution, list_pipeline_templates

urlpatterns = [
    path('health/', health, name='open-health'),
    path('cmdb/sync/', cmdb_sync, name='open-cmdb-sync'),
    path('incidents/', create_incident, name='open-create-incident'),
    path('incidents/<str:incident_id>/', query_incident, name='open-query-incident'),
    path('executions/trigger/', trigger_execution, name='open-trigger-execution'),
    path('pipelines/trigger/', trigger_pipeline, name='open-trigger-pipeline'),
    path('pipelines/<int:execution_id>/', query_execution, name='open-query-execution'),
    path('pipelines/templates/', list_pipeline_templates, name='open-list-pipeline-templates'),
]
