# -*- coding: utf-8 -*-
"""Ticket serializers"""

from rest_framework import serializers
from common.utils.serializers import CustomModelSerializer
from itsm.models import Ticket, TicketStatus, SignTask, SlaTask


class TicketSerializer(CustomModelSerializer):
    sla_info = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['sn', 'current_status', 'pipeline_id',
                            'create_datetime', 'update_datetime', 'sla_info']

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

    def get_processor_name(self, obj):
        """Resolve processors text (may be user IDs) to display names."""
        raw = obj.processors or ''
        if not raw.strip():
            return ''
        # Use cached user map from context to avoid N+1 queries
        user_map = getattr(self, '_user_map', None)
        if user_map is None:
            from django.contrib.auth import get_user_model
            from django.db.models import Q
            User = get_user_model()
            # Collect all numeric IDs from ALL records being serialized, then batch-query once
            all_ids = set()
            if self.parent and hasattr(self.parent, 'instance') and isinstance(self.parent.instance, list):
                for ts in self.parent.instance:
                    r = (ts.processors or '')
                    for x in r.replace(';', ',').split(','):
                        if x.strip().isdigit():
                            all_ids.add(int(x.strip()))
            if not all_ids:
                self._user_map = {}
                return raw + ''  # non-numeric — return as-is
            users = User.objects.filter(Q(id__in=all_ids)).values('id', 'username')
            self._user_map = {str(u['id']): u.get('username', str(u['id'])) for u in users}
        ids = [x.strip() for x in raw.replace(';', ',').split(',') if x.strip().isdigit()]
        if ids:
            return ', '.join(self._user_map.get(uid, uid) for uid in ids)
        return raw


class SignTaskSerializer(CustomModelSerializer):
    class Meta:
        model = SignTask
        fields = '__all__'
