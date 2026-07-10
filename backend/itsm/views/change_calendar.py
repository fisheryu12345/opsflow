# -*- coding: utf-8 -*-
"""Change Calendar ViewSet — aggregates ITSM tickets + OpsFlow schedules."""
from datetime import date as date_type

from rest_framework.exceptions import ValidationError

from common.utils.json_response import DetailResponse
from itsm.views.workflow_views import ItsmProjectViewSet
from itsm.services.change_calendar import ChangeCalendarService
from itsm.serializers.change_calendar import CalendarItemSerializer


class ChangeCalendarViewSet(ItsmProjectViewSet):
    """变更日历 — unified timeline of ITSM tickets and OpsFlow schedules.

    GET /api/itsm/change-calendar/
        ?start_date=2026-07-01&end_date=2026-07-31&project_id=1
        &source=itsm_ticket|opsflow_schedule
        &ticket_type=change|incident|request|problem
    """
    model = None
    serializer_class = CalendarItemSerializer

    def list(self, request, *args, **kwargs):
        start_date_str = request.query_params.get('start_date', '')
        end_date_str = request.query_params.get('end_date', '')
        project_id = request.query_params.get('project_id', '')
        source = request.query_params.get('source', '')
        ticket_type = request.query_params.get('ticket_type', '')

        if not start_date_str or not end_date_str:
            raise ValidationError({'detail': 'start_date and end_date are required'})

        if not project_id:
            raise ValidationError({'detail': 'project_id is required'})

        try:
            start_date = date_type.fromisoformat(start_date_str)
            end_date = date_type.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            raise ValidationError({'detail': 'Invalid date format. Use YYYY-MM-DD.'})

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            raise ValidationError({'detail': 'project_id must be an integer.'})

        items = ChangeCalendarService.aggregate(
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            source=source or None,
            ticket_type=ticket_type or None,
        )

        serializer = self.get_serializer(items, many=True)
        return DetailResponse(data={
            'items': serializer.data,
            'total': len(items),
        })
