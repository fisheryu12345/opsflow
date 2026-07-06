# -*- coding: utf-8 -*-
"""Escalation serializers — with i18n support"""

from common.utils.serializers import CustomModelSerializer
from itsm.models import EscalationLevel


class EscalationLevelSerializer(CustomModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        lang = ''
        if request:
            lang = request.query_params.get('lang', '') or request.META.get('HTTP_X_LANG', '')
        if lang and lang.startswith('en') and instance.name_en:
            data['name'] = instance.name_en
        return data
