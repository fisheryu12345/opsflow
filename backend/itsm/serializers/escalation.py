# -*- coding: utf-8 -*-
"""Escalation serializers — with i18n support"""

from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import EscalationLevel


class EscalationLevelSerializer(CustomModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = '__all__'
        read_only_fields = ['create_datetime', 'update_datetime']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data
