"""Dashboard — 分析/分布端点（top_templates, user_activity, 分布, 排行等）"""

from datetime import timedelta

from django.db.models import Count, Avg, Q, F, Max, Sum, Case, Value, IntegerField, When
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from common.utils.json_response import DetailResponse, ErrorResponse
from rest_framework.response import Response

from ...models import FlowExecution, NodeExecutionTrace


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_top_templates(request):
    """Top N templates ranked by execution count (with success rate and average duration)"""
    limit = int(request.GET.get("limit", 8))

    rows = (
        FlowExecution.objects.values(tid=F("template_id"), template_name=F("template__name"))
        .annotate(
            count=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            failed=Count("id", filter=Q(status="failed")),
            avg_duration=Avg(F("ended_at") - F("started_at")),
        )
        .order_by("-count")[:limit]
    )

    data = []
    for r in rows:
        total_finished = (r["completed"] or 0) + (r["failed"] or 0)
        success_rate = round(r["completed"] / total_finished * 100, 1) if total_finished else 0
        avg_sec = 0
        if r["avg_duration"] is not None:
            avg_sec = round(r["avg_duration"].total_seconds())
        data.append({
            "id": r["tid"],
            "name": r["template_name"],
            "count": r["count"],
            "avg_duration": avg_sec,
            "success_rate": success_rate,
        })
    return DetailResponse(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_user_activity(request):
    """User execution activity statistics"""
    limit = int(request.GET.get("limit", 10))
    rows = (
        FlowExecution.objects.values(username=F("created_by__username"))
        .annotate(
            execution_count=Count("id"),
            template_count=Count("template_id", distinct=True),
            last_active=Max("created_at"),
        )
        .order_by("-execution_count")[:limit]
    )
    data = []
    for r in rows:
        data.append({
            "username": r["username"] or "unknown",
            "execution_count": r["execution_count"],
            "template_count": r["template_count"],
            "last_active": r["last_active"].strftime("%Y-%m-%d") if r["last_active"] else None,
        })
    return DetailResponse(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_status_distribution(request):
    """Execution status distribution"""
    status_labels = {
        "pending": "Pending", "running": "Running", "completed": "Completed",
        "failed": "Failed", "cancelled": "Cancelled", "paused": "Paused",
    }
    rows = FlowExecution.objects.values("status").annotate(count=Count("id")).order_by("status")
    data = [
        {"status": r["status"], "count": r["count"], "label": status_labels.get(r["status"], r["status"])}
        for r in rows
    ]
    return DetailResponse(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_node_type_distribution(request):
    """Node type distribution (aggregated by atom_type from NodeExecutionTrace)"""
    rows = (
        NodeExecutionTrace.objects.values("atom_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:15]
    )
    data = []
    for r in rows:
        label = r["atom_type"] or "unknown"
        data.append({"type": r["atom_type"] or "unknown", "count": r["count"], "label": label})
    return DetailResponse(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_duration_distribution(request):
    """执行耗时分布 — 按耗时区间统计执行次数"""
    from django.utils import timezone

    base = FlowExecution.objects.filter(
        started_at__isnull=False,
        ended_at__isnull=False,
    )
    bucket_map = {
        '0-30s': Case(When(ended_at__lte=F('started_at') + timedelta(seconds=30), then=Value(1)),
                      default=Value(0), output_field=IntegerField()),
        '30s-1m': Case(When(ended_at__gt=F('started_at') + timedelta(seconds=30),
                            ended_at__lte=F('started_at') + timedelta(minutes=1), then=Value(1)),
                       default=Value(0), output_field=IntegerField()),
        '1m-3m': Case(When(ended_at__gt=F('started_at') + timedelta(minutes=1),
                           ended_at__lte=F('started_at') + timedelta(minutes=3), then=Value(1)),
                      default=Value(0), output_field=IntegerField()),
        '3m-5m': Case(When(ended_at__gt=F('started_at') + timedelta(minutes=3),
                           ended_at__lte=F('started_at') + timedelta(minutes=5), then=Value(1)),
                      default=Value(0), output_field=IntegerField()),
        '5m-10m': Case(When(ended_at__gt=F('started_at') + timedelta(minutes=5),
                            ended_at__lte=F('started_at') + timedelta(minutes=10), then=Value(1)),
                       default=Value(0), output_field=IntegerField()),
        '10m-1h': Case(When(ended_at__gt=F('started_at') + timedelta(minutes=10),
                            ended_at__lte=F('started_at') + timedelta(hours=1), then=Value(1)),
                       default=Value(0), output_field=IntegerField()),
        '>1h': Case(When(ended_at__gt=F('started_at') + timedelta(hours=1), then=Value(1)),
                    default=Value(0), output_field=IntegerField()),
    }
    agg = base.aggregate(**{key: Sum(expr) for key, expr in bucket_map.items()})
    buckets = [{"range": key, "count": agg.get(key, 0) or 0} for key in bucket_map]
    return DetailResponse(data=buckets)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_node_duration_top(request):
    """节点耗时排行榜 — Top N 最慢节点类型（从 NodeExecutionTrace 汇总）"""
    limit = int(request.GET.get("limit", 10))
    rows = (
        NodeExecutionTrace.objects
        .filter(duration_ms__isnull=False)
        .values("atom_type")
        .annotate(
            count=Count("id"),
            avg_duration=Avg("duration_ms"),
            max_duration=Max("duration_ms"),
        )
        .order_by("-avg_duration")[:limit]
    )
    data = [
        {
            "atom_type": r["atom_type"] or "unknown",
            "avg_duration": round(r["avg_duration"]) if r["avg_duration"] else 0,
            "count": r["count"],
            "max_duration": r["max_duration"] or 0,
        }
        for r in rows
    ]
    return DetailResponse(data=data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_template_stats(request):
    """模板执行聚合统计 — 每个模板的执行次数/平均耗时/成功率/平均节点数"""
    rows = (
        FlowExecution.objects.values(
            tid=F("template_id"),
            name=F("template__name"),
        )
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="completed")),
            failed=Count("id", filter=Q(status="failed")),
            avg_duration=Avg(F("ended_at") - F("started_at")),
        )
        .order_by("-total")
    )
    data = []
    for r in rows:
        total_finished = (r["completed"] or 0) + (r["failed"] or 0)
        success_rate = round(r["completed"] / total_finished * 100, 1) if total_finished else 0
        avg_sec = 0
        if r["avg_duration"] is not None:
            avg_sec = round(r["avg_duration"].total_seconds())
        data.append({
            "template_id": r["tid"],
            "name": r["name"] or f"Template {r['tid']}",
            "total": r["total"],
            "avg_duration": avg_sec,
            "success_rate": success_rate,
        })
    return DetailResponse(data=data)
