# -*- coding: utf-8 -*-
"""Serializers for ITSM app

统一规范: 继承 CustomModelSerializer，自动审计字段
"""

from common.utils.serializers import CustomModelSerializer
from itsm.models.incident import Incident, Change, ServiceRequest, Problem, ServiceCategory, SlaPolicy


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


class IncidentSerializer(CustomModelSerializer):
    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = ['incident_id', 'sla_status', 'sla_deadline']


class IncidentCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Incident
        fields = "__all__"
        read_only_fields = ['incident_id', 'status', 'sla_status', 'sla_deadline', 'resolved_at']


class ChangeSerializer(CustomModelSerializer):
    class Meta:
        model = Change
        fields = "__all__"
        read_only_fields = ['change_id']


class ChangeCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Change
        fields = "__all__"
        read_only_fields = ['change_id', 'status']


class ServiceRequestSerializer(CustomModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = ['request_id']


class ProblemSerializer(CustomModelSerializer):
    class Meta:
        model = Problem
        fields = "__all__"
        read_only_fields = ['problem_id']


class ProblemCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Problem
        fields = "__all__"
        read_only_fields = ['problem_id', 'status']
