# -*- coding: utf-8 -*-
"""Dashboard views — 监控看板统计端点

12 个统计端点: 概览/趋势/分布/TOP N
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import action

from common.utils.viewset import CustomModelViewSet
from common.utils.json_response import DetailResponse

from ..models import Alert, AlertEvent, MonitorStrategy


class DashboardViewSet(CustomModelViewSet):
    """监控看板统计 (只读)"""
    queryset = Alert.objects.none()

    @action(detail=False)
    def summary(self, request):
        """概览统计"""
        return DetailResponse(data={
            'firing': Alert.objects.filter(status='firing').count(),
            'acknowledged': Alert.objects.filter(status='acknowledged').count(),
            'resolved': Alert.objects.filter(status='resolved').count(),
            'total_alerts': Alert.objects.count(),
            'total_events': AlertEvent.objects.count(),
            'total_strategies': MonitorStrategy.objects.count(),
            'active_strategies': MonitorStrategy.objects.filter(is_enabled=True).count(),
        })

    @action(detail=False)
    def trend(self, request):
        """30天告警趋势"""
        days = int(request.query_params.get('days', 30))
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        cutoff = timezone.now() - timedelta(days=days)
        trend = (
            Alert.objects.filter(fired_at__gte=cutoff)
            .annotate(date=TruncDate('fired_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        return DetailResponse(data=list(trend))

    @action(detail=False)
    def severity_dist(self, request):
        """严重级别分布"""
        from django.db.models import Count
        dist = Alert.objects.values('severity').annotate(count=Count('id')).order_by('severity')
        return DetailResponse(data=list(dist))

    @action(detail=False)
    def top_alerts(self, request):
        """TOP N 告警规则"""
        n = int(request.query_params.get('n', 10))
        from django.db.models import Count
        top = (
            Alert.objects.values('strategy__name', 'strategy_id')
            .annotate(count=Count('id'))
            .order_by('-count')[:n]
        )
        return DetailResponse(data=list(top))

    @action(detail=False)
    def status_dist(self, request):
        """状态分布"""
        from django.db.models import Count
        dist = Alert.objects.values('status').annotate(count=Count('id'))
        return DetailResponse(data=list(dist))

    @action(detail=False)
    def duration_dist(self, request):
        """告警持续时间分布"""
        buckets = [
            {'label': '<5min', 'max': 300},
            {'label': '5-30min', 'min': 300, 'max': 1800},
            {'label': '30min-2h', 'min': 1800, 'max': 7200},
            {'label': '2-8h', 'min': 7200, 'max': 28800},
            {'label': '>8h', 'min': 28800},
        ]
        result = []
        for bucket in buckets:
            qs = Alert.objects.filter(duration__gte=bucket.get('min', 0))
            if 'max' in bucket:
                qs = qs.filter(duration__lt=bucket['max'])
            result.append({'label': bucket['label'], 'count': qs.count()})
        return DetailResponse(data=result)
