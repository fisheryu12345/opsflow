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
