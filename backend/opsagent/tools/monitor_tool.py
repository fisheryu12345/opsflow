# -*- coding: utf-8 -*-
"""Monitor query tool — Agent can query alerts and monitoring metrics

监控查询工具 — Agent 可查询当前告警事件、查看监控指标
"""

from opsagent.tools.base import tool
from opsagent.core.types import RiskLevel, ToolResult


@tool(
    name="monitor_query",
    description="Query monitoring alerts and events. Supports listing active alerts, "
                "searching alert events, and getting alert details.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_alerts", "get_alert_detail", "search_events",
                         "alert_summary"],
                "description": "Query action: "
                               "list_alerts=list firing/active alerts; "
                               "get_alert_detail=get full detail of a specific alert; "
                               "search_events=search raw alert events by keyword or filter; "
                               "alert_summary=get summary statistics of alerts",
            },
            "alert_id": {
                "type": "string",
                "description": "Alert ID (the alert_id field, not DB id). "
                               "Required for get_alert_detail.",
            },
            "status": {
                "type": "string",
                "description": "Filter by status: firing, acknowledged, resolved, "
                               "silenced, closed (default: firing)",
                "default": "firing",
            },
            "severity": {
                "type": "integer",
                "description": "Filter by severity: 1=fatal, 2=warning, 3=info",
            },
            "search": {
                "type": "string",
                "description": "Keyword search in alert title/description",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (1-100, default 20)",
                "default": 20,
            },
        },
        "required": ["action"],
    },
    risk_level=RiskLevel.READ,
    requires_approval=False,
)
async def monitor_query(action: str, alert_id: str = '', status: str = 'firing',
                        severity: int = 0, search: str = '', limit: int = 20, **kwargs):
    """Query monitoring alerts and events

    Queries the monitor app's Alert and AlertEvent models to retrieve
    current alert status, event history, and summary statistics.
    """
    limit = max(1, min(100, limit or 20))

    try:
        if action == 'list_alerts':
            return await _list_alerts(status, severity, search, limit)
        elif action == 'get_alert_detail':
            return await _get_alert_detail(alert_id)
        elif action == 'search_events':
            return await _search_events(status, severity, search, limit)
        elif action == 'alert_summary':
            return await _alert_summary()
        else:
            return ToolResult(
                success=False, output='',
                error=f'Unknown action: {action}',
            )
    except Exception as e:
        return ToolResult(success=False, output='', error=f'Monitor query failed: {e}')


SEVERITY_LABELS = {1: 'Fatal', 2: 'Warning', 3: 'Info'}


async def _list_alerts(status: str, severity: int, search: str, limit: int) -> ToolResult:
    """List alerts with optional filters — 列出告警并支持过滤"""
    from monitor.models.alert import Alert

    filters = {}
    if status:
        filters['status'] = status
    if severity:
        filters['severity'] = severity

    queryset = Alert.objects.filter(**filters)

    if search:
        from django.db.models import Q
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    alerts = queryset.order_by('-fired_at')[:limit]
    alert_list = []

    lines = [f'Alerts (status={status}, showing {len(alerts)}):']
    for a in alerts:
        sev_label = SEVERITY_LABELS.get(a.severity, str(a.severity))
        alert_list.append({
            'alert_id': a.alert_id,
            'title': a.title,
            'severity': a.severity,
            'severity_label': sev_label,
            'status': a.status,
            'fired_at': str(a.fired_at),
            'current_value': a.current_value,
            'metric_unit': a.metric_unit,
            'event_count': a.event_count,
            'assignee': a.assignee,
        })
        lines.append(f'  [{sev_label}] {a.title}')
        lines.append(f'      ID: {a.alert_id} | Status: {a.status}')
        lines.append(f'      Fired: {a.fired_at}')
        if a.current_value is not None:
            unit = a.metric_unit or ''
            lines.append(f'      Value: {a.current_value}{unit}')
        if a.assignee:
            lines.append(f'      Assignee: {a.assignee}')

    if not alerts:
        return ToolResult(
            success=True,
            output=f'No alerts found with status="{status}".',
            metadata={'status': status, 'total': 0},
        )

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'status': status, 'total': len(alert_list), 'alerts': alert_list},
    )


async def _get_alert_detail(alert_id: str) -> ToolResult:
    """Get detailed info for a specific alert — 获取单个告警详情"""
    if not alert_id:
        return ToolResult(success=False, output='', error='alert_id is required')

    from monitor.models.alert import Alert, AlertLog, AlertEvent

    try:
        alert = Alert.objects.get(alert_id=alert_id)
    except Alert.DoesNotExist:
        return ToolResult(success=False, output='', error=f'Alert not found: {alert_id}')

    sev_label = SEVERITY_LABELS.get(alert.severity, str(alert.severity))

    # Get related events — 获取相关事件
    events = AlertEvent.objects.filter(
        strategy=alert.strategy,
        target=alert.cmdb_host_id or '',
    )[:10]
    event_list = []
    for e in events:
        event_list.append({
            'event_id': e.event_id,
            'alert_name': e.alert_name,
            'status': e.status,
            'time': str(e.time),
            'metric_value': e.metric_value,
        })

    # Get logs — 获取流水日志
    logs = AlertLog.objects.filter(alert=alert).order_by('-create_time')[:20]
    log_list = []
    for l in logs:
        log_list.append({
            'operate': l.operate,
            'operator': l.operator,
            'time': str(l.create_time),
            'description': l.description,
        })

    lines = [f'Alert Detail: {alert.title}']
    lines.append(f'  Alert ID: {alert.alert_id}')
    lines.append(f'  Severity: {sev_label} ({alert.severity})')
    lines.append(f'  Status: {alert.status}')
    lines.append(f'  Fired At: {alert.fired_at}')
    if alert.resolved_at:
        lines.append(f'  Resolved At: {alert.resolved_at}')
    lines.append(f'  Event Count: {alert.event_count}')
    if alert.current_value is not None:
        unit = alert.metric_unit or ''
        lines.append(f'  Current Value: {alert.current_value}{unit}')
    lines.append(f'  Description: {alert.description or "N/A"}')

    if log_list:
        lines.append(f'\n  Recent Activity ({len(log_list)}):')
        for l in log_list[:5]:
            lines.append(f'    [{l["time"]}] {l["operate"]} by {l["operator"]} — {l["description"][:100]}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={
            'alert_id': alert.alert_id,
            'title': alert.title,
            'status': alert.status,
            'severity': alert.severity,
            'events_count': len(event_list),
            'logs_count': len(log_list),
            'events': event_list,
            'logs': log_list,
        },
    )


async def _search_events(status: str, severity: int, search: str, limit: int) -> ToolResult:
    """Search raw alert events — 搜索原始告警事件"""
    from monitor.models.alert import AlertEvent
    from django.db.models import Q

    filters = {}
    if status:
        filters['status'] = status
    if severity:
        filters['severity'] = severity

    queryset = AlertEvent.objects.filter(**filters)

    if search:
        queryset = queryset.filter(
            Q(alert_name__icontains=search)
            | Q(description__icontains=search)
            | Q(target__icontains=search)
        )

    events = queryset.order_by('-time')[:limit]
    event_list = []

    lines = [f'Alert Events (status={status}, showing {len(events)}):']
    for e in events:
        sev_label = SEVERITY_LABELS.get(e.severity, str(e.severity))
        event_list.append({
            'event_id': e.event_id,
            'alert_name': e.alert_name,
            'severity': e.severity,
            'status': e.status,
            'target': e.target,
            'time': str(e.time),
            'metric': e.metric,
            'metric_value': e.metric_value,
        })
        lines.append(f'  [{sev_label}] {e.alert_name}')
        lines.append(f'      ID: {e.event_id} | Target: {e.target}')
        lines.append(f'      Time: {e.time} | Status: {e.status}')
        if e.metric_value is not None:
            lines.append(f'      Metric: {e.metric} = {e.metric_value}')

    if not events:
        return ToolResult(
            success=True,
            output=f'No events found matching criteria.',
            metadata={'status': status, 'total': 0},
        )

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'status': status, 'total': len(event_list), 'events': event_list},
    )


async def _alert_summary() -> ToolResult:
    """Get alert summary statistics — 获取告警汇总统计"""
    from monitor.models.alert import Alert
    from django.db.models import Count

    # Total counts by status — 按状态统计
    status_counts = Alert.objects.values('status').annotate(count=Count('id'))
    status_map = {s['status']: s['count'] for s in status_counts}

    # Total counts by severity — 按级别统计
    severity_counts = Alert.objects.values('severity').annotate(count=Count('id'))

    # Recent firing alerts — 最近的触发中告警
    recent = Alert.objects.filter(status='firing').order_by('-fired_at')[:10]

    lines = ['Alert Summary:']
    lines.append(f'  Firing: {status_map.get("firing", 0)}')
    lines.append(f'  Acknowledged: {status_map.get("acknowledged", 0)}')
    lines.append(f'  Resolved: {status_map.get("resolved", 0)}')
    lines.append(f'  Silenced: {status_map.get("silenced", 0)}')
    lines.append(f'  Closed: {status_map.get("closed", 0)}')
    lines.append(f'  Total: {sum(status_map.values())}')

    lines.append('\n  By Severity:')
    for sc in severity_counts:
        sev_label = SEVERITY_LABELS.get(sc['severity'], str(sc['severity']))
        lines.append(f'    {sev_label}: {sc["count"]}')

    if recent:
        lines.append(f'\n  Recent Firing Alerts ({len(recent)}):')
        for a in recent:
            sev_label = SEVERITY_LABELS.get(a.severity, str(a.severity))
            lines.append(f'    [{sev_label}] {a.title} (since {a.fired_at})')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={
            'status_counts': status_map,
            'total': sum(status_map.values()),
            'recent_firing': [
                {'alert_id': a.alert_id, 'title': a.title, 'severity': a.severity,
                 'fired_at': str(a.fired_at)}
                for a in recent
            ],
        },
    )
