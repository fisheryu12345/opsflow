# -*- coding: utf-8 -*-
"""Serializers for agent app"""

from rest_framework import serializers

from .models import (
    AgentInstance, AgentTaskExecution, AgentTaskResult,
    AgentFileTask, AgentCollect, AgentUpgrade,
)


class AgentInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInstance
        fields = "__all__"
        read_only_fields = ['agent_id', 'status', 'last_heartbeat', 'first_register',
                            'credential_token', 'last_upgrade', 'upgrade_status']


class AgentTaskExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTaskExecution
        fields = "__all__"
        read_only_fields = ['status', 'exit_code', 'start_time', 'finish_time', 'error_msg']


class AgentTaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentTaskResult
        fields = "__all__"


class AgentFileTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentFileTask
        fields = "__all__"
        read_only_fields = ['progress', 'status', 'error_msg']


class AgentCollectSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCollect
        fields = "__all__"


class AgentUpgradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentUpgrade
        fields = "__all__"
        read_only_fields = ['status', 'started_at', 'finished_at', 'error_msg']
