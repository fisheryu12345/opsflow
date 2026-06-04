"""Portal dashboard — aggregate data from all modules

运维门户首页聚合数据接口
"""

from dvadmin.utils.json_response import DetailResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """获取门户首页聚合数据"""
    user = request.user
    data = {
        'incident_stats': _get_incident_stats(),
        'alert_stats': _get_alert_stats(),
        'execution_stats': _get_execution_stats(),
        'my_tasks': _get_my_tasks(user),
    }
    return DetailResponse(data=data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_tasks(request):
    """获取我的待办/待审批"""
    user = request.user
    data = _get_my_tasks(user)
    return DetailResponse(data=data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quick_stats(request):
    """快速概览统计"""
    data = {
        'incidents': _get_incident_stats(),
        'alerts': _get_alert_stats(),
        'executions': _get_execution_stats(),
    }
    return DetailResponse(data=data)


def _get_incident_stats():
    """获取工单统计"""
    try:
        from itsm.models.incident import Incident
        return {
            'total': Incident.objects.count(),
            'open': Incident.objects.filter(status__in=['new', 'assigned', 'in_progress']).count(),
            'overdue': Incident.objects.filter(sla_status='breached').count(),
        }
    except Exception:
        return {'total': 0, 'open': 0, 'overdue': 0}


def _get_alert_stats():
    """获取告警统计"""
    try:
        from monitor.models.alert import AlertEvent
        return {
            'firing': AlertEvent.objects.filter(status='firing').count(),
            'acknowledged': AlertEvent.objects.filter(status='acknowledged').count(),
            'total_today': AlertEvent.objects.filter(fired_at__date='today').count(),
        }
    except Exception:
        return {'firing': 0, 'acknowledged': 0, 'total_today': 0}


def _get_execution_stats():
    """获取执行统计"""
    try:
        from job_platform.models import JobExecution
        return {
            'running': JobExecution.objects.filter(status='running').count(),
            'pending': JobExecution.objects.filter(status='pending').count(),
            'success_today': JobExecution.objects.filter(
                status='success', finished_at__date='today'
            ).count(),
        }
    except Exception:
        return {'running': 0, 'pending': 0, 'success_today': 0}


def _get_my_tasks(user):
    """获取当前用户的待办事项"""
    tasks = []
    try:
        from itsm.models.incident import Incident, Change
        incidents = Incident.objects.filter(assignee=user, status__in=['new', 'assigned', 'in_progress'])
        for inc in incidents:
            tasks.append({
                'type': 'incident',
                'id': inc.incident_id,
                'title': inc.title,
                'status': inc.status,
                'priority': inc.priority,
                'created_at': inc.create_datetime,
            })
        changes = Change.objects.filter(assignee=user, status='pending_approval')
        for ch in changes:
            tasks.append({
                'type': 'change',
                'id': ch.change_id,
                'title': ch.title,
                'status': ch.status,
                'risk_level': ch.risk_level,
                'created_at': ch.create_datetime,
            })
    except Exception:
        pass
    tasks.sort(key=lambda t: t.get('created_at') or '', reverse=True)
    return tasks[:20]
