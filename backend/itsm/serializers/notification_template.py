# -*- coding: utf-8 -*-
"""Serializer for NotificationTemplate with i18n support"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import NotificationTemplate


class NotificationTemplateSerializer(CustomModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data
