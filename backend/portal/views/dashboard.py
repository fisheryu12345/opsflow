"""Portal dashboard — aggregate data from all modules

运维门户首页聚合数据接口
"""

import logging
from datetime import datetime, timedelta

from django.utils import timezone
from common.utils.json_response import DetailResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

FSM = "portal_dashboard"


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """获取门户首页聚合数据"""
    user = request.user
    data = {
        'user_info': _get_user_info(user),
        'incident_stats': _get_incident_stats(),
        'alert_stats': _get_alert_stats(),
        'execution_stats': _get_execution_stats(),
        'itsm_ticket_stats': _get_itsm_ticket_stats(),
        'opsflow_template_stats': _get_opsflow_template_stats(),
        'my_tasks': _get_my_tasks(user),
        'module_counts': _get_module_counts(),
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
        'tickets': _get_itsm_ticket_stats(),
        'templates': _get_opsflow_template_stats(),
    }
    return DetailResponse(data=data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_activity(request):
    """获取近期系统活动 feed

    Query params:
        limit (int): 返回条数，默认 20
        hours (int): 查询最近几小时，默认 72
    """
    limit = min(int(request.query_params.get('limit', 20)), 100)
    hours = int(request.query_params.get('hours', 72))
    since = timezone.now() - timedelta(hours=hours)

    activities = []

    # 1. OpsFlow 执行记录
    try:
        from opsflow.models import FlowExecution
        executions = FlowExecution.objects.filter(
            created_at__gte=since
        ).select_related('template', 'created_by').order_by('-created_at')[:limit]
        for exe in executions:
            activities.append({
                'type': 'execution',
                'id': exe.id,
                'title': f"流程执行: {exe.template.name if exe.template else 'N/A'}",
                'status': exe.get_status_display(),
                'user': exe.created_by.username if exe.created_by else '',
                'created_at': exe.created_at,
                'url': f'/apps/opsflow/execution/{exe.id}',
            })
    except Exception as e:
        logger.warning("[%s] Failed to load executions: %s", FSM, e)

    # 2. ITSM 工单活动
    try:
        from itsm.models import Ticket
        tickets = Ticket.objects.filter(
            create_datetime__gte=since
        ).select_related('creator').order_by('-create_datetime')[:limit]
        for t in tickets:
            activities.append({
                'type': 'ticket',
                'id': t.id,
                'title': f"工单: {t.title}",
                'status': t.get_current_status_display() if hasattr(t, 'get_current_status_display') else t.current_status,
                'user': t.creator.username if t.creator else '',
                'created_at': t.create_datetime,
                'url': f'/apps/itsm/ticket/{t.id}',
                'sn': t.sn,
            })
    except Exception as e:
        logger.warning("[%s] Failed to load tickets: %s", FSM, e)

    # 3. 告警活动
    try:
        from monitor.models.alert import AlertEvent
        alerts = AlertEvent.objects.filter(
            fired_at__gte=since
        ).order_by('-fired_at')[:limit]
        for a in alerts:
            activities.append({
                'type': 'alert',
                'id': a.id,
                'title': f"告警: {a.title or a.alert_name or 'N/A'}",
                'status': a.get_status_display() if hasattr(a, 'get_status_display') else a.status,
                'user': '',
                'created_at': a.fired_at,
                'url': f'/apps/monitor/alert/{a.id}',
            })
    except Exception as e:
        logger.warning("[%s] Failed to load alerts: %s", FSM, e)

    # 4. CMDB 变更活动
    try:
        from cmdb.models import OperationLog
        cmdb_logs = OperationLog.objects.filter(
            create_datetime__gte=since
        ).order_by('-create_datetime')[:limit]
        for log in cmdb_logs:
            activities.append({
                'type': 'cmdb',
                'id': log.id,
                'title': f"CMDB: {log.operation or '变更'}",
                'status': log.status if hasattr(log, 'status') else 'done',
                'user': log.operator if hasattr(log, 'operator') else '',
                'created_at': log.create_datetime,
                'url': f'/apps/cmdb',
            })
    except Exception as e:
        logger.warning("[%s] Failed to load CMDB logs: %s", FSM, e)

    # 按时间排序并截取
    activities.sort(key=lambda a: a.get('created_at') or datetime.min, reverse=True)
    return DetailResponse(data=activities[:limit])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def favorites(request):
    """获取用户的收藏模板/操作"""
    user = request.user
    data = {
        'templates': [],
        'recent_actions': [],
    }

    # 1. 收藏的 OpsFlow 模板
    try:
        from opsflow.models import TemplateCollect
        collects = TemplateCollect.objects.filter(
            user=user
        ).select_related('template').order_by('-create_datetime')[:10]
        data['templates'] = [
            {
                'id': c.template.id,
                'name': c.template.name,
                'category': c.template.category.name if hasattr(c.template, 'category') and c.template.category else '',
                'description': c.template.description,
                'url': f'/apps/opsflow/template/{c.template.id}',
            }
            for c in collects if c.template
        ]
    except Exception as e:
        logger.warning("[%s] Failed to load favorites: %s", FSM, e)

    # 2. 最近操作记录
    try:
        from opsflow.models import OperationRecord
        records = OperationRecord.objects.filter(
            operator=user.username
        ).order_by('-create_datetime')[:5]
        data['recent_actions'] = [
            {
                'id': r.id,
                'action': r.action,
                'resource_type': r.resource_type if hasattr(r, 'resource_type') else '',
                'resource_id': r.resource_id if hasattr(r, 'resource_id') else '',
                'detail': r.detail if hasattr(r, 'detail') else '',
                'created_at': r.create_datetime,
            }
            for r in records
        ]
    except Exception as e:
        logger.warning("[%s] Failed to load recent actions: %s", FSM, e)

    return DetailResponse(data=data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def health(request):
    """系统健康状态 — 各模块基本健康检查"""
    checks = {}

    # 数据库检查
    try:
        from django.db import connections
        connections['default'].cursor().execute('SELECT 1')
        checks['database'] = {'status': 'up', 'latency_ms': 0}
    except Exception as e:
        checks['database'] = {'status': 'down', 'error': str(e)}

    # 各模块数据量
    modules = {
        'itsm': ('itsm.models', 'Ticket', 'ticket'),
        'opsflow': ('opsflow.models', 'FlowExecution', 'execution'),
        'cmdb': ('cmdb.models', None, None),
        'monitor': ('monitor.models.alert', 'AlertEvent', 'alert'),
    }

    module_counts = {}
    for name, (mod_path, model_name, _) in modules.items():
        try:
            if model_name:
                mod = __import__(mod_path, fromlist=[model_name])
                cls = getattr(mod, model_name)
                module_counts[name] = cls.objects.count()
            else:
                module_counts[name] = 0
        except Exception:
            module_counts[name] = -1

    checks['module_counts'] = module_counts

    # 系统时间
    checks['server_time'] = timezone.now().isoformat()

    return DetailResponse(data=checks)


# --
# Helper functions
# --

def _get_user_info(user):
    """获取当前用户信息"""
    return {
        'id': user.id,
        'username': user.username,
        'name': user.name if hasattr(user, 'name') else user.username,
        'email': user.email if hasattr(user, 'email') else '',
        'avatar': user.avatar if hasattr(user, 'avatar') else '',
        'last_login': user.last_login,
        'is_superuser': user.is_superuser if hasattr(user, 'is_superuser') else False,
    }


def _get_incident_stats():
    """获取工单统计"""
    try:
        from itsm.models.incident import Incident
        today = timezone.now().date()
        return {
            'total': Incident.objects.count(),
            'open': Incident.objects.filter(status__in=['new', 'assigned', 'in_progress']).count(),
            'overdue': Incident.objects.filter(sla_status='breached').count(),
            'resolved_today': Incident.objects.filter(
                status='resolved', update_datetime__date=today
            ).count(),
        }
    except Exception:
        return {'total': 0, 'open': 0, 'overdue': 0, 'resolved_today': 0}


def _get_alert_stats():
    """获取告警统计"""
    try:
        from monitor.models.alert import AlertEvent
        today = timezone.now().date()
        firing_count = AlertEvent.objects.filter(status='firing').count()
        acknowledged = AlertEvent.objects.filter(status='acknowledged').count()
        today_count = AlertEvent.objects.filter(fired_at__date=today).count()
        return {
            'firing': firing_count,
            'acknowledged': acknowledged,
            'total_today': today_count,
            'total': firing_count + acknowledged,
        }
    except Exception:
        return {'firing': 0, 'acknowledged': 0, 'total_today': 0, 'total': 0}


def _get_execution_stats():
    """获取执行统计"""
    try:
        from job_platform.models import JobExecution
        today = timezone.now().date()
        return {
            'running': JobExecution.objects.filter(status='running').count(),
            'pending': JobExecution.objects.filter(status='pending').count(),
            'success_today': JobExecution.objects.filter(
                status='success', finished_at__date=today
            ).count(),
            'failed_today': JobExecution.objects.filter(
                status='failed', finished_at__date=today
            ).count(),
        }
    except Exception:
        return {'running': 0, 'pending': 0, 'success_today': 0, 'failed_today': 0}


def _get_itsm_ticket_stats():
    """获取 ITSM 工单统计"""
    try:
        from itsm.models import Ticket
        today = timezone.now().date()
        return {
            'draft': Ticket.objects.filter(current_status='draft').count(),
            'running': Ticket.objects.filter(current_status='running').count(),
            'finished': Ticket.objects.filter(current_status='finished').count(),
            'created_today': Ticket.objects.filter(create_datetime__date=today).count(),
            'total': Ticket.objects.count(),
        }
    except Exception:
        return {'draft': 0, 'running': 0, 'finished': 0, 'created_today': 0, 'total': 0}


def _get_opsflow_template_stats():
    """获取 OpsFlow 模板统计"""
    try:
        from opsflow.models import FlowTemplate
        return {
            'total': FlowTemplate.objects.count(),
            'published': FlowTemplate.objects.filter(is_draft=False).count(),
            'draft': FlowTemplate.objects.filter(is_draft=True).count(),
        }
    except Exception:
        return {'total': 0, 'published': 0, 'draft': 0}


def _get_my_tasks(user):
    """获取当前用户的待办事项"""
    tasks = []
    try:
        from itsm.models.incident import Incident, Change
        incidents = Incident.objects.filter(
            assignee=user, status__in=['new', 'assigned', 'in_progress']
        )
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

    # ITSM Ticket 待审批
    try:
        from itsm.models import Ticket, SignTask, TicketStatus
        pending_signs = SignTask.objects.filter(
            processor=user.username,
            status_val='pending',
        ).select_related('ticket')[:10]
        for s in pending_signs:
            tasks.append({
                'type': 'approval',
                'id': s.ticket.id,
                'title': f"审批: {s.ticket.title}",
                'status': 'pending_approval',
                'priority': s.ticket.priority,
                'created_at': s.ticket.create_datetime,
                'sn': s.ticket.sn,
            })
    except Exception:
        pass

    # OpsFlow 待审批执行
    try:
        from opsflow.models import FlowExecution
        pending_execs = FlowExecution.objects.filter(
            status='pending_approval',
            created_by=user,
        ).select_related('template')[:10]
        for e in pending_execs:
            tasks.append({
                'type': 'execution_approval',
                'id': e.id,
                'title': f"流程审批: {e.template.name if e.template else 'N/A'}",
                'status': 'pending_approval',
                'priority': '',
                'created_at': e.created_at,
            })
    except Exception:
        pass

    tasks.sort(key=lambda t: t.get('created_at') or datetime.min, reverse=True)
    return tasks[:20]


def _get_module_counts():
    """获取各模块核心数据量"""
    counts = {}
    try:
        from itsm.models import Ticket
        counts['itsm_tickets'] = Ticket.objects.count()
    except Exception:
        counts['itsm_tickets'] = 0

    try:
        from opsflow.models import FlowTemplate
        counts['opsflow_templates'] = FlowTemplate.objects.count()
    except Exception:
        counts['opsflow_templates'] = 0

    try:
        from opsflow.models import FlowExecution
        counts['opsflow_executions'] = FlowExecution.objects.count()
    except Exception:
        counts['opsflow_executions'] = 0

    try:
        from cmdb.models.host import Host
        counts['cmdb_hosts'] = Host.objects.count()
    except Exception:
        counts['cmdb_hosts'] = 0

    try:
        from itsm.models.incident import Incident
        counts['incidents'] = Incident.objects.count()
    except Exception:
        counts['incidents'] = 0

    try:
        from monitor.models.alert import AlertEvent
        counts['alerts'] = AlertEvent.objects.count()
    except Exception:
        counts['alerts'] = 0

    return counts
