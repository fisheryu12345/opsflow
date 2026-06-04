"""URL configuration for job_platform app

路由前缀: /api/job-platform/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import ScriptViewSet, JobDefinitionViewSet, JobExecutionViewSet, DangerousCmdRuleViewSet

router = routers.SimpleRouter()
router.register(r'scripts', ScriptViewSet)
router.register(r'jobs', JobDefinitionViewSet)
router.register(r'executions', JobExecutionViewSet)
router.register(r'dangerous-rules', DangerousCmdRuleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
