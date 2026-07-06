# -*- coding: utf-8 -*-
"""SLA 引擎 — 工单级别计时与升级管理

核心功能:
  - 创建/启动 SLA 计时任务
  - 根据优先级计算 deadline
  - Celery beat 周期性检查超时
  - 超时后执行升级动作（通知、自动转派、标记违例）
"""

import logging
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class SlaEngine:
    """SLA 引擎 — 管理工单的 SLA 计时与升级"""

    # SLA 状态常量
    NORMAL = 'normal'
    WARNING = 'warning'
    VIOLATED = 'violated'

    @staticmethod
    def start_ticket_sla(ticket):
        """工单进入处理状态时启动 SLA 计时"""
        from itsm.models import SlaTask, SlaPolicy

        # 查找匹配的 SLA 策略 — project-scoped
        policy = SlaPolicy.objects.filter(
            priority=ticket.priority, is_active=True,
        ).filter(
            models.Q(project_id=ticket.project_id) | models.Q(project_id__isnull=True)
        ).first()
        if not policy:
            logger.warning(f'No SLA policy for priority {ticket.priority}')
            return None

        # 计算截止时间
        now = timezone.now()
        handle_deadline = now + timedelta(minutes=policy.response_minutes) if policy.response_minutes else None
        reply_deadline = now + timedelta(minutes=policy.resolve_minutes) if policy.resolve_minutes else None

        # Only create SLA task if none exists — don't overwrite active SLA timers
        sla_task, created = SlaTask.objects.get_or_create(
            ticket=ticket,
            defaults={
                'sla_policy': policy,
                'priority': ticket.priority,
                'deadline': handle_deadline,
                'reply_deadline': reply_deadline,
                'task_status': 'running',
                'sla_status': SlaEngine.NORMAL,
            }
        )
        if not created:
            if sla_task.task_status == 'paused':
                SlaEngine.resume_ticket_sla(ticket)
            elif sla_task.task_status == 'stopped':
                # Reset a stopped SLA for subsequent approval nodes
                sla_task.deadline = handle_deadline
                sla_task.reply_deadline = reply_deadline
                sla_task.task_status = 'running'
                sla_task.sla_status = SlaEngine.NORMAL
                sla_task.save(update_fields=['deadline', 'reply_deadline', 'task_status', 'sla_status'])
        logger.info(f'SLA timer started for ticket {ticket.sn}: deadline={handle_deadline}')
        return sla_task

    @staticmethod
    def pause_ticket_sla(ticket):
        """挂起工单时暂停 SLA 计时，记录暂停时间用于恢复"""
        from itsm.models import SlaTask
        now = timezone.now()
        SlaTask.objects.filter(ticket=ticket, task_status='running').update(
            task_status='paused',
            paused_at=now,
        )
        logger.info(f'SLA timer paused for ticket {ticket.sn}')

    @staticmethod
    def resume_ticket_sla(ticket):
        """恢复工单时继续 SLA 计时 — 补偿暂停时间"""
        from itsm.models import SlaTask
        sla = SlaTask.objects.filter(ticket=ticket, task_status='paused').first()
        if sla:
            now = timezone.now()
            pause_duration = (now - sla.paused_at) if sla.paused_at else timedelta(0)
            if sla.deadline:
                sla.deadline = sla.deadline + pause_duration
            if sla.reply_deadline:
                sla.reply_deadline = sla.reply_deadline + pause_duration
            sla.task_status = 'running'
            sla.save(update_fields=['deadline', 'reply_deadline', 'task_status'])
            logger.info(f'SLA timer resumed for ticket {ticket.sn}')

    @staticmethod
    def stop_ticket_sla(ticket):
        """工单完成/终止时停止 SLA 计时"""
        from itsm.models import SlaTask
        SlaTask.objects.filter(ticket=ticket, task_status='running').update(
            task_status='stopped',
        )
        logger.info(f'SLA timer stopped for ticket {ticket.sn}')

    @staticmethod
    def check_all_active_sla():
        """检查所有活跃工单的 SLA 状态（由 Celery beat 定期调用）"""
        from itsm.models import Ticket, SlaTask

        now = timezone.now()
        active_tasks = SlaTask.objects.filter(
            task_status='running',
            ticket__current_status__in=['running', 'suspended'],
        ).select_related('ticket')

        violations = []
        warnings = []

        for task in active_tasks:
            if task.deadline and now > task.deadline:
                # SLA 已超时
                if task.sla_status != SlaEngine.VIOLATED:
                    task.sla_status = SlaEngine.VIOLATED
                    task.save(update_fields=['sla_status'])
                    violations.append(task.ticket)
                    SlaEngine._execute_escalation(task.ticket, 'timeout')
            elif task.deadline and task.reply_deadline:
                # 检查响应超时
                if now > task.reply_deadline and task.sla_status == SlaEngine.NORMAL:
                    task.sla_status = SlaEngine.WARNING
                    task.save(update_fields=['sla_status'])
                    warnings.append(task.ticket)

        return {
            'violations': len(violations),
            'warnings': len(warnings),
            'checked': active_tasks.count(),
        }

    @staticmethod
    def _execute_escalation(ticket, esc_type='timeout'):
        """执行升级动作 — 记录日志 + 发送通知"""
        logger.warning(f'SLA escalation for ticket {ticket.sn}: type={esc_type}')
        meta = ticket.meta or {}
        sla_history = meta.get('sla_history', [])
        sla_history.append({
            'type': esc_type,
            'time': timezone.now().isoformat(),
        })
        meta['sla_history'] = sla_history
        ticket.meta = meta
        ticket.save(update_fields=['meta'])

        # 发送超时通知
        try:
            from itsm.services.notifications import NotificationService
            NotificationService.notify_sla_violation(ticket)
        except Exception as e:
            logger.error(f'SLA notification failed: {e}')
