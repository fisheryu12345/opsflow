# -*- coding: utf-8 -*-
"""ITSM Dashboard view — 看板数据聚合

提供工单概览统计、待办任务、趋势图、状态分布、超时工单等接口。
"""

import logging
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet

from dvadmin.utils.json_response import DetailResponse

from itsm.models import Ticket, TicketStatus, SignTask

ACTIVE_STATUSES = ['assigned', 'receiving', 'running']

logger = logging.getLogger(__name__)


class DashboardViewSet(ViewSet):
    """ITSM 看板 — 数据聚合（只读）"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """看板主页聚合数据"""
        return DetailResponse(data={
            'summary': self._summary(request),
            'my_tasks': self._my_tasks(request),
            'trend': self._trend(),
            'status_dist': self._status_dist(),
            'overdue': self._overdue(request),
        })

    @action(methods=['GET'], detail=False)
    def summary(self, request):
        """统计卡片: 我的待办、超时工单、今日解决、平均解决时长"""
        return DetailResponse(data=self._summary(request))

    @action(methods=['GET'], detail=False)
    def my_tasks(self, request):
        """当前用户的待办任务"""
        return DetailResponse(data=self._my_tasks(request))

    @action(methods=['GET'], detail=False)
    def trend(self, request):
        """近30天工单创建趋势"""
        return DetailResponse(data=self._trend())

    @action(methods=['GET'], detail=False)
    def status_dist(self, request):
        """工单状态分布"""
        return DetailResponse(data=self._status_dist())

    @action(methods=['GET'], detail=False)
    def overdue(self, request):
        """超时工单列表"""
        return DetailResponse(data=self._overdue(request))

    # ----- helpers -----

    def _summary(self, request):
        """聚合统计"""
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        user = request.user

        # 我的待办: running 工单中当前用户有审批/处理任务的
        pending_tickets = Ticket.objects.filter(
            current_status__in=ACTIVE_STATUSES,
            status_records__status='RUNNING',
            status_records__processors__icontains=user.username,
        ).distinct().count()

        # 超时工单: running 超过 7 天的工单（简易判定）
        week_ago = timezone.now() - timedelta(days=7)
        overdue_count = Ticket.objects.filter(
            current_status__in=ACTIVE_STATUSES,
            create_datetime__lt=week_ago,
        ).count()

        # 今日 resolved (根据工单状态变更记录)
        today_resolved = Ticket.objects.filter(
            current_status='finished',
            update_datetime__gte=today,
            update_datetime__lt=tomorrow,
        ).count()

        # 平均解决时长（已完成工单: update_datetime - create_datetime）
        finished = Ticket.objects.filter(current_status='finished')
        total_seconds = 0
        total_count = finished.count()
        for t in finished:
            if t.create_datetime and t.update_datetime:
                delta = t.update_datetime - t.create_datetime
                total_seconds += delta.total_seconds()
        avg_time = round(total_seconds / total_count / 3600, 1) if total_count else 0

        return {
            'pending_tickets': pending_tickets,
            'overdue_count': overdue_count,
            'today_resolved': today_resolved,
            'avg_resolution_hours': avg_time,
        }

    def _my_tasks(self, request):
        """当前用户的待办审批/处理任务"""
        user = request.user
        running_statuses = TicketStatus.objects.filter(
            ticket__current_status__in=ACTIVE_STATUSES,
            status='RUNNING',
        ).select_related('ticket')

        tasks = []
        for ts in running_statuses:
            processors = ts.processors or ''
            if user.username in processors:
                tasks.append({
                    'ticket_id': ts.ticket.id,
                    'sn': ts.ticket.sn,
                    'title': ts.ticket.title,
                    'node_name': ts.name,
                    'node_type': ts.type,
                    'priority': ts.ticket.priority,
                    'itsm_type': ts.ticket.itsm_type,
                    'create_datetime': ts.ticket.create_datetime.isoformat() if ts.ticket.create_datetime else '',
                })
        # 按创建时间倒序
        tasks.sort(key=lambda x: x['create_datetime'], reverse=True)
        return tasks

    def _trend(self):
        """近30天工单创建趋势"""
        today = timezone.localdate()
        start = today - timedelta(days=29)
        dates = [start + timedelta(days=i) for i in range(30)]

        # 按日期分组统计
        from django.db.models.functions import TruncDate
        qs = Ticket.objects.filter(
            create_datetime__date__gte=start,
            create_datetime__date__lte=today,
        ).annotate(
            day=TruncDate('create_datetime')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        count_map = {item['day']: item['count'] for item in qs}
        trend_data = []
        for d in dates:
            trend_data.append({
                'date': d.isoformat(),
                'count': count_map.get(d, 0),
            })
        return trend_data

    def _status_dist(self):
        """工单状态分布"""
        qs = Ticket.objects.values('current_status').annotate(
            count=Count('id')
        ).order_by('current_status')
        return list(qs)

    def _overdue(self, request):
        """超时工单列表 — running 超过 7 天"""
        week_ago = timezone.now() - timedelta(days=7)
        qs = Ticket.objects.filter(
            current_status__in=ACTIVE_STATUSES,
            create_datetime__lt=week_ago,
        ).order_by('create_datetime')[:20]
        return [{
            'id': t.id,
            'sn': t.sn,
            'title': t.title,
            'priority': t.priority,
            'itsm_type': t.itsm_type,
            'create_datetime': t.create_datetime.isoformat() if t.create_datetime else '',
            'elapsed_days': (timezone.now() - t.create_datetime).days if t.create_datetime else 0,
        } for t in qs]
