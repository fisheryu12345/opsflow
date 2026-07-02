# -*- coding: utf-8 -*-
"""View sets for ITSM assignment models — project-scoped with multi-tenant isolation"""

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.decorators import action

from itsm.models.skill_group import SkillGroup, OnDutySchedule
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.models.transfer_log import TicketTransferLog
from itsm.serializers.assign_serializers import (
    SkillGroupSerializer, OnDutyScheduleSerializer,
    AssignRuleSerializer, EscalationLevelSerializer,
    TicketTransferLogSerializer,
)
from itsm.views.workflow_views import ItsmProjectViewSet


class SkillGroupViewSet(CustomModelViewSet):
    """技能组管理 — business-scoped (非 project 维度，保持 CustomModelViewSet)"""
    model = SkillGroup
    queryset = SkillGroup.objects.all()
    serializer_class = SkillGroupSerializer
    search_fields = ['name', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        from iam.resolvers import get_visible_businesses
        biz_ids = get_visible_businesses(user)
        return qs.filter(business_id__in=biz_ids)

    @action(methods=['POST'], detail=True)
    def add_member(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        group.members.add(user_id)
        return DetailResponse(msg='成员已添加')

    @action(methods=['POST'], detail=True)
    def remove_member(self, request, pk=None):
        group = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return ErrorResponse(msg='user_id required')
        group.members.remove(user_id)
        return DetailResponse(msg='成员已移除')


class OnDutyScheduleViewSet(ItsmProjectViewSet):
    """值班排班管理 — project-scoped"""
    model = OnDutySchedule
    queryset = OnDutySchedule.objects.all()
    serializer_class = OnDutyScheduleSerializer
    filter_fields = ['group', 'duty_date', 'duty_type']


class AssignRuleViewSet(ItsmProjectViewSet):
    """分派规则管理 — project-scoped"""
    model = AssignRule
    queryset = AssignRule.objects.all()
    serializer_class = AssignRuleSerializer
    filter_fields = ['is_active', 'target_group']
    ordering = ['priority']


class EscalationLevelViewSet(ItsmProjectViewSet):
    """升级级别管理 — project-scoped"""
    model = EscalationLevel
    queryset = EscalationLevel.objects.all()
    serializer_class = EscalationLevelSerializer
    filter_fields = ['group', 'level']


class TicketTransferLogViewSet(CustomModelViewSet):
    """转派记录查询 — 级联 ticket，保持 CustomModelViewSet"""
    model = TicketTransferLog
    queryset = TicketTransferLog.objects.all()
    serializer_class = TicketTransferLogSerializer
    filter_fields = ['ticket', 'transfer_type']
    ordering = ['-create_datetime']
