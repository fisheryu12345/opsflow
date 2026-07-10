# -*- coding: utf-8 -*-
"""Change Calendar aggregation service.

Aggregates ITSM tickets and OpsFlow schedule plans into a unified,
time-sorted list for calendar/timeline rendering.
"""
import logging
from datetime import timedelta
from django.db.models import Q

logger = logging.getLogger(__name__)


class ChangeCalendarService:
    """Aggregate change-related items from ITSM and OpsFlow."""

    @staticmethod
    def aggregate(start_date, end_date, project_id, source=None, ticket_type=None):
        """Return unified, time-sorted list of calendar items."""
        items = []

        if source is None or source == 'itsm_ticket':
            items.extend(ChangeCalendarService._get_ticket_items(
                start_date, end_date, project_id, ticket_type
            ))

        if source is None or source == 'opsflow_schedule':
            items.extend(ChangeCalendarService._get_schedule_items(
                start_date, end_date, project_id
            ))

        items.sort(key=lambda x: x['start_time'] if x['start_time'] else '')
        return items

    @staticmethod
    def _get_ticket_items(start_date, end_date, project_id, ticket_type):
        from datetime import datetime as dt_type
        from django.utils import timezone
        from itsm.models import Ticket

        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(dt_type(start_date.year, start_date.month, start_date.day, 0, 0, 0), tz)
        end_dt = timezone.make_aware(dt_type(end_date.year, end_date.month, end_date.day, 23, 59, 59), tz)

        qs = Ticket.objects.filter(
            project_id=project_id,
            create_datetime__gte=start_dt,
            create_datetime__lte=end_dt,
        ).exclude(current_status='draft').select_related('workflow_version__workflow')

        if ticket_type:
            qs = qs.filter(itsm_type=ticket_type)

        status_map = dict(Ticket.STATUS_CHOICES)
        items = []
        for ticket in qs.iterator():
            sla_deadline = ChangeCalendarService._get_sla_deadline(ticket)
            end_time = None
            if hasattr(ticket, 'finished_at') and ticket.finished_at:
                end_time = ticket.finished_at
            elif sla_deadline:
                from django.utils.dateparse import parse_datetime
                end_time = parse_datetime(sla_deadline)

            # Extract assignee names from ticket.meta
            assignee = []
            meta = ticket.meta or {}
            assignee_data = meta.get('assignee', [])
            if assignee_data:
                if isinstance(assignee_data, list):
                    for a in assignee_data:
                        if isinstance(a, dict):
                            assignee.append(a.get('name', a.get('username', '')))
                        else:
                            assignee.append(str(a))

            # Extract service item name
            service_item_name = ''
            if hasattr(ticket, 'service_item') and ticket.service_item:
                service_item_name = ticket.service_item.name

            items.append({
                'id': f'ticket_{ticket.id}',
                'source': 'itsm_ticket',
                'title': ticket.title or '',
                'ticket_sn': ticket.sn or '',
                'status': ticket.current_status,
                'status_display': status_map.get(ticket.current_status, ticket.current_status),
                'priority': ticket.priority,
                'start_time': ticket.create_datetime,
                'end_time': end_time,
                'link': f'/apps/itsm/ticket/{ticket.id}',
                'assignee': assignee,
                'service_item_name': service_item_name,
                'sla_deadline': sla_deadline,
            })
        return items

    @staticmethod
    def _get_schedule_items(start_date, end_date, project_id):
        from opsflow.models import SchedulePlan

        qs = SchedulePlan.objects.filter(
            project_id=project_id,
            status__in=['active', 'paused'],
        )

        status_map = dict(SchedulePlan.Status.choices)
        items = []
        for sp in qs.iterator():
            event_time = sp.scheduled_at or sp.next_run_at
            if event_time is None:
                continue
            # Filter by date range
            event_date = event_time.date()
            if event_date < start_date or event_date > end_date:
                continue

            end_time = event_time + timedelta(hours=1)

            items.append({
                'id': f'schedule_{sp.id}',
                'source': 'opsflow_schedule',
                'title': sp.name or '',
                'status': sp.status,
                'status_display': status_map.get(sp.status, sp.status),
                'priority': None,
                'start_time': event_time,
                'end_time': end_time,
                'link': f'/apps/opsflow-template/schedule/{sp.id}',
                'cron_description': sp.cron_description or '',
            })
        return items

    @staticmethod
    def _get_sla_deadline(ticket):
        """Return SLA deadline as ISO string, or None."""
        try:
            from itsm.models import SlaTask
            sla_task = SlaTask.objects.filter(ticket=ticket).first()
            if sla_task and sla_task.deadline:
                return sla_task.deadline.isoformat()
        except Exception:
            logger.warning("Failed to fetch SLA deadline for ticket %s", ticket.id, exc_info=True)
        return None
