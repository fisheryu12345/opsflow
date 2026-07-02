# -*- coding: utf-8 -*-
"""Ticket serializers"""

from common.utils.serializers import CustomModelSerializer
from itsm.models import Ticket, TicketStatus, SignTask


class TicketSerializer(CustomModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'create_datetime', 'update_datetime']


class TicketCreateSerializer(CustomModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'creator', 'create_datetime', 'update_datetime']


class TicketSubmitSerializer(CustomModelSerializer):
    """提交工单（启动 pipeline）"""
    class Meta:
        model = Ticket
        fields = ['id']


class TicketApproveSerializer(CustomModelSerializer):
    """审批工单"""
    class Meta:
        model = Ticket
        fields = ['id', 'state_id', 'approve_result', 'comment']


class TicketStatusSerializer(CustomModelSerializer):
    class Meta:
        model = TicketStatus
        fields = '__all__'


class SignTaskSerializer(CustomModelSerializer):
    class Meta:
        model = SignTask
        fields = '__all__'
