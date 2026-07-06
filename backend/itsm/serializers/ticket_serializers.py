# -*- coding: utf-8 -*-
"""Ticket serializers"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from itsm.models import Ticket, TicketStatus, SignTask, SlaTask


class TicketSerializer(CustomModelSerializer):
    sla_info = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'create_datetime', 'update_datetime', 'sla_info']

    @staticmethod
    def get_sla_info(obj):
        task = next(iter(obj.sla_tasks.all()), None)
        if not task:
            return None
        from django.utils import timezone
        now = timezone.now()
        remaining = None
        if task.deadline:
            delta = task.deadline - now
            remaining = max(0, int(delta.total_seconds()))
        return {
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'reply_deadline': task.reply_deadline.isoformat() if task.reply_deadline else None,
            'remaining_seconds': remaining,
            'task_status': task.task_status,
            'sla_status': task.sla_status,
            'policy_name': task.sla_policy.name if task.sla_policy else None,
        }


class TicketCreateSerializer(CustomModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'creator', 'create_datetime', 'update_datetime']
        extra_kwargs = {
            'workflow_version': {'required': False, 'allow_null': True},
        }


class TicketStatusSerializer(CustomModelSerializer):
    class Meta:
        model = TicketStatus
        fields = '__all__'


class SignTaskSerializer(CustomModelSerializer):
    class Meta:
        model = SignTask
        fields = '__all__'
