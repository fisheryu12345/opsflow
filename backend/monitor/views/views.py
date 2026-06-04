# -*- coding: utf-8 -*-
"""Monitor views — AlertRule, AlertEvent, MonitorTarget

告警规则CRUD + 告警事件列表/确认/联动工单
"""

from rest_framework.decorators import action
from django.utils import timezone

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.alert import AlertRule, AlertEvent, MonitorTarget
from ..serializers import (
    AlertRuleSerializer, AlertRuleCreateUpdateSerializer,
    AlertEventSerializer, AlertEventAckSerializer,
    MonitorTargetSerializer,
)


class AlertRuleViewSet(CustomModelViewSet):
    """告警规则管理"""
    model = AlertRule
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    create_serializer_class = AlertRuleCreateUpdateSerializer
    update_serializer_class = AlertRuleCreateUpdateSerializer
    filter_fields = ['severity', 'status', 'source']
    search_fields = ['name', 'description']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def toggle(self, request, pk=None):
        """启用/禁用规则"""
        instance = self.get_object()
        instance.status = 'disabled' if instance.status == 'enabled' else 'enabled'
        instance.save(update_fields=['status'])
        return DetailResponse(data={'status': instance.status}, msg='操作成功')


class AlertEventViewSet(CustomModelViewSet):
    """告警事件中心"""
    model = AlertEvent
    queryset = AlertEvent.objects.all()
    serializer_class = AlertEventSerializer
    filter_fields = ['status', 'severity', 'rule']
    search_fields = ['title', 'description']
    ordering = ['-fired_at']
    # 只读: 禁止创建/修改/删除告警事件
    read_only_fields = '__all__'

    @action(methods=['POST'], detail=True)
    def acknowledge(self, request, pk=None):
        """确认告警"""
        instance = self.get_object()
        instance.status = 'acknowledged'
        instance.acknowledged_at = timezone.now()
        instance.acknowledged_by = request.user.name or str(request.user.id)
        instance.save(update_fields=['status', 'acknowledged_at', 'acknowledged_by'])
        return DetailResponse(msg='已确认')

    @action(methods=['POST'], detail=True)
    def create_incident(self, request, pk=None):
        """创建关联事件工单"""
        instance = self.get_object()
        if instance.incident:
            return ErrorResponse(msg='已关联工单')
        from itsm.models.incident import Incident
        import uuid
        incident = Incident.objects.create(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            title=f"[告警] {instance.title}",
            description=instance.description[:2000] if instance.description else '',
            priority='P1' if instance.severity == 'critical' else 'P2' if instance.severity == 'warning' else 'P3',
            source='alert',
            alert_id=instance.alert_id,
            alert_data={'severity': instance.severity, 'labels': instance.labels},
            cmdb_host_id=instance.cmdb_host_id,
            cmdb_biz_id=instance.cmdb_biz_id,
        )
        instance.incident = incident
        instance.save(update_fields=['incident'])
        return DetailResponse(data={'incident_id': incident.incident_id}, msg='工单已创建')


class MonitorTargetViewSet(CustomModelViewSet):
    """监控目标管理"""
    model = MonitorTarget
    queryset = MonitorTarget.objects.all()
    serializer_class = MonitorTargetSerializer
    filter_fields = ['target_type', 'source', 'is_active']
    search_fields = ['name', 'endpoint']
    ordering = ['name']

    @action(methods=['POST'], detail=True)
    def toggle(self, request, pk=None):
        instance = self.get_object()
        instance.is_active = not instance.is_active
        instance.save(update_fields=['is_active'])
        return DetailResponse(data={'is_active': instance.is_active}, msg='操作成功')
