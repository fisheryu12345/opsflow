# -*- coding: utf-8 -*-
"""Serializers for ITSM app — ServiceCategory, SlaPolicy with i18n support"""

from common.utils.serializers import CustomModelSerializer
from itsm.models import ServiceCategory, SlaPolicy


def _i18n_name(instance, data, field='name'):
    """根据请求语言返回对应语言的名称，序列化器 MethodField 使用"""
    request = data.context.get('request') if hasattr(data, 'context') else None
    lang = ''
    if request:
        lang = request.query_params.get('lang', '') or request.META.get('HTTP_X_LANG', '')
    if lang == 'en':
        en_val = getattr(instance, f'{field}_en', '')
        if en_val:
            return en_val
    return getattr(instance, field, '')


class ServiceCategorySerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        lang = ''
        if request:
            lang = request.query_params.get('lang', '') or request.META.get('HTTP_X_LANG', '')
        if lang and lang.startswith('en'):
            if instance.name_en:
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
        request = self.context.get('request')
        lang = ''
        if request:
            lang = request.query_params.get('lang', '') or request.META.get('HTTP_X_LANG', '')
        if lang and lang.startswith('en'):
            if instance.name_en:
                data['name'] = instance.name_en
        return data
