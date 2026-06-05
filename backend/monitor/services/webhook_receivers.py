# -*- coding: utf-8 -*-
"""Webhook receivers — Prometheus AlertManager / Grafana / 自定义推流

接收外部监控系统的告警推送，转换为 AlertEvent 并触发管道处理。
"""

import json
import hashlib
import logging
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)
FSM = 'monitor_webhook'


def _make_event_id(source: str, raw_id: str) -> str:
    """生成全局唯一的 event_id"""
    raw = f"{source}:{raw_id}:{timezone.now().timestamp()}"
    return hashlib.md5(raw.encode()).hexdigest()[:32]


def _severity_map(source_severity: str) -> int:
    """将外部系统的 severity 映射为内部 1/2/3"""
    mapping = {
        'critical': 1, 'fatal': 1, 'emergency': 1,
        'warning': 2, 'warn': 2,
        'info': 3, 'information': 3, 'debug': 3,
    }
    return mapping.get(source_severity.lower(), 3)


def _trigger_pipeline(event_id: str):
    """触发告警管道处理 — 入 Redis List 或直接调用"""
    try:
        from ..services.pipeline import AlertPipeline
        pipeline = AlertPipeline()
        from ..models import AlertEvent
        event = AlertEvent.objects.filter(event_id=event_id).first()
        if event:
            pipeline.process_event({
                'event_id': event.event_id,
                'alert_name': event.alert_name,
                'description': event.description or '',
                'severity': event.severity,
                'target_type': event.target_type,
                'target': event.target,
                'metric': event.metric,
                'metric_value': event.metric_value,
                'labels': event.tags,
                'time': event.time,
                'cmdb_host_id': event.cmdb_host_id or '',
                'cmdb_biz_id': event.cmdb_biz_id or '',
                'strategy_id': None,
                'extra_info': event.extra_info,
            })
    except Exception as e:
        logger.warning(f"[Webhook] Trigger pipeline failed for {event_id}: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Prometheus AlertManager Webhook
# ═══════════════════════════════════════════════════════════════════════
@csrf_exempt
@require_POST
def prometheus_webhook(request):
    """
    Prometheus AlertManager Webhook 接收端点
    配置 AlertManager → webhook_configs → url: /api/monitor/webhook/prometheus/
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': 'Invalid JSON'}, status=400)

    alerts = payload.get('alerts', [])
    created = 0
    for alert in alerts:
        try:
            _handle_prometheus_alert(alert)
            created += 1
        except Exception as e:
            logger.error(f"Prometheus webhook: handle alert failed: {e}")

    return JsonResponse({'code': 2000, 'data': {'received': len(alerts), 'created': created}})


def _handle_prometheus_alert(alert: dict):
    """处理单条 Prometheus alert"""
    from ..models import AlertEvent

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    status = alert.get('status', 'firing')

    alertname = labels.get('alertname', 'unknown')
    source_event_id = f"prometheus-{alertname}-{labels.get('instance', '')}"
    event_id = _make_event_id('prometheus', source_event_id)

    # 解析触发时间
    starts_at = alert.get('startsAt', '')
    try:
        fired_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        fired_at = timezone.now()

    cmdb_host_id = labels.get('cmdb_host_id', '') or labels.get('instance', '')
    cmdb_biz_id = labels.get('bk_biz_id', '')

    severity = _severity_map(labels.get('severity', 'warning'))

    event_status = 'abnormal' if status == 'firing' else 'recovered'

    # metric_value — 从 annotations 或 labels 里提取数值
    metric_value = alert.get('value')
    if metric_value is not None:
        try:
            metric_value = float(str(metric_value).strip())
        except (ValueError, TypeError):
            metric_value = None

    event, created = AlertEvent.objects.update_or_create(
        event_id=event_id,
        defaults={
            'alert_name': annotations.get('summary', alertname),
            'description': annotations.get('description', ''),
            'severity': severity,
            'status': event_status,
            'target_type': 'host',
            'target': labels.get('instance', ''),
            'metric': labels.get('metric', ''),
            'metric_value': metric_value,
            'tags': labels,
            'dedupe_keys': ['alert_name', 'target', 'metric'],
            'dedupe_md5': hashlib.md5(
                json.dumps({k: labels.get(k) for k in ['alertname', 'instance', 'metric']}, sort_keys=True).encode()
            ).hexdigest(),
            'time': fired_at,
            'cmdb_host_id': cmdb_host_id,
            'cmdb_biz_id': cmdb_biz_id,
            'extra_info': {'source': 'prometheus', 'status': status, 'annotations': annotations},
        }
    )

    # 触发管道
    if created and event_status == 'abnormal':
        _trigger_pipeline(event.event_id)


# ═══════════════════════════════════════════════════════════════════════
# Grafana Alerting Webhook
# ═══════════════════════════════════════════════════════════════════════
@csrf_exempt
@require_POST
def grafana_webhook(request):
    """
    Grafana Alerting Webhook 接收端点
    配置 Grafana Notification Channel → Webhook → /api/monitor/webhook/grafana/
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': 'Invalid JSON'}, status=400)

    alerts = payload.get('alerts', [])
    created = 0
    for alert in alerts:
        try:
            _handle_grafana_alert(alert)
            created += 1
        except Exception as e:
            logger.error(f"Grafana webhook: handle alert failed: {e}")

    return JsonResponse({'code': 2000, 'data': {'received': len(alerts), 'created': created}})


def _handle_grafana_alert(alert: dict):
    """处理单条 Grafana alert"""
    from ..models import AlertEvent

    labels = alert.get('labels', {})
    annotations = alert.get('annotations', {})
    status = alert.get('status', 'firing')

    alertname = labels.get('alertname', annotations.get('summary', 'unknown'))
    source_event_id = f"grafana-{alert.get('fingerprint', alertname)}"
    event_id = _make_event_id('grafana', source_event_id)

    starts_at = alert.get('startsAt', alert.get('firedAt', ''))
    try:
        fired_at = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        fired_at = timezone.now()

    cmdb_host_id = labels.get('cmdb_host_id', '') or labels.get('instance', '')
    cmdb_biz_id = labels.get('bk_biz_id', '') or labels.get('biz_id', '')

    severity = _severity_map(labels.get('severity', 'warning'))
    event_status = 'abnormal' if status == 'firing' else 'recovered'

    event, created = AlertEvent.objects.update_or_create(
        event_id=event_id,
        defaults={
            'alert_name': annotations.get('summary', alertname),
            'description': annotations.get('description', ''),
            'severity': severity,
            'status': event_status,
            'target_type': 'host',
            'target': labels.get('instance', ''),
            'metric': labels.get('metric', ''),
            'metric_value': alert.get('value'),
            'tags': {**labels, **annotations},
            'dedupe_keys': ['alert_name', 'target'],
            'dedupe_md5': hashlib.md5(
                json.dumps({'alertname': alertname, 'instance': labels.get('instance', '')}, sort_keys=True).encode()
            ).hexdigest(),
            'time': fired_at,
            'cmdb_host_id': cmdb_host_id,
            'cmdb_biz_id': cmdb_biz_id,
            'extra_info': {'source': 'grafana', 'status': status, 'payload': alert},
        }
    )

    if created and event_status == 'abnormal':
        _trigger_pipeline(event.event_id)


# ═══════════════════════════════════════════════════════════════════════
# Custom Push API — 自建采集推流
# ═══════════════════════════════════════════════════════════════════════
@csrf_exempt
@require_POST
def custom_push(request, code: str = ''):
    """
    自定义采集推流端点
    POST /api/monitor/webhook/custom/{code}/
    body: {"events": [{"alert_name": "...", "metric_value": 90.0, ...}]}
    """
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 4000, 'msg': 'Invalid JSON'}, status=400)

    from ..models import CollectConfig, AlertEvent
    import hashlib, json

    # 验证采集器
    try:
        collect = CollectConfig.objects.get(data_source_label='custom', id=int(code) if code.isdigit() else 0)
    except (CollectConfig.DoesNotExist, ValueError):
        collect = None

    events = payload.get('events', [payload] if 'alert_name' in payload else [])
    created = 0

    for ev in events:
        try:
            event_id = _make_event_id('custom', f"{code}-{ev.get('alert_name', '')}-{timezone.now().timestamp()}")
            AlertEvent.objects.create(
                event_id=event_id,
                alert_name=ev.get('alert_name', 'unknown'),
                description=ev.get('description', ''),
                severity=_severity_map(ev.get('severity', 'warning')),
                status='pending',
                target_type=ev.get('target_type', 'host'),
                target=ev.get('target', ''),
                metric=ev.get('metric', ''),
                metric_value=ev.get('metric_value'),
                tags=ev.get('tags', {}),
                dedupe_md5=hashlib.md5(json.dumps(ev, sort_keys=True).encode()).hexdigest(),
                time=timezone.now(),
                bk_biz_id=ev.get('bk_biz_id', 0),
                cmdb_host_id=ev.get('cmdb_host_id', ''),
                extra_info={'source': 'custom', 'code': code},
            )
            created += 1
            _trigger_pipeline(event_id)
        except Exception as e:
            logger.error(f"Custom push: handle event failed: {e}")

    return JsonResponse({'code': 2000, 'data': {'received': len(events), 'created': created}})
