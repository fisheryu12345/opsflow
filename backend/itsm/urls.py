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
    FieldViewSet, AIGenerateView,
)
from .views.ticket_views import TicketViewSet
from .views.dashboard import DashboardViewSet
from .views.delegation import DelegationViewSet
from .views.assign_views import (
    SkillGroupViewSet, OnDutyScheduleViewSet,
    AssignRuleViewSet, EscalationLevelViewSet,
    TicketTransferLogViewSet,
)

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

# Dashboard (read-only 看板)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# Delegation (审批委托)
router.register(r'delegations', DelegationViewSet)

# Assignment management
router.register(r'skill-groups', SkillGroupViewSet)
router.register(r'on-duty-schedules', OnDutyScheduleViewSet)
router.register(r'assign-rules', AssignRuleViewSet)
router.register(r'escalation-levels', EscalationLevelViewSet)
router.register(r'transfer-logs', TicketTransferLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # AI generation (APIView, not ModelViewSet)
    path('ai/generate-workflow/', AIGenerateView.as_view(), name='ai-generate-workflow'),
    path('ai/generate-fields/', AIGenerateView.as_view(), name='ai-generate-fields'),
]
