# -*- coding: utf-8 -*-
"""Grafana webhook receiver — consume Grafana alert notifications

Grafana 告警 Webhook 接收器 — 接收 Grafana Alerting 推送的告警事件
"""

import json
import logging
import hashlib
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

FSM = 'grafana_webhook'


@csrf_exempt
@require_POST
def grafana_alert_webhook(request):
    """
    Grafana Alerting Webhook 接收端点
    配置 Grafana Notification Channel → Webhook → POST 到此端点
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': '无效的 JSON'}, status=400)

    alerts = payload.get('alerts', [])
    created = 0
    for alert in alerts:
        try:
            _create_alert_event(alert)
            created += 1
        except Exception as e:
            logger.error(f"创建告警事件失败: {e}")

    return JsonResponse({'code': 2000, 'data': {'received': len(alerts), 'created': created}})


def _create_alert_event(alert: dict):
    """将 Grafana alert 数据结构转换为 AlertEvent"""
    from ..models.alert import AlertEvent

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    status = alert.get('status', 'firing')

    # 生成唯一 alert_id
    alert_id_source = json.dumps(labels, sort_keys=True) + str(alert.get('startsAt', ''))
    alert_id = hashlib.md5(alert_id_source.encode()).hexdigest()

    # 解析 CMDB 关联
    cmdb_host_id = labels.get('cmdb_host_id', '') or labels.get('host_id', '')
    cmdb_biz_id = labels.get('cmdb_biz_id', '') or labels.get('biz_id', '')

    # 解析触发时间
    fired_at = datetime.fromisoformat(alert.get('startsAt', '').replace('Z', '+00:00')) if alert.get('startsAt') else datetime.now()

    AlertEvent.objects.get_or_create(
        alert_id=alert_id,
        defaults={
            'title': annotations.get('summary', labels.get('alertname', 'Unknown Alert')),
            'description': annotations.get('description', ''),
            'status': 'firing' if status == 'firing' else 'resolved',
            'severity': labels.get('severity', 'warning'),
            'labels': labels,
            'annotations': annotations,
            'fired_at': fired_at,
            'cmdb_host_id': cmdb_host_id,
            'cmdb_biz_id': cmdb_biz_id,
        }
    )
