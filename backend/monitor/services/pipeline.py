# -*- coding: utf-8 -*-
"""Alert Pipeline — 告警处理管道引擎

事件摄入 → 策略匹配 → 告警构建 → 静默过滤 → 收敛 → 动作分派

APScheduler 驱动，支持 Redis 轻量队列触发。
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from django.utils import timezone

logger = logging.getLogger(__name__)
FSM = 'alert_pipeline'


class AlertPipeline:
    """
    告警管道 — 处理单条事件/告警的全生命周期
    每个阶段返回 dict 或 None (中断)
    """

    def process_event(self, event_data: dict) -> Optional[dict]:
        """处理原始事件"""
        try:
            # 1. Event Clean — 字段标准化
            cleaned = self._clean_event(event_data)
            if not cleaned:
                return None

            # 2. Strategy Match — 策略匹配
            matched = self._match_strategy(cleaned)
            if not matched:
                self._save_event_as_closed(cleaned)
                return None

            # 3. Alert Build — 告警构建
            alert = self._build_alert(matched)
            if not alert:
                return None

            # 4. Shield Filter — 静默过滤
            if self._check_shield(alert):
                alert['status'] = 'silenced'
                self._save_alert(alert)
                return alert

            # 5. Convergence — 收敛
            if self._check_convergence(alert):
                logger.info(f"Alert {alert.get('alert_id')} converged, skipped")
                return alert

            # 6. Dispatch — 动作分派
            self._dispatch(alert)
            return alert

        except Exception as e:
            logger.error(f"Alert pipeline error: {e}", exc_info=True)
            return None

    def _clean_event(self, data: dict) -> Optional[dict]:
        """标准化事件字段"""
        event_id = data.get('event_id') or data.get('alert_id', '')
        if not event_id:
            logger.warning("Event missing event_id, skipped")
            return None

        dedupe_keys = data.get('dedupe_keys', ['alert_name', 'target', 'metric'])
        dedupe_raw = json.dumps({k: data.get(k) for k in dedupe_keys if data.get(k)}, sort_keys=True)
        dedupe_md5 = hashlib.md5(dedupe_raw.encode()).hexdigest()

        return {
            'event_id': event_id,
            'alert_name': data.get('alert_name', data.get('title', 'Unknown')),
            'description': data.get('description', ''),
            'severity': data.get('severity', 3),
            'target_type': data.get('target_type', 'host'),
            'target': data.get('target', ''),
            'metric': data.get('metric', ''),
            'metric_value': data.get('metric_value'),
            'tags': data.get('tags', {}),
            'dedupe_keys': dedupe_keys,
            'dedupe_md5': dedupe_md5,
            'time': data.get('time') or timezone.now(),
            'anomaly_time': data.get('anomaly_time'),
            'bk_biz_id': data.get('bk_biz_id', 0),
            'cmdb_host_id': data.get('cmdb_host_id', ''),
            'cmdb_biz_id': data.get('cmdb_biz_id', ''),
            'extra_info': data.get('extra_info', {}),
            'strategy_id': data.get('strategy_id'),
            'labels': data.get('labels', {}),
            'annotations': data.get('annotations', {}),
        }

    def _match_strategy(self, cleaned: dict) -> Optional[dict]:
        """策略匹配 — 简化版: 按 strategy_id 或自动匹配"""
        from ..models import MonitorStrategy, MonitorItem

        strategy_id = cleaned.get('strategy_id')
        strategy = None
        item = None

        if strategy_id:
            try:
                strategy = MonitorStrategy.objects.get(id=strategy_id, is_enabled=True)
                item = strategy.items.first()
            except MonitorStrategy.DoesNotExist:
                pass

        if not strategy:
            return None

        return {
            **cleaned,
            'strategy_id': strategy.id,
            'strategy_name': strategy.name,
            'item_id': item.id if item else None,
        }

    def _build_alert(self, matched: dict) -> Optional[dict]:
        """构建或更新告警"""
        from ..models import Alert

        # 生成 alert_id
        raw = f"{matched.get('strategy_id', '')}-{matched.get('target', '')}-{matched.get('metric', '')}"
        alert_id = hashlib.md5(raw.encode()).hexdigest()[:16]

        # 幂等查找
        alert, created = Alert.objects.get_or_create(
            alert_id=alert_id,
            defaults={
                'strategy_id': matched.get('strategy_id'),
                'severity': matched.get('severity', 3),
                'status': 'firing',
                'title': matched.get('alert_name', ''),
                'description': matched.get('description', ''),
                'current_value': matched.get('metric_value'),
                'labels': matched.get('labels', {}),
                'annotations': matched.get('annotations', {}),
                'fired_at': matched.get('time', timezone.now()),
                'cmdb_host_id': matched.get('cmdb_host_id', ''),
                'cmdb_biz_id': matched.get('cmdb_biz_id', ''),
            }
        )

        if not created:
            # 更新现有告警
            alert.event_count += 1
            alert.current_value = matched.get('metric_value')
            alert.labels = matched.get('labels', alert.labels)
            if alert.status in ('resolved', 'closed'):
                alert.status = 'firing'
                alert.fired_at = matched.get('time', timezone.now())
            # 计算持续时间
            if alert.fired_at:
                delta = timezone.now() - alert.fired_at
                alert.duration = int(delta.total_seconds())
            alert.save()

        # 记录 AlertLog
        from ..models import AlertLog
        AlertLog.objects.create(
            alert=alert, operate='created' if created else 'updated',
            operator='system',
            description=f"{'创建' if created else '更新'}告警 (event_count={alert.event_count})",
        )

        return {
            'alert_id': alert.alert_id,
            'alert': alert,
            'is_new': created,
        }

    def _check_shield(self, alert_result: dict) -> bool:
        """检查静默屏蔽"""
        from ..models import ShieldPlan
        now = timezone.now()
        alert = alert_result.get('alert')
        matched = ShieldPlan.objects.filter(
            is_enabled=True,
        ).filter(
            # 策略级屏蔽
            shield_type__in=['strategy', 'global'],
        ).filter(
            conditions__strategy_id=str(alert.strategy_id),
        ).exclude(
            time_range__isnull=False,
            time_range__end__lt=now,
        ).exists()
        return matched

    def _check_convergence(self, alert_result: dict) -> bool:
        """去重收敛检查 — 同策略+同目标在窗口内多次触发仅计 event_count++"""
        if not alert_result or not alert_result.get('alert'):
            return False
        alert = alert_result['alert']
        # 新创建的告警不走收敛（第一条必须通过）
        if alert_result.get('is_new', False):
            return False
        # 同一告警在 10 分钟内更新超过 5 次 → 降低通知频率
        window = timezone.now() - timedelta(minutes=10)
        recent_logs = alert.logs.filter(create_time__gte=window, operate='notified').count()
        return recent_logs >= 5

    def _dispatch(self, alert_result: dict):
        """动作分派 — 匹配分派规则 → 通知组 → 执行动作"""
        if not alert_result or not alert_result.get('alert'):
            return
        alert = alert_result['alert']
        # 静默的告警不分派
        if alert.status == 'silenced':
            return
        try:
            self._match_and_execute(alert)
        except Exception as e:
            logger.error(f"[Pipeline] Dispatch error for alert {alert.alert_id}: {e}", exc_info=True)

    def _match_and_execute(self, alert):
        """匹配 AlertAssignGroup 规则并执行动作"""
        from ..models import AlertAssignGroup, AlertAssignRule, AlertLog

        # 按优先级获取启用的分派规则组
        groups = AlertAssignGroup.objects.filter(
            is_enabled=True,
            rules__is_enabled=True,
        ).distinct().order_by('priority')
        if not groups:
            logger.debug(f"[Pipeline] No assign group for alert {alert.alert_id}")
            return

        executed_actions = []
        for group in groups:
            rules = group.rules.filter(is_enabled=True)
            for rule in rules:
                if self._match_condition(rule.conditions, alert):
                    self._execute_action(rule, alert)
                    executed_actions.append(rule.name)

        if executed_actions:
            AlertLog.objects.create(
                alert=alert, operate='action_executed',
                operator='system',
                description=f'分派规则组匹配: {", ".join(executed_actions)}',
            )

    def _match_condition(self, conditions: dict, alert) -> bool:
        """评估分派条件是否匹配"""
        if not conditions:
            return True
        # severity 匹配
        severity_list = conditions.get('severity')
        if severity_list and alert.severity not in severity_list:
            return False
        # 标签匹配
        label_conditions = conditions.get('labels', {})
        if label_conditions:
            alert_labels = alert.labels or {}
            for k, v in label_conditions.items():
                if alert_labels.get(k) != v:
                    return False
        # 策略ID匹配
        strategy_ids = conditions.get('strategy_ids', [])
        if strategy_ids and alert.strategy_id not in strategy_ids:
            return False
        return True

    def _execute_action(self, rule, alert):
        """执行单条分派规则"""
        from ..models import AlertLog

        action_type = rule.action_type

        # 通知
        if action_type == 'notify' and rule.notify_group:
            from ..models import DutyArrange
            now = timezone.now()
            # 查找当前值班人
            on_duty = DutyArrange.objects.filter(
                plan__group=rule.notify_group,
                date_from__lte=now,
                date_to__gte=now,
                duty_type='primary',
            ).order_by('date_from').first()

            # 通过适配器发送通知
            from .adapter_loader import AdapterLoader
            from ..adapters import NotifyMessage

            adapter = AdapterLoader.get_adapter('notify', 'wecom', rule.action_config or {})
            if adapter:
                msg = NotifyMessage(
                    title=alert.title,
                    content=alert.description or alert.title,
                    severity=alert.severity,
                    alert_id=alert.alert_id,
                )
                recipients = [on_duty.user_name] if on_duty else []
                result = adapter.send(recipients, msg)
                AlertLog.objects.create(
                    alert=alert, operate='notified',
                    operator='system',
                    description=f"通知发送 {'成功' if result.success else '失败'}: {result.message}",
                )

        # Webhook
        elif action_type == 'webhook':
            import requests
            import json
            url = rule.action_config.get('url', '')
            if url:
                try:
                    resp = requests.post(url, json={
                        'alert_id': alert.alert_id,
                        'title': alert.title,
                        'severity': alert.severity,
                        'status': alert.status,
                        'fired_at': alert.fired_at.isoformat(),
                        'labels': alert.labels,
                    }, timeout=15)
                    AlertLog.objects.create(
                        alert=alert, operate='action_executed',
                        operator='system',
                        description=f"Webhook {url}: {resp.status_code}",
                    )
                except Exception as e:
                    logger.warning(f"[Pipeline] Webhook failed: {e}")

        # OpsFlow / AWX / ITSM — 通过 SPI 动作适配器执行
        elif rule.action_plugin and rule.action_plugin.adapter_class:
            from django.utils.module_loading import import_string
            try:
                adapter_cls = import_string(rule.action_plugin.adapter_class)
                adapter = adapter_cls(rule.action_config or {})
                from ..adapters import ActionContext
                context = ActionContext(
                    alert_id=alert.alert_id,
                    alert_title=alert.title,
                    severity=alert.severity,
                    config=rule.action_config,
                )
                result = adapter.execute(context)
                AlertLog.objects.create(
                    alert=alert, operate='action_executed',
                    operator='system',
                    description=f"动作 {rule.action_plugin.name}: {'成功' if result.success else '失败'} - {result.message}",
                )
            except Exception as e:
                logger.error(f"[Pipeline] Action plugin {rule.action_plugin.plugin_key} error: {e}")

    def _save_event_as_closed(self, cleaned: dict):
        """保存未匹配到策略的事件为已关闭"""
        from ..models import AlertEvent
        try:
            AlertEvent.objects.create(
                event_id=cleaned['event_id'],
                alert_name=cleaned['alert_name'],
                description=cleaned.get('description', ''),
                severity=cleaned.get('severity', 3),
                status='closed',
                target=cleaned.get('target', ''),
                metric=cleaned.get('metric', ''),
                metric_value=cleaned.get('metric_value'),
                dedupe_md5=cleaned.get('dedupe_md5', ''),
                time=cleaned.get('time', timezone.now()),
                bk_biz_id=cleaned.get('bk_biz_id', 0),
                cmdb_host_id=cleaned.get('cmdb_host_id', ''),
                extra_info=cleaned.get('extra_info', {}),
            )
        except Exception as e:
            logger.error(f"Save unmatched event failed: {e}")
