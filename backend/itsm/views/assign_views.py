# -*- coding: utf-8 -*-
"""View sets for ITSM assignment models"""

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse
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


class SkillGroupViewSet(CustomModelViewSet):
    """技能组管理"""
    model = SkillGroup
    queryset = SkillGroup.objects.all()
    serializer_class = SkillGroupSerializer
    search_fields = ['name', 'code']

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


class OnDutyScheduleViewSet(CustomModelViewSet):
    """值班排班管理"""
    model = OnDutySchedule
    queryset = OnDutySchedule.objects.all()
    serializer_class = OnDutyScheduleSerializer
    filter_fields = ['group', 'duty_date', 'duty_type']


class AssignRuleViewSet(CustomModelViewSet):
    """分派规则管理"""
    model = AssignRule
    queryset = AssignRule.objects.all()
    serializer_class = AssignRuleSerializer
    filter_fields = ['is_active', 'target_group']
    ordering = ['priority']


class EscalationLevelViewSet(CustomModelViewSet):
    """升级级别管理"""
    model = EscalationLevel
    queryset = EscalationLevel.objects.all()
    serializer_class = EscalationLevelSerializer
    filter_fields = ['group', 'level']


class TicketTransferLogViewSet(CustomModelViewSet):
    """转派记录查询"""
    model = TicketTransferLog
    queryset = TicketTransferLog.objects.all()
    serializer_class = TicketTransferLogSerializer
    filter_fields = ['ticket', 'transfer_type']
    ordering = ['-create_datetime']
