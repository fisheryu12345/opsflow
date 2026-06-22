# -*- coding: utf-8 -*-
"""Cloud Sync API — 云资产同步状态查询 & 手动触发"""

import logging
from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cmdb.models.cloud_sync_log import CloudSyncLog

logger = logging.getLogger(__name__)

STALE_TIMEOUT_MINUTES = 15  # 同步超过 15 分钟视为卡死


def _reset_stale_records():
    """自动重置卡死的 running 记录（进程重启/线程崩溃导致状态未更新）"""
    cutoff = timezone.now() - timedelta(minutes=STALE_TIMEOUT_MINUTES)
    stuck = CloudSyncLog.objects.filter(status='running', started_at__lt=cutoff)
    count = stuck.count()
    if count:
        stuck.update(
            status='failed',
            finished_at=timezone.now(),
            errors=[{'error': '同步超时，状态已自动重置（前次进程可能异常中断）'}],
        )
        logger.warning("自动重置了 %d 条卡死的同步记录", count)
    return count


# 已注册的云厂商列表
PROVIDERS = {
    'aliyun': {'name': '阿里云', 'name_en': 'Aliyun ECS', 'sync_class': 'cmdb.services.sync_service.AliyunSync'},
}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_providers(request):
    """列出已注册的云厂商及其连接器状态"""
    _reset_stale_records()
    from integration.models.connector import ConnectorDefinition
    available = []
    for code, info in PROVIDERS.items():
        connector = ConnectorDefinition.objects.filter(code=f'{code}_ecs' if code != 'tencent' else f'{code}_cvm').first()
        is_configured = False
        is_active = False
        if connector:
            inst = connector.instances.filter(is_active=True).first()
            if inst:
                is_configured = True
                is_active = inst.is_active
        # 获取最新同步记录
        last_log = CloudSyncLog.objects.filter(provider=code).order_by('-started_at').first()
        available.append({
            'code': code,
            'name': info['name'],
            'name_en': info.get('name_en', code),
            'configured': is_configured,
            'active': is_active,
            'last_sync': {
                'status': last_log.status if last_log else None,
                'started_at': last_log.started_at.isoformat() if last_log and last_log.started_at else None,
                'finished_at': last_log.finished_at.isoformat() if last_log and last_log.finished_at else None,
                'total': last_log.total if last_log else 0,
                'error_count': last_log.error_count if last_log else 0,
                'triggered_by': last_log.triggered_by if last_log else None,
            } if last_log else None,
        })
    return Response({"code": 2000, "data": available})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_status(request, provider):
    """获取指定云厂商的最新同步状态"""
    _reset_stale_records()
    if provider not in PROVIDERS:
        return Response({"code": 4000, "msg": f"不支持的云厂商: {provider}"})
    log = CloudSyncLog.objects.filter(provider=provider).order_by('-started_at').first()
    if not log:
        return Response({"code": 2000, "data": None})
    return Response({"code": 2000, "data": {
        'status': log.status,
        'started_at': log.started_at.isoformat() if log.started_at else None,
        'finished_at': log.finished_at.isoformat() if log.finished_at else None,
        'total': log.total,
        'created_count': log.created_count,
        'updated_count': log.updated_count,
        'error_count': log.error_count,
        'triggered_by': log.triggered_by,
    }})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync(request, provider):
    """手动触发全量同步"""
    if provider not in PROVIDERS:
        return Response({"code": 4000, "msg": f"不支持的云厂商: {provider}"})

    import importlib
    mod_path, cls_name = PROVIDERS[provider]['sync_class'].rsplit('.', 1)
    mod = importlib.import_module(mod_path)
    sync_cls = getattr(mod, cls_name)
    sync_instance = sync_cls()

    # 异步执行
    from threading import Thread

    def _run():
        try:
            result = sync_instance.sync(triggered_by='manual')
            logger.info("手动同步完成 %s: %s", provider, result)
        except Exception as e:
            logger.exception("手动同步失败 %s: %s", provider, e)

    Thread(target=_run, daemon=True).start()

    return Response({"code": 2000, "msg": "同步已触发"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_history(request, provider):
    """获取同步历史记录（分页）"""
    _reset_stale_records()
    if provider not in PROVIDERS:
        return Response({"code": 4000, "msg": f"不支持的云厂商: {provider}"})

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    qs = CloudSyncLog.objects.filter(provider=provider).order_by('-started_at')
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]

    data = []
    for log in items:
        data.append({
            'id': log.id,
            'status': log.status,
            'started_at': log.started_at.isoformat() if log.started_at else None,
            'finished_at': log.finished_at.isoformat() if log.finished_at else None,
            'total': log.total,
            'created_count': log.created_count,
            'updated_count': log.updated_count,
            'error_count': log.error_count,
            'triggered_by': log.triggered_by,
            'errors': (log.errors or [])[:10],  # 最多返回 10 条错误
        })

    return Response({
        "code": 2000,
        "data": {
            "items": data,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    })
