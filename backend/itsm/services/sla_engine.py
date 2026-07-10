# -*- coding: utf-8 -*-
"""SLA 引擎 — 工单级别计时与升级管理

核心功能:
  - 创建/启动 SLA 计时任务 (working-time-aware via SlaTime)
  - 根据优先级 + Schedule 计算 deadline
  - Celery beat / APScheduler 周期性检查超时 + 更新 cost_time
  - 超时后执行 EscalationLevel 升级动作
"""

import logging
from datetime import timedelta

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
        """工单进入处理状态时启动 SLA 计时。

        Uses SlaTime for working-time-aware deadline calculation.
        """
        from itsm.models import SlaTask, SlaPolicy
        from itsm.services.sla_time import SlaTime, _unit_to_seconds

        # 查找匹配的 SLA 策略 — project-scoped
        policy = SlaPolicy.objects.filter(
            priority=ticket.priority, is_active=True,
        ).filter(
            models.Q(project_id=ticket.project_id) | models.Q(project_id__isnull=True)
        ).select_related('schedule').first()
        if not policy:
            logger.warning('No SLA policy for priority %s', ticket.priority)
            return None

        # Ensure schedule is preloaded before passing to SlaTime
        schedule = policy.schedule

        # Convert policy time+unit to seconds
        resolve_secs = policy.resolve_seconds
        response_secs = policy.response_seconds

        # Calculate deadlines using SlaTime (working-time-aware)
        now = timezone.now()
        sla_calc = SlaTime(schedule)
        deadline = sla_calc.sla_deadline(now, resolve_secs) if resolve_secs else None
        reply_deadline = sla_calc.sla_deadline(now, response_secs) if response_secs else None

        # Only create SLA task if none exists — don't overwrite active SLA timers
        sla_task, created = SlaTask.objects.get_or_create(
            ticket=ticket,
            defaults={
                'sla_policy': policy,
                'priority': ticket.priority,
                'deadline': deadline,
                'reply_deadline': reply_deadline,
                'task_status': 'running',
                'sla_status': SlaEngine.NORMAL,
                'total_seconds': resolve_secs,
                'cost_time': 0,
                'begin_at': now,
            }
        )
        if not created:
            if sla_task.task_status == 'paused':
                SlaEngine.resume_ticket_sla(ticket)
            elif sla_task.task_status == 'stopped':
                # Reset a stopped SLA for subsequent approval nodes
                sla_task.deadline = deadline
                sla_task.reply_deadline = reply_deadline
                sla_task.total_seconds = resolve_secs
                sla_task.cost_time = 0
                sla_task.begin_at = now
                sla_task.task_status = 'running'
                sla_task.sla_status = SlaEngine.NORMAL
                sla_task.save(update_fields=[
                    'deadline', 'reply_deadline', 'total_seconds',
                    'cost_time', 'begin_at', 'task_status', 'sla_status',
                ])
        logger.info('SLA timer started for ticket %s: deadline=%s', ticket.sn, deadline)
        return sla_task

    @staticmethod
    def pause_ticket_sla(ticket):
        """挂起工单时暂停 SLA 计时，记录已消耗的有效 SLA 秒数。"""
        from itsm.models import SlaTask
        from itsm.services.sla_time import SlaTime

        now = timezone.now()
        for task in SlaTask.objects.filter(ticket=ticket, task_status='running'):
            if task.begin_at and task.sla_policy and task.sla_policy.schedule_id:
                sla_calc = SlaTime(task.sla_policy.schedule)
                task.cost_time = sla_calc.sla_time(task.begin_at, now)
            task.task_status = 'paused'
            task.paused_at = now
            task.save(update_fields=['cost_time', 'task_status', 'paused_at'])
        logger.info('SLA timer paused for ticket %s', ticket.sn)

    @staticmethod
    def resume_ticket_sla(ticket):
        """恢复工单时继续 SLA 计时 — 用剩余 SLA 秒数重新计算 deadline。"""
        from itsm.models import SlaTask
        from itsm.services.sla_time import SlaTime

        now = timezone.now()
        for sla in SlaTask.objects.filter(ticket=ticket, task_status='paused'):
            if not sla.sla_policy or not sla.sla_policy.schedule_id:
                continue
            remaining = max(0, sla.total_seconds - sla.cost_time)
            sla_calc = SlaTime(sla.sla_policy.schedule)
            sla.deadline = sla_calc.sla_deadline(now, remaining)
            sla.reply_deadline = sla_calc.sla_deadline(now, sla.sla_policy.response_seconds) if sla.sla_policy.response_seconds else None
            sla.begin_at = now
            sla.task_status = 'running'
            sla.save(update_fields=['deadline', 'reply_deadline', 'begin_at', 'task_status'])
        logger.info('SLA timer resumed for ticket %s', ticket.sn)

    @staticmethod
    def stop_ticket_sla(ticket):
        """工单完成/终止时停止 SLA 计时。"""
        from itsm.models import SlaTask
        SlaTask.objects.filter(ticket=ticket, task_status='running').update(
            task_status='stopped',
        )
        logger.info('SLA timer stopped for ticket %s', ticket.sn)

    @staticmethod
    def check_all_active_sla():
        """检查所有活跃工单的 SLA 状态（由 Celery beat / APScheduler 定期调用）。

        Updates cost_time for running tasks, then evaluates violations and
        executes escalation levels.
        """
        from itsm.models import SlaTask
        from itsm.services.sla_time import SlaTime

        now = timezone.now()
        active_tasks = SlaTask.objects.filter(
            task_status='running',
            ticket__current_status__in=['running', 'suspended'],
        ).select_related('ticket', 'sla_policy', 'sla_policy__schedule')

        violations = []
        warnings = []

        for task in active_tasks:
            policy = task.sla_policy
            if not policy or not policy.schedule_id:
                continue

            # Update cost_time for escalation evaluation
            if task.begin_at:
                sla_calc = SlaTime(policy.schedule)
                task.cost_time = sla_calc.sla_time(task.begin_at, now)
                task.save(update_fields=['cost_time'])

            # Check deadline violation
            if task.deadline and now > task.deadline:
                if task.sla_status != SlaEngine.VIOLATED:
                    task.sla_status = SlaEngine.VIOLATED
                    task.save(update_fields=['sla_status'])
                    violations.append(task.ticket)
                    SlaEngine._execute_escalation(task.ticket, task)
            elif task.reply_deadline and now > task.reply_deadline:
                if task.sla_status == SlaEngine.NORMAL:
                    task.sla_status = SlaEngine.WARNING
                    task.save(update_fields=['sla_status'])
                    warnings.append(task.ticket)

        return {
            'violations': len(violations),
            'warnings': len(warnings),
            'checked': active_tasks.count(),
        }

    @staticmethod
    def _execute_escalation(ticket, sla_task):
        """执行升级动作 — 按 EscalationLevel 配置逐级触发。

        Queries the SlaPolicy's escalation_levels (ordered by level), and
        executes each action whose timeout threshold has been exceeded.
        """
        logger.warning('SLA escalation for ticket %s: cost_time=%d', ticket.sn, sla_task.cost_time)

        # Log to ticket meta history
        meta = ticket.meta or {}
        sla_history = meta.get('sla_history', [])
        sla_history.append({
            'type': 'timeout',
            'cost_time': sla_task.cost_time,
            'time': timezone.now().isoformat(),
        })
        meta['sla_history'] = sla_history
        ticket.meta = meta
        ticket.save(update_fields=['meta'])

        # Query escalation levels from the policy
        if not sla_task.sla_policy:
            SlaEngine._notify_default(ticket)
            return

        levels = sla_task.sla_policy.escalation_levels.filter(is_active=True).order_by('level')
        if not levels.exists():
            SlaEngine._notify_default(ticket)
            return

        cost_minutes = sla_task.cost_time // 60
        for level in levels:
            if cost_minutes < level.timeout_minutes:
                continue
            logger.info('Executing escalation L%d (%s) for ticket %s',
                        level.level, level.action, ticket.sn)
            SlaEngine._dispatch_action(level, ticket)

    @staticmethod
    def _dispatch_action(level, ticket):
        """Execute a single escalation action."""
        action = level.action
        if action == 'notify_only':
            try:
                from itsm.services.notifications import NotificationService
                NotificationService.notify_sla_violation(ticket)
            except Exception as e:
                logger.error('SLA notify_only failed: %s', e)

        elif action == 'transfer_leader':
            try:
                from itsm.services.sla_time import resolve_leader
                leader = resolve_leader(ticket.processor or '')
                if leader:
                    ticket.assign(leader)
            except Exception as e:
                logger.error('SLA transfer_leader failed: %s', e)

        elif action == 'transfer_next':
            logger.info('SLA transfer_next for ticket %s — escalation chain', ticket.sn)
            # Placeholder: implement escalation chain logic
            try:
                from itsm.services.notifications import NotificationService
                NotificationService.notify_sla_violation(ticket)
            except Exception as e:
                logger.error('SLA transfer_next notification failed: %s', e)

        elif action == 'notify_users':
            try:
                from itsm.services.sla_time import notify_specific_users
                usernames = [u.strip() for u in level.notify_users.split(',') if u.strip()]
                if usernames:
                    notify_specific_users(usernames)
            except Exception as e:
                logger.error('SLA notify_users failed: %s', e)

    @staticmethod
    def _notify_default(ticket):
        """Fallback notification when no escalation levels are configured."""
        try:
            from itsm.services.notifications import NotificationService
            NotificationService.notify_sla_violation(ticket)
        except Exception as e:
            logger.error('SLA default notification failed: %s', e)
