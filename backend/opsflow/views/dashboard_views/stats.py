"""Dashboard — 聚合统计 + 调度统计端点"""

import logging

from datetime import timedelta

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ...models import FlowTemplate, FlowExecution, OpsLog, SchedulePlan

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Return aggregate statistics for the opsflow dashboard (including scheduler)."""
    User = get_user_model()

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
    ).aggregate(avg_duration=Avg(F("ended_at") - F("started_at")))

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

    # --- Scheduler stats ---
    schedule_status_qs = SchedulePlan.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=SchedulePlan.Status.ACTIVE)),
        paused=Count("id", filter=Q(status=SchedulePlan.Status.PAUSED)),
        completed=Count("id", filter=Q(status=SchedulePlan.Status.COMPLETED)),
        expired=Count("id", filter=Q(status=SchedulePlan.Status.EXPIRED)),
        total_runs=Sum("total_run_count"),
    )

    # Next scheduled run (soonest future execution)
    now_naive = timezone.now().replace(tzinfo=None)
    next_schedule = (
        SchedulePlan.objects.filter(
            is_active=True,
            next_run_at__isnull=False,
            next_run_at__gte=now_naive,
        )
        .order_by("next_run_at")
        .first()
    )
    next_scheduled_run = (
        {"id": next_schedule.id, "name": next_schedule.name, "next_run_at": next_schedule.next_run_at.strftime("%Y-%m-%d %H:%M:%S")}
        if next_schedule
        else None
    )

    # Schedule-triggered execution stats (via schedule_plan FK)
    sched_exec_qs = FlowExecution.objects.filter(
        schedule_plan__isnull=False
    ).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status="completed")),
        failed=Count("id", filter=Q(status="failed")),
        running=Count("id", filter=Q(status="running")),
        paused=Count("id", filter=Q(status="paused")),
        cancelled=Count("id", filter=Q(status="cancelled")),
    )
    sched_total_finished = (sched_exec_qs["completed"] or 0) + (sched_exec_qs["failed"] or 0)
    schedule_success_rate = (
        round(sched_exec_qs["completed"] / sched_total_finished * 100, 1)
        if sched_total_finished
        else 0
    )

    data = {
        # Executions
        "total_executions": status_qs["total"] or 0,
        "running_executions": status_qs["running"] or 0,
        "completed_executions": status_qs["completed"] or 0,
        "failed_executions": status_qs["failed"] or 0,
        "cancelled_executions": status_qs["cancelled"] or 0,
        "paused_executions": status_qs["paused"] or 0,
        # Templates
        "total_templates": template_qs["total"] or 0,
        "published_templates": template_qs["published"] or 0,
        "draft_templates": template_qs["draft"] or 0,
        # Users
        "total_users": total_users,
        "active_users_7d": active_users_7d,
        # Performance
        "total_nodes_executed": total_nodes,
        "avg_duration_sec": avg_duration_sec,
        "success_rate": success_rate,
        # Scheduler
        "total_schedule_plans": schedule_status_qs["total"] or 0,
        "active_schedule_plans": schedule_status_qs["active"] or 0,
        "paused_schedule_plans": schedule_status_qs["paused"] or 0,
        "completed_schedule_plans": schedule_status_qs["completed"] or 0,
        "expired_schedule_plans": schedule_status_qs["expired"] or 0,
        "total_scheduled_runs": schedule_status_qs["total_runs"] or 0,
        "next_scheduled_run": next_scheduled_run,
        "scheduled_executions_total": sched_exec_qs["total"] or 0,
        "scheduled_executions_completed": sched_exec_qs["completed"] or 0,
        "scheduled_executions_failed": sched_exec_qs["failed"] or 0,
        "scheduled_executions_running": sched_exec_qs["running"] or 0,
        "schedule_success_rate": schedule_success_rate,
    }
    return Response({"code": 2000, "msg": "success", "data": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_schedule_stats(request):
    """Return detailed scheduler statistics for the dashboard."""
    # Schedule plan type distribution
    type_dist = (
        SchedulePlan.objects.values("schedule_type")
        .annotate(cnt=Count("id"))
        .order_by("schedule_type")
    )
    type_dist_map = {r["schedule_type"]: r["cnt"] for r in type_dist}

    # Top schedules by execution count (top 8)
    top_schedules = (
        SchedulePlan.objects.filter(total_run_count__gt=0)
        .select_related("template")
        .order_by("-total_run_count")[:8]
    )
    top_schedules_data = [
        {
            "id": s.id,
            "name": s.name,
            "template_name": s.template.name if s.template else "",
            "schedule_type": s.schedule_type,
            "total_run_count": s.total_run_count,
            "last_run_at": s.last_run_at.strftime("%Y-%m-%d %H:%M") if s.last_run_at else None,
            "next_run_at": s.next_run_at.strftime("%Y-%m-%d %H:%M") if s.next_run_at else None,
            "is_active": s.is_active,
        }
        for s in top_schedules
    ]

    # Schedule plan trend (daily count of schedule-triggered executions)
    from django.db.models.functions import TruncDate
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)
    sched_rows = (
        FlowExecution.objects.filter(
            created_at__gte=since,
            schedule_plan__isnull=False,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date", "status")
        .annotate(cnt=Count("id"))
        .order_by("date")
    )

    sched_trend_map: dict[str, dict] = {}
    for r in sched_rows:
        d = str(r["date"])
        if d not in sched_trend_map:
            sched_trend_map[d] = {"date": d, "total": 0, "completed": 0, "failed": 0}
        sched_trend_map[d]["total"] += r["cnt"]
        if r["status"] == "completed":
            sched_trend_map[d]["completed"] += r["cnt"]
        elif r["status"] == "failed":
            sched_trend_map[d]["failed"] += r["cnt"]

    # Fill in missing dates with zero
    sched_trend_result = []
    for i in range(days):
        d = (timezone.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = sched_trend_map.get(d, {"date": d, "total": 0, "completed": 0, "failed": 0})
        sched_trend_result.append(entry)

    data = {
        "type_distribution": type_dist_map,
        "top_schedules": top_schedules_data,
        "trend": sched_trend_result,
    }
    return Response({"code": 2000, "msg": "success", "data": data})
