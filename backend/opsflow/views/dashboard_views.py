import logging
from datetime import timedelta

from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import FlowTemplate, FlowExecution, OpsLog

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Return aggregate statistics for the opsflow dashboard."""
    User = settings.AUTH_USER_MODEL

    # --- Execution counts by status ---
    status_qs = FlowExecution.objects.aggregate(
        total=Count("id"),
        running=Count("id", filter=Q(status="running")),
        completed=Count("id", filter=Q(status="completed")),
        failed=Count("id", filter=Q(status="failed")),
        cancelled=Count("id", filter=Q(status="cancelled")),
        paused=Count("id", filter=Q(status="paused")),
    )

    # --- Template stats ---
    template_qs = FlowTemplate.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(is_draft=False)),
        draft=Count("id", filter=Q(is_draft=True)),
    )

    # --- User stats ---
    total_users = User.objects.count()
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_users_7d = (
        User.objects.filter(
            Q(flowexecution__created_at__gte=seven_days_ago)
            | Q(flowtemplate__created_at__gte=seven_days_ago)
        )
        .distinct()
        .count()
    )

    # --- Node / duration stats via OpsLog ---
    duration_agg = FlowExecution.objects.filter(
        started_at__isnull=False, ended_at__isnull=False
    ).aggregate(avg_duration=Avg("ended_at" - "started_at"))

    total_nodes = OpsLog.objects.count()

    # --- Success rate ---
    total_finished = (status_qs["completed"] or 0) + (status_qs["failed"] or 0)
    success_rate = (
        round(status_qs["completed"] / total_finished * 100, 1)
        if total_finished
        else 0
    )

    avg_duration_sec = 0
    if duration_agg["avg_duration"] is not None:
        avg_duration_sec = round(duration_agg["avg_duration"].total_seconds())

    data = {
        "total_executions": status_qs["total"] or 0,
        "running_executions": status_qs["running"] or 0,
        "completed_executions": status_qs["completed"] or 0,
        "failed_executions": status_qs["failed"] or 0,
        "cancelled_executions": status_qs["cancelled"] or 0,
        "paused_executions": status_qs["paused"] or 0,
        "total_templates": template_qs["total"] or 0,
        "published_templates": template_qs["published"] or 0,
        "draft_templates": template_qs["draft"] or 0,
        "total_users": total_users,
        "active_users_7d": active_users_7d,
        "total_nodes_executed": total_nodes,
        "avg_duration_sec": avg_duration_sec,
        "success_rate": success_rate,
    }
    return Response({"code": 2000, "msg": "success", "data": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_trend(request):
    """Return execution trend data per day for the last N days (default 30)."""
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)

    from django.db.models.functions import TruncDate

    rows = (
        FlowExecution.objects.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date", "status")
        .annotate(cnt=Count("id"))
        .order_by("date")
    )

    # Group by date
    trend_map: dict[str, dict] = {}
    for r in rows:
        d = str(r["date"])
        if d not in trend_map:
            trend_map[d] = {"date": d, "total": 0, "completed": 0, "failed": 0, "cancelled": 0, "avg_duration": 0}
        trend_map[d]["total"] += r["cnt"]
        if r["status"] == "completed":
            trend_map[d]["completed"] += r["cnt"]
        elif r["status"] == "failed":
            trend_map[d]["failed"] += r["cnt"]
        elif r["status"] == "cancelled":
            trend_map[d]["cancelled"] += r["cnt"]

    # Fill in missing dates with zero
    result = []
    for i in range(days):
        d = (timezone.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = trend_map.get(d, {"date": d, "total": 0, "completed": 0, "failed": 0, "cancelled": 0, "avg_duration": 0})
        result.append(entry)

    return Response({"code": 2000, "msg": "success", "data": result})
