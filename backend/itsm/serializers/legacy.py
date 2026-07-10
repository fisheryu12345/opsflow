# -*- coding: utf-8 -*-
"""Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support"""

from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import ServiceCategory, SlaPolicy


class ServiceCategorySerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data


class ServiceCategoryCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class SlaPolicySerializer(CustomModelSerializer):
    class Meta:
        model = SlaPolicy
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data
