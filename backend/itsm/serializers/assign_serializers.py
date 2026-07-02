# -*- coding: utf-8 -*-
"""Serializers for ITSM assignment models"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from itsm.models.skill_group import SkillGroup, OnDutySchedule
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.models.transfer_log import TicketTransferLog


class SkillGroupSerializer(CustomModelSerializer):
    leader_name = serializers.CharField(source='leader.name', read_only=True, default='')

    class Meta:
        model = SkillGroup
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class OnDutyScheduleSerializer(CustomModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default='')
    user_name = serializers.CharField(source='user.name', read_only=True, default='')

    class Meta:
        model = OnDutySchedule
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class AssignRuleSerializer(CustomModelSerializer):
    target_group_name = serializers.CharField(source='target_group.name', read_only=True, default='')
    match_category_name = serializers.CharField(source='match_category.name', read_only=True, default='')

    class Meta:
        model = AssignRule
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class EscalationLevelSerializer(CustomModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default='')

    class Meta:
        model = EscalationLevel
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class TicketTransferLogSerializer(CustomModelSerializer):
    class Meta:
        model = TicketTransferLog
        fields = '__all__'
        read_only_fields = ['id', 'create_datetime', 'update_datetime']
