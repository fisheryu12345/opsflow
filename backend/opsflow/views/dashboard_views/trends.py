"""Dashboard — 执行趋势 + 成功率趋势端点"""

from datetime import timedelta

from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.db.models.functions import TruncDate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from common.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response

from ...models import FlowExecution


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_trend(request):
    """Return execution trend data per day for the last N days (default 30).

    Includes avg_duration (average duration of completed executions on that day, in seconds).
    """
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)

    rows = (
        FlowExecution.objects.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date", "status")
        .annotate(cnt=Count("id"))
        .order_by("date")
    )

    # Per-date avg duration (only for executions with started_at and ended_at)
    duration_rows = (
        FlowExecution.objects.filter(
            created_at__gte=since,
            started_at__isnull=False,
            ended_at__isnull=False,
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(avg_dur=Avg(F("ended_at") - F("started_at")))
        .order_by("date")
    )
    dur_map: dict[str, int] = {}
    for r in duration_rows:
        d = str(r["date"])
        if r["avg_dur"] is not None:
            dur_map[d] = round(r["avg_dur"].total_seconds())

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
        entry["avg_duration"] = dur_map.get(d, 0)
        result.append(entry)

    return DetailResponse(data=result)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_success_rate_trend(request):
    """每日成功率趋势 — 按日聚合执行成功/失败数量及成功率"""
    days = int(request.GET.get("days", 30))
    since = timezone.now() - timedelta(days=days)

    rows = (
        FlowExecution.objects.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date", "status")
        .annotate(cnt=Count("id"))
        .order_by("date")
    )

    trend_map = {}
    for r in rows:
        d = str(r["date"])
        if d not in trend_map:
            trend_map[d] = {"date": d, "total": 0, "completed": 0, "failed": 0, "rate": 0.0}
        trend_map[d]["total"] += r["cnt"]
        if r["status"] == "completed":
            trend_map[d]["completed"] += r["cnt"]
        elif r["status"] == "failed":
            trend_map[d]["failed"] += r["cnt"]

    result = []
    for i in range(days):
        d = (timezone.now() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        entry = trend_map.get(d, {"date": d, "total": 0, "completed": 0, "failed": 0, "rate": 0.0})
        if entry["total"] > 0:
            entry["rate"] = round(entry["completed"] / entry["total"] * 100, 1)
        result.append(entry)
    return DetailResponse(data=result)
