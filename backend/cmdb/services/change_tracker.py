# -*- coding: utf-8 -*-
from __future__ import annotations

"""ChangeTracker — CI 变更追踪服务

记录模型实例的创建、更新、删除操作到 ChangeLog。
更新操作会逐字段对比并记录差异。

整合后可联动 event_dispatcher 触发 webhook 通知。
"""

import logging
from typing import Optional

from ..models.change_log import ChangeLog
from ..models.model_definition import ModelDefinition

logger = logging.getLogger(__name__)

FSM = 'change_tracker'  # 日志上下文标签


def _build_changes_dict(instance_data_before: dict,
                        instance_data_after: dict) -> list[dict]:
    """对比前后数据，返回变更字段列表

    Returns:
        [{field, old_value, new_value}, ...]
    """
    skip_fields = {'instance_id', '__model_code', '__created_at', '__updated_at'}
    changes = []
    all_keys = set(instance_data_before.keys()) | set(instance_data_after.keys())
    for key in all_keys:
        if key in skip_fields:
            continue
        old_val = instance_data_before.get(key)
        new_val = instance_data_after.get(key)
        if old_val != new_val:
            changes.append({
                'field': key,
                'old_value': old_val,
                'new_value': new_val,
            })
    return changes


def track_create(instance_data: dict, model_code: str, operator: str = 'system'):
    """记录实例创建

    Args:
        instance_data: 创建后的实例数据 (含 instance_id)
        model_code: 模型编码
        operator: 操作人
    """
    try:
        instance_id = instance_data.get('instance_id', '')
        ChangeLog.objects.create(
            model_code=model_code,
            instance_id=instance_id,
            action='create',
            operator=operator,
            changes={'new_value': instance_data},
        )
        logger.info(f"{FSM} 记录创建: {model_code}/{instance_id} by {operator}")
    except Exception as e:
        logger.error(f"{FSM} 记录创建失败: {e}")


def track_update(instance_data_before: dict,
                 instance_data_after: dict,
                 model_code: str,
                 operator: str = 'system'):
    """记录实例更新 — 逐字段对比差异

    Args:
        instance_data_before: 更新前的实例数据
        instance_data_after: 更新后的实例数据
        model_code: 模型编码
        operator: 操作人
    """
    try:
        instance_id = instance_data_after.get('instance_id',
                                              instance_data_before.get('instance_id', ''))

        changes = _build_changes_dict(instance_data_before, instance_data_after)

        if not changes:
            logger.info(f"{FSM} 无字段变更，跳过记录: {model_code}/{instance_id}")
            return

        ChangeLog.objects.create(
            model_code=model_code,
            instance_id=instance_id,
            action='update',
            operator=operator,
            changes={'fields': changes},
        )
        logger.info(f"{FSM} 记录更新: {model_code}/{instance_id} "
                     f"{len(changes)} 个字段变更 by {operator}")

        # 联动事件分发（由 event_dispatcher 处理）
        _dispatch_if_available('update', model_code, instance_id, operator, changes)

    except Exception as e:
        logger.error(f"{FSM} 记录更新失败: {e}")


def track_delete(instance_id: str, model_code: str, operator: str = 'system',
                 instance_snapshot: Optional[dict] = None):
    """记录实例删除

    Args:
        instance_id: 被删除的实例 ID
        model_code: 模型编码
        operator: 操作人
        instance_snapshot: 删除前的实例快照（如有则记录）
    """
    try:
        ChangeLog.objects.create(
            model_code=model_code,
            instance_id=instance_id,
            action='delete',
            operator=operator,
            changes={'old_value': instance_snapshot},
        )
        logger.info(f"{FSM} 记录删除: {model_code}/{instance_id} by {operator}")

        # 联动事件分发
        _dispatch_if_available('delete', model_code, instance_id, operator,
                               [{'field': '*', 'old_value': instance_snapshot, 'new_value': None}])

    except Exception as e:
        logger.error(f"{FSM} 记录删除失败: {e}")


def _dispatch_if_available(event_type: str, model_code: str,
                           instance_id: str, operator: str, changes: list):
    """尝试分发事件 — event_dispatcher 可能尚未注册"""
    try:
        from .event_dispatcher import dispatch_event
        dispatch_event(event_type, model_code, instance_id, operator, changes)
    except ImportError:
        pass  # event_dispatcher 尚未创建时静默跳过
    except Exception as e:
        logger.warning(f"{FSM} 事件分发失败: {e}")
