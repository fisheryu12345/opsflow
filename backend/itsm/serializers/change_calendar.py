# -*- coding: utf-8 -*-
"""Serializer for Change Calendar aggregated response items."""
from rest_framework import serializers


class CalendarItemSerializer(serializers.Serializer):
    """Unified calendar item — output only, no model backing."""
    id = serializers.CharField()
    source = serializers.CharField()
    title = serializers.CharField()
    ticket_sn = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField()
    status_display = serializers.CharField()
    priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField(required=False, allow_null=True)
    link = serializers.CharField()
    assignee = serializers.ListField(required=False)
    service_item_name = serializers.CharField(required=False, allow_blank=True)
    sla_deadline = serializers.DateTimeField(required=False, allow_null=True)
    cron_description = serializers.CharField(required=False, allow_blank=True)
