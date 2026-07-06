# -*- coding: utf-8 -*-
"""Serializers for ITSM app

统一规范: 继承 CustomModelSerializer，自动审计字段
"""

from common.utils.serializers import CustomModelSerializer
from itsm.models import ServiceCategory, SlaPolicy


class ServiceCategorySerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class ServiceCategoryCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class SlaPolicySerializer(CustomModelSerializer):
    class Meta:
        model = SlaPolicy
        fields = "__all__"
