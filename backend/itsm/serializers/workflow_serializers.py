# -*- coding: utf-8 -*-
"""Workflow serializers — with i18n support"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from common.utils.language import get_request_lang
from itsm.models import Workflow, WorkflowVersion, State, Transition, Field


class WorkflowSerializer(CustomModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['is_enabled', 'create_datetime', 'update_datetime']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and instance.name_en:
            data['name'] = instance.name_en
        return data


class WorkflowCreateSerializer(CustomModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'


class WorkflowVersionSerializer(CustomModelSerializer):
    workflow_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowVersion
        fields = '__all__'
        read_only_fields = ['create_datetime']

    def get_workflow_name(self, obj):
        if not obj.workflow:
            return ''
        lang = get_request_lang(self.context.get('request'))
        if lang == 'en' and obj.workflow.name_en:
            return obj.workflow.name_en
        return obj.workflow.name


class StateSerializer(CustomModelSerializer):
    class Meta:
        model = State
        fields = '__all__'


class TransitionSerializer(CustomModelSerializer):
    class Meta:
        model = Transition
        fields = '__all__'


class FieldSerializer(CustomModelSerializer):
    class Meta:
        model = Field
        fields = '__all__'
