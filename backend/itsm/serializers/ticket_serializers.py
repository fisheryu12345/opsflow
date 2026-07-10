# -*- coding: utf-8 -*-
"""Ticket serializers"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from itsm.models import Ticket, TicketStatus, SignTask, SlaTask


class TicketSerializer(CustomModelSerializer):
    sla_info = serializers.SerializerMethodField()
    workflow = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'create_datetime', 'update_datetime', 'sla_info']

    @staticmethod
    def get_workflow(obj):
        return obj.workflow_version.workflow_id

    @staticmethod
    def get_sla_info(obj):
        task = next(iter(obj.sla_tasks.all()), None)
        if not task:
            return None
        from django.utils import timezone
        now = timezone.now()
        remaining = None
        if task.deadline:
            delta = task.deadline - now
            remaining = max(0, int(delta.total_seconds()))
        return {
            'deadline': task.deadline.isoformat() if task.deadline else None,
            'reply_deadline': task.reply_deadline.isoformat() if task.reply_deadline else None,
            'remaining_seconds': remaining,
            'task_status': task.task_status,
            'sla_status': task.sla_status,
            'policy_name': task.sla_policy.name if task.sla_policy else None,
        }


class TicketCreateSerializer(CustomModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'creator', 'create_datetime', 'update_datetime']
        extra_kwargs = {
            'workflow_version': {'required': False, 'allow_null': True},
        }


class TicketStatusSerializer(CustomModelSerializer):
    processor_name = serializers.SerializerMethodField()

    class Meta:
        model = TicketStatus
        fields = '__all__'

    @staticmethod
    def _parse_processor_ids(raw: str) -> list:
        """Parse processors — always JSON array e.g. "[5, 4, 1]" or '["admin", "ops"]'"""
        import json
        if not raw or not raw.strip():
            return []
        try:
            parsed = json.loads(raw.strip())
            return list(parsed) if isinstance(parsed, list) else [parsed]
        except (json.JSONDecodeError, TypeError):
            return []

    def get_processor_name(self, obj):
        """Resolve processors text to display names."""
        ids = self._parse_processor_ids(obj.processors or '')
        if not ids:
            return obj.processors or ''

        user_map = getattr(self, '_user_map', None)
        if user_map is None:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            all_ids = set()
            parent_instance = getattr(self.parent, 'instance', None) if self.parent else None
            if parent_instance and hasattr(parent_instance, '__iter__'):
                for ts in parent_instance:
                    all_ids.update(self._parse_processor_ids(ts.processors or ''))
            all_ids.update(ids)
            if not all_ids:
                self._user_map = {}
                return obj.processors or ''
            users = User.objects.filter(id__in=all_ids).values('id', 'username')
            self._user_map = {str(u['id']): u.get('username', str(u['id'])) for u in users}

        names = [self._user_map.get(str(uid), str(uid)) for uid in ids]
        return ', '.join(names)


class SignTaskSerializer(CustomModelSerializer):
    class Meta:
        model = SignTask
        fields = '__all__'
