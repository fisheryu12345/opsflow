# -*- coding: utf-8 -*-
"""Alert views — AlertEvent, Alert, AlertLog ViewSets

告警事件中心: 列表/确认/恢复/关闭/转派/批量操作/创建工单
"""

from django.utils import timezone
from rest_framework.decorators import action

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models import AlertEvent, Alert, AlertLog
from ..serializers import (
    AlertEventSerializer,
    AlertListSerializer, AlertDetailSerializer,
    AlertAckSerializer, AlertAssignSerializer,
    AlertLogSerializer,
)


class AlertEventViewSet(CustomModelViewSet):
    """
    原始告警事件（只读）

    list: 事件列表
    retrieve: 事件详情
    clear: 清理过期事件
    """
    model = AlertEvent
    queryset = AlertEvent.objects.all()
    serializer_class = AlertEventSerializer
    filter_fields = ['status', 'severity', 'strategy', 'bk_biz_id', 'target']
    search_fields = ['alert_name', 'description']
    ordering = ['-time']
    read_only_fields = ['id', 'event_id', 'alert_name', 'description', 'severity', 'status',
                        'target_type', 'target', 'metric', 'metric_value', 'tags',
                        'dedupe_keys', 'dedupe_md5', 'time', 'anomaly_time',
                        'create_time', 'bk_biz_id', 'cmdb_host_id', 'cmdb_biz_id', 'extra_info']

    @action(methods=['POST'], detail=False)
    def clear(self, request):
        """清理指定天数前的已关闭事件"""
        days = request.data.get('days', 30)
        from django.utils import timezone as tz
        from datetime import timedelta
        cutoff = tz.now() - timedelta(days=days)
        cnt, _ = AlertEvent.objects.filter(status='closed', time__lt=cutoff).delete()
        return DetailResponse(data={'deleted': cnt}, msg=f'已清理 {cnt} 条过期事件')


class AlertViewSet(CustomModelViewSet):
    """
    聚合告警管理

    list: 告警列表 (filter: status/severity/strategy)
    retrieve: 告警详情 (含流水日志)
    acknowledge: 确认告警
    resolve: 手动恢复
    close: 关闭告警
    assign: 转派
    batch_ack: 批量确认
    batch_close: 批量关闭
    create_incident: 创建 ITSM 工单
    """
    model = Alert
    queryset = Alert.objects.all()
    serializer_class = AlertListSerializer
    filter_fields = ['status', 'severity', 'strategy', 'cmdb_biz_id', 'cmdb_host_id']
    search_fields = ['title', 'description']
    ordering = ['-fired_at']
    read_only_fields = ['id', 'alert_id', 'severity', 'status', 'title', 'description',
                        'current_value', 'metric_unit', 'labels', 'annotations',
                        'fired_at', 'resolved_at', 'acknowledged_at', 'acknowledged_by',
                        'duration', 'event_count', 'cmdb_host_id', 'cmdb_biz_id',
                        'assignee', 'incident_id', 'escalation_count', 'next_escalate_at']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AlertDetailSerializer(instance)
        return DetailResponse(data=serializer.data)

    @action(methods=['POST'], detail=True)
    def acknowledge(self, request, pk=None):
        """确认告警"""
        instance = self.get_object()
        if instance.status not in ('firing',):
            return ErrorResponse(msg=f'当前状态({instance.get_status_display()})不可确认')
        instance.status = 'acknowledged'
        instance.acknowledged_at = timezone.now()
        instance.acknowledged_by = request.user.name or str(request.user.id)
        instance.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by'])
        AlertLog.objects.create(
            alert=instance, operate='acknowledged',
            operator=str(request.user), description='已确认告警',
        )
        return DetailResponse(msg='已确认')

    @action(methods=['POST'], detail=True)
    def resolve(self, request, pk=None):
        """手动恢复告警"""
        instance = self.get_object()
        if instance.status not in ('firing', 'acknowledged'):
            return ErrorResponse(msg=f'当前状态({instance.get_status_display()})不可恢复')
        instance.status = 'resolved'
        instance.resolved_at = timezone.now()
        instance.save(update_fields=['status', 'resolved_at'])
        AlertLog.objects.create(
            alert=instance, operate='resolved',
            operator=str(request.user), description='已恢复告警',
        )
        return DetailResponse(msg='已恢复')

    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        """关闭告警（终态，不可再操作）"""
        instance = self.get_object()
        if instance.status in ('closed',):
            return ErrorResponse(msg='已关闭，不可重复操作')
        instance.status = 'closed'
        instance.resolved_at = timezone.now()
        instance.save(update_fields=['status', 'resolved_at'])
        AlertLog.objects.create(
            alert=instance, operate='closed',
            operator=str(request.user), description='已关闭告警',
        )
        return DetailResponse(msg='已关闭')

    @action(methods=['POST'], detail=True)
    def assign(self, request, pk=None):
        """转派告警"""
        serializer = AlertAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.get_object()
        prev = instance.assignee
        instance.assignee = serializer.validated_data['assignee']
        instance.save(update_fields=['assignee'])
        AlertLog.objects.create(
            alert=instance, operate='assigned',
            operator=str(request.user),
            description=f'从 {prev} 转派至 {instance.assignee}',
        )
        return DetailResponse(data={'assignee': instance.assignee}, msg='转派成功')

    @action(methods=['POST'], detail=False)
    def batch_ack(self, request):
        """批量确认"""
        ids = request.data.get('ids', [])
        now = timezone.now()
        updated = Alert.objects.filter(id__in=ids, status='firing').update(
            status='acknowledged', acknowledged_at=now,
        )
        return DetailResponse(data={'updated': updated}, msg=f'已确认 {updated} 条')

    @action(methods=['POST'], detail=False)
    def batch_close(self, request):
        """批量关闭"""
        ids = request.data.get('ids', [])
        now = timezone.now()
        updated = Alert.objects.filter(id__in=ids).exclude(status='closed').update(
            status='closed', resolved_at=now,
        )
        return DetailResponse(data={'updated': updated}, msg=f'已关闭 {updated} 条')

    @action(methods=['POST'], detail=True)
    def create_incident(self, request, pk=None):
        """创建关联 ITSM 工单"""
        instance = self.get_object()
        if instance.incident_id:
            return ErrorResponse(msg=f'已关联工单: {instance.incident_id}')
        try:
            from itsm.models.incident import Incident
            import uuid
            incident = Incident.objects.create(
                incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
                title=f"[告警] {instance.title}",
                description=instance.description[:2000] if instance.description else '',
                priority='P1' if instance.severity == 1 else 'P2' if instance.severity == 2 else 'P3',
                source='alert',
                alert_data={'severity': instance.severity, 'labels': instance.labels},
            )
            instance.incident_id = incident.incident_id
            instance.save(update_fields=['incident_id'])
            AlertLog.objects.create(
                alert=instance, operate='incident_created',
                operator=str(request.user),
                description=f'创建 ITSM 工单: {incident.incident_id}',
            )
            return DetailResponse(data={'incident_id': incident.incident_id}, msg='工单已创建')
        except Exception as e:
            return ErrorResponse(msg=f'创建工单失败: {e}')
