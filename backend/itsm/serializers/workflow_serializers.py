# -*- coding: utf-8 -*-
"""Workflow serializers"""

from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer
from itsm.models import Workflow, WorkflowVersion, State, Transition, Field


class WorkflowSerializer(CustomModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'
        read_only_fields = ['is_enabled', 'create_datetime', 'update_datetime']


class WorkflowCreateSerializer(CustomModelSerializer):
    class Meta:
        model = Workflow
        fields = '__all__'


class WorkflowVersionSerializer(CustomModelSerializer):
    workflow_name = serializers.CharField(source='workflow.name', read_only=True, default='')

    class Meta:
        model = WorkflowVersion
        fields = '__all__'
        read_only_fields = ['create_datetime']


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
