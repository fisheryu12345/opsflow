# -*- coding: utf-8 -*-
"""EscalationService — 工单升级检测与执行

由 APScheduler 定时触发，扫描超时工单并执行 EscalationLevel 动作。
"""

import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class EscalationService:
    """多级升级服务 — 检测超时并执行升级动作"""

    @staticmethod
    def check_and_escalate():
        """扫描所有活跃工单，对超时的执行升级（APScheduler 每分钟调用）"""
        from itsm.models.ticket import Ticket

        tickets = Ticket.objects.filter(
            current_status__in=['assigned', 'receiving', 'running'],
        ).select_related('category__default_group')
        count = 0
        for ticket in tickets:
            try:
                if EscalationService._process_ticket(ticket):
                    count += 1
            except Exception as e:
                logger.error("Escalation check failed for ticket %s: %s", ticket.sn, e)
        if count:
            logger.info("EscalationService: %d tickets escalated", count)
        return count

    @staticmethod
    def _process_ticket(ticket):
        """检查单个工单是否需要升级，是则执行"""
        meta = dict(ticket.meta or {})
        current_level = meta.get('escalation_level', 0)
        escalated_at = meta.get('escalated_at')

        # 获取当前技能组
        group_id = None
        assignee = meta.get('assignee')
        assign_group = meta.get('assign_group')
        if assignee and assignee.get('group'):
            from itsm.models.skill_group import SkillGroup
            try:
                grp = SkillGroup.objects.get(code=assignee['group'])
                group_id = grp.id
            except SkillGroup.DoesNotExist:
                pass

        if not group_id and assign_group:
            group_id = assign_group.get('id')

        if not group_id:
            return False

        # 找下一级 EscalationLevel
        from itsm.models.escalation import EscalationLevel
        next_level = current_level + 1
        try:
            level_config = EscalationLevel.objects.get(
                group_id=group_id, level=next_level
            )
        except EscalationLevel.DoesNotExist:
            return False  # 没有配置更高级别

        # 计算基准时间
        if escalated_at:
            from django.utils.dateparse import parse_datetime
            baseline = parse_datetime(escalated_at) if isinstance(escalated_at, str) else escalated_at
            if not baseline:
                baseline = ticket.create_datetime
        else:
            # 使用 TicketStatus 创建时间或 Ticket 创建时间
            from itsm.models.ticket import TicketStatus
            status_record = TicketStatus.objects.filter(
                ticket=ticket, status='RUNNING'
            ).order_by('create_datetime').first()
            baseline = status_record.create_datetime if status_record else ticket.create_datetime

        elapsed = (timezone.now() - baseline).total_seconds()
        if elapsed < level_config.timeout_minutes * 60:
            return False  # 未超时

        # 执行升级动作
        from itsm.models.transfer_log import TicketTransferLog
        from django.contrib.auth import get_user_model
        User = get_user_model()

        with transaction.atomic():
            meta['escalation_level'] = next_level
            meta['escalated_at'] = timezone.now().isoformat()

            if level_config.action == 'notify_only':
                ticket.meta = meta
                ticket.current_status = 'escalated'
                ticket.save(update_fields=['meta', 'current_status'])
                # TODO: send notification to level_config.notify_users

            elif level_config.action == 'transfer_to_leader':
                leader = level_config.group.leader
                if leader:
                    meta['assignee'] = {
                        'id': leader.id,
                        'username': leader.username,
                        'name': leader.name,
                        'group': level_config.group.code,
                    }
                    ticket.meta = meta
                    ticket.current_status = 'assigned'
                    ticket.save(update_fields=['meta', 'current_status'])

                    TicketTransferLog.objects.create(
                        ticket=ticket,
                        from_user_id=(assignee or {}).get('id'),
                        to_user=leader,
                        from_group_id=group_id,
                        to_group_id=group_id,
                        transfer_type='auto_escalation',
                        reason=f'升级({level_config.name}): 转给组长',
                    )

            elif level_config.action == 'transfer_to_next_level':
                ticket.meta = meta
                ticket.current_status = 'escalated'
                ticket.save(update_fields=['meta', 'current_status'])

                TicketTransferLog.objects.create(
                    ticket=ticket,
                    from_user_id=(assignee or {}).get('id'),
                    from_group_id=group_id,
                    to_group_id=group_id,
                    transfer_type='auto_escalation',
                    reason=f'升级({level_config.name}): 进入下一级',
                )

        logger.info(
            "Ticket %s escalated to level %d (action=%s)",
            ticket.sn, next_level, level_config.action,
        )
        return True
