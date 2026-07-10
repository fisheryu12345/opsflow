# -*- coding: utf-8 -*-
"""Trigger CRUD — project-scoped with multi-tenant isolation"""

from ..models import Trigger, TriggerExecution
from ..serializers.trigger import TriggerSerializer
from .workflow_views import ItsmProjectViewSet
from rest_framework.decorators import action
from rest_framework.response import Response


class TriggerViewSet(ItsmProjectViewSet):
    """触发器 CRUD — project-scoped"""
    model = Trigger
    queryset = Trigger.objects.prefetch_related('actions', 'states').select_related('workflow')
    serializer_class = TriggerSerializer
    filter_fields = ['event_type', 'workflow', 'is_active', 'states']
    ordering = ['-create_datetime']

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Return execution history for this trigger."""
        trigger = self.get_object()
        qs = TriggerExecution.objects.filter(trigger=trigger).order_by('-created_at')
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response([
                {
                    'id': e.id,
                    'status': e.status,
                    'event_type': e.event_type,
                    'action_results': e.action_results,
                    'created_at': e.created_at,
                    'ticket_id': e.ticket_id,
                }
                for e in page
            ])
        return Response([])
