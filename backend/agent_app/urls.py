# -*- coding: utf-8 -*-
"""URL routing for agent app"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AgentInstanceViewSet, AgentTaskExecutionViewSet,
    AgentFileTaskViewSet, AgentCollectViewSet, AgentUpgradeViewSet,
    DirectFileDownloadView,
)
from . import internal_views

router = DefaultRouter()
router.register(r'agents', AgentInstanceViewSet, basename='agent-instance')
router.register(r'tasks', AgentTaskExecutionViewSet, basename='agent-task')
router.register(r'files', AgentFileTaskViewSet, basename='agent-file')
router.register(r'collect', AgentCollectViewSet, basename='agent-collect')
router.register(r'upgrades', AgentUpgradeViewSet, basename='agent-upgrade')

urlpatterns = [
    # Internal endpoints (no auth — Agent Server ↔ Django)
    path('internal/batch_results/', internal_views.batch_results, name='internal-batch-results'),
    path('internal/collect_reports/', internal_views.collect_reports, name='internal-collect-reports'),
    path('file-download/<str:file_task_id>/', DirectFileDownloadView.get, name='file-download'),
    path('', include(router.urls)),
]
