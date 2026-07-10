# -*- coding: utf-8 -*-
"""ViewSets for Schedule, Day, Duration CRUD."""

from django.db import models
from itsm.models import Duration, Day, Schedule
from itsm.serializers.schedule import DurationSerializer, DaySerializer, ScheduleSerializer
from itsm.views.workflow_views import ItsmProjectViewSet


class DurationViewSet(ItsmProjectViewSet):
    """Duration CRUD."""
    model = Duration
    queryset = Duration.objects.all()
    serializer_class = DurationSerializer


class DayViewSet(ItsmProjectViewSet):
    """Day CRUD."""
    model = Day
    queryset = Day.objects.all()
    serializer_class = DaySerializer


class ScheduleViewSet(ItsmProjectViewSet):
    """Schedule CRUD — project-scoped + global.

    Built-in schedules (is_builtin=True) cannot be deleted.
    """
    model = Schedule
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    filter_fields = ['is_builtin', 'project']

    def get_queryset(self):
        qs = super().get_queryset()
        # Show global schedules + project-specific ones
        project_id = getattr(self.request, 'project_id', None)
        if project_id:
            return qs.filter(
                models.Q(project_id=project_id) | models.Q(project_id__isnull=True)
            )
        return qs

    def perform_destroy(self, instance):
        if instance.is_builtin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Built-in schedules cannot be deleted.")
        super().perform_destroy(instance)
