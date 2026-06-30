# -*- coding: utf-8 -*-
"""Serializers for identity sync — sync trigger, status, mappings"""

from rest_framework import serializers


class SyncTriggerSerializer(serializers.Serializer):
    """手动触发同步请求（无必填参数）"""
    pass


class SyncStatusSerializer(serializers.Serializer):
    """同步状态概览"""
    instance_id = serializers.IntegerField()
    instance_name = serializers.CharField()
    definition_code = serializers.CharField()
    status = serializers.CharField()
    dept_count = serializers.IntegerField(default=0)
    user_count = serializers.IntegerField(default=0)
    last_sync_at = serializers.DateTimeField(allow_null=True, default=None)


class SyncResultSerializer(serializers.Serializer):
    """同步结果"""
    success = serializers.BooleanField()
    instance_id = serializers.IntegerField()
    instance_name = serializers.CharField()
    dept_added = serializers.IntegerField(default=0)
    dept_updated = serializers.IntegerField(default=0)
    dept_disabled = serializers.IntegerField(default=0)
    user_added = serializers.IntegerField(default=0)
    user_updated = serializers.IntegerField(default=0)
    user_disabled = serializers.IntegerField(default=0)
    errors = serializers.ListField(default=list)
    error = serializers.CharField(allow_null=True, default=None)
