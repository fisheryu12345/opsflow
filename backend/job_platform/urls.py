# -*- coding: utf-8 -*-
"""URL configuration for job_platform app

路由前缀: /api/job-platform/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import (
    AccountViewSet, FileSourceViewSet,
    ScriptViewSet,
    TemplateViewSet, PlanViewSet, VariableViewSet,
    StepViewSet, ScriptStepViewSet, FileStepViewSet, ApprovalStepViewSet,
    JobExecutionViewSet, StepExecutionViewSet,
    DangerousCmdRuleViewSet, DangerousCheckLogViewSet,
    CronJobViewSet,
    QuickExecViewSet,
    DashboardViewSet,
)

router = routers.SimpleRouter()
router.register(r'accounts', AccountViewSet)
router.register(r'file-sources', FileSourceViewSet)
router.register(r'scripts', ScriptViewSet)
router.register(r'templates', TemplateViewSet)
router.register(r'plans', PlanViewSet)
router.register(r'variables', VariableViewSet)
router.register(r'steps', StepViewSet)
router.register(r'script-steps', ScriptStepViewSet)
router.register(r'file-steps', FileStepViewSet)
router.register(r'approval-steps', ApprovalStepViewSet)
router.register(r'executions', JobExecutionViewSet)
router.register(r'step-executions', StepExecutionViewSet)
router.register(r'dangerous-rules', DangerousCmdRuleViewSet)
router.register(r'dangerous-logs', DangerousCheckLogViewSet)
router.register(r'cron-jobs', CronJobViewSet)
router.register(r'quick-exec', QuickExecViewSet, basename='quick-exec')
router.register(r'dashboard', DashboardViewSet, basename='job-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
