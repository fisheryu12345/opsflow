# -*- coding: utf-8 -*-
"""URL configuration for ITSM app

路由前缀: /api/itsm/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import (
    ServiceCategoryViewSet, SlaPolicyViewSet,
)
from .views.workflow_views import (
    WorkflowViewSet, WorkflowVersionViewSet,
    StateViewSet, TransitionViewSet,
    FieldViewSet, AIGenerateView,
)
from .views.ticket_views import TicketViewSet
from .views.dashboard import DashboardViewSet
from .views.delegation import DelegationViewSet
from .views.service_item import ServiceItemViewSet
from .views.escalation_views import EscalationLevelViewSet
from .views.preset_views import PresetViewSet
from .views.schedule_views import ScheduleViewSet, DayViewSet, DurationViewSet

router = routers.SimpleRouter()
# Existing ITSM routes
router.register(r'service-categories', ServiceCategoryViewSet)
router.register(r'sla-policies', SlaPolicyViewSet)

# Workflow engine routes
router.register(r'workflows', WorkflowViewSet)
router.register(r'workflow-versions', WorkflowVersionViewSet)
router.register(r'states', StateViewSet)
router.register(r'transitions', TransitionViewSet)
router.register(r'fields', FieldViewSet)
router.register(r'tickets', TicketViewSet)

# Dashboard (read-only 看板)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# Delegation (审批委托)
router.register(r'delegations', DelegationViewSet)

# Service catalog
router.register(r'service-items', ServiceItemViewSet)

# Escalation hierarchy
router.register(r'escalation-levels', EscalationLevelViewSet)

# Presets (预设管理)
router.register(r'presets', PresetViewSet)

# SLA Working Time Model
router.register(r'schedules', ScheduleViewSet)
router.register(r'days', DayViewSet)
router.register(r'durations', DurationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # AI generation (APIView, not ModelViewSet)
    path('ai/generate-workflow/', AIGenerateView.as_view(), name='ai-generate-workflow'),
    path('ai/generate-fields/', AIGenerateView.as_view(), name='ai-generate-fields'),
]
