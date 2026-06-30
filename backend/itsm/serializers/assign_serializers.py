# -*- coding: utf-8 -*-
"""Serializers for ITSM assignment models"""

from dvadmin.utils.serializers import CustomModelSerializer
from itsm.models.skill_group import SkillGroup, OnDutySchedule
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.models.transfer_log import TicketTransferLog


class SkillGroupSerializer(CustomModelSerializer):
    class Meta:
        model = SkillGroup
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class OnDutyScheduleSerializer(CustomModelSerializer):
    class Meta:
        model = OnDutySchedule
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class AssignRuleSerializer(CustomModelSerializer):
    class Meta:
        model = AssignRule
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class EscalationLevelSerializer(CustomModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class TicketTransferLogSerializer(CustomModelSerializer):
    class Meta:
        model = TicketTransferLog
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
