# -*- coding: utf-8 -*-
"""Serializers for job_platform app
"""

from rest_framework import serializers
from dvadmin.utils.serializers import CustomModelSerializer
from .models.models import Script, JobDefinition, JobExecution, DangerousCmdRule


class ScriptSerializer(CustomModelSerializer):
    class Meta:
        model = Script
        fields = "__all__"


class ScriptCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Script
        fields = "__all__"


class JobDefinitionSerializer(CustomModelSerializer):
    class Meta:
        model = JobDefinition
        fields = "__all__"
        read_only_fields = ['id', 'create_datetime', 'update_datetime']


class JobDefinitionCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = JobDefinition
        fields = "__all__"


class JobExecutionSerializer(CustomModelSerializer):
    job_name = serializers.CharField(source='job.name', read_only=True, default='')

    class Meta:
        model = JobExecution
        fields = "__all__"
        read_only_fields = ['status', 'started_at', 'finished_at', 'result_detail',
                            'exit_code', 'error_message', 'result_summary']


class JobExecutionDetailSerializer(CustomModelSerializer):
    """执行详情 — 包含完整结果"""
    class Meta:
        model = JobExecution
        fields = "__all__"


class DangerousCmdRuleSerializer(CustomModelSerializer):
    class Meta:
        model = DangerousCmdRule
        fields = "__all__"
