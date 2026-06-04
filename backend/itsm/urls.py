# -*- coding: utf-8 -*-
"""URL configuration for ITSM app

路由前缀: /api/itsm/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import (
    ServiceCategoryViewSet, SlaPolicyViewSet,
    IncidentViewSet, ChangeViewSet,
    ServiceRequestViewSet, ProblemViewSet,
)
from .views.workflow_views import (
    WorkflowViewSet, WorkflowVersionViewSet,
    StateViewSet, TransitionViewSet,
    FieldViewSet, AIGenerateViewSet,
)
from .views.ticket_views import TicketViewSet

router = routers.SimpleRouter()
# Existing ITSM routes
router.register(r'service-categories', ServiceCategoryViewSet)
router.register(r'sla-policies', SlaPolicyViewSet)
router.register(r'incidents', IncidentViewSet)
router.register(r'changes', ChangeViewSet)
router.register(r'service-requests', ServiceRequestViewSet)
router.register(r'problems', ProblemViewSet)

# Workflow engine routes
router.register(r'workflows', WorkflowViewSet)
router.register(r'workflow-versions', WorkflowVersionViewSet)
router.register(r'states', StateViewSet)
router.register(r'transitions', TransitionViewSet)
router.register(r'fields', FieldViewSet)
router.register(r'tickets', TicketViewSet)

# AI generation
router.register(r'ai', AIGenerateViewSet, basename='ai-generate')

urlpatterns = [
    path('', include(router.urls)),
]
