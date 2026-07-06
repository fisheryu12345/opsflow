# -*- coding: utf-8 -*-
"""Escalation serializers"""

from common.utils.serializers import CustomModelSerializer
from itsm.models import EscalationLevel


class EscalationLevelSerializer(CustomModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime']
