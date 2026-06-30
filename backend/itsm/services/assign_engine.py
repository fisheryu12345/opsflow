# -*- coding: utf-8 -*-
"""AssignEngine — 工单自动分派引擎

流程: 触发 → 规则匹配 → 人选确定 → 执行分派
"""

import logging
import json

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class AssignEngine:
    """ITSM 工单自动分派引擎"""

    def __init__(self, ticket, project_id=None):
        self.ticket = ticket
        self.project_id = project_id or (ticket.project_id if ticket else None)

    def auto_assign(self):
        """执行自动分派，返回分派结果 dict"""
        from itsm.models.assign_rule import AssignRule
        from itsm.models.skill_group import SkillGroup, OnDutySchedule
        from itsm.models.transfer_log import TicketTransferLog
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # 1. 规则匹配
        rule = self._match_rule()
        if not rule:
            # 2. 回落: category.default_group
            category = self.ticket.category
            if category and category.auto_assign and category.default_group:
                return self._assign_to_group(category.default_group, rule=None)
            logger.info("Ticket %s: no assign rule matched, skipping auto-assign", self.ticket.sn)
            return None

        target_group = rule.target_group

        # 3. 按 assign_mode 确定人选
        user = None
        if rule.assign_mode == 'to_group':
            # 分派到组，不指定具体人
            return self._assign_to_group(target_group, rule)

        elif rule.assign_mode == 'to_onduty':
            today = timezone.localdate()
            duty = OnDutySchedule.objects.filter(
                group=target_group, duty_date=today, duty_type='primary'
            ).select_related('user').first()
            if not duty:
                duty = OnDutySchedule.objects.filter(
                    group=target_group, duty_date=today, duty_type='backup'
                ).select_related('user').first()
            if duty:
                user = duty.user
            else:
                # 无值班 -> 转组长
                user = target_group.leader

        elif rule.assign_mode == 'least_busy':
            users = target_group.members.all()
            if not users:
                user = target_group.leader
            else:
                # 取待办最少的人
                from itsm.models.ticket import Ticket
                user_counts = []
                for u in users:
                    cnt = Ticket.objects.filter(
                        current_status__in=['assigned', 'receiving', 'running'],
                        meta__assignee__id=u.id,
                    ).count()
                    user_counts.append((cnt, u))
                user_counts.sort(key=lambda x: x[0])
                user = user_counts[0][1]

        if not user:
            logger.warning("Ticket %s: no assignee resolved (group=%s, mode=%s)", self.ticket.sn, target_group.code, rule.assign_mode)
            return None

        # 4. 执行分派
        with transaction.atomic():
            meta = dict(self.ticket.meta or {})
            if user:
                meta['assignee'] = {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name,
                    'group': target_group.code,
                }
            else:
                meta['assignee'] = None
            self.ticket.meta = meta
            self.ticket.current_status = 'assigned'
            self.ticket.save(update_fields=['meta', 'current_status'])

            TicketTransferLog.objects.create(
                ticket=self.ticket,
                to_user=user,
                to_group=target_group,
                transfer_type='auto_assign',
                reason=f'规则[{rule.name}] 模式={rule.assign_mode}' if rule else '分类默认技能组',
            )

        logger.info(
            "Ticket %s auto-assigned to %s (group=%s, mode=%s)",
            self.ticket.sn, user, target_group.code, rule.assign_mode if rule else 'fallback',
        )
        return {'user': user, 'group': target_group, 'rule': rule}

    def _match_rule(self):
        """按优先级匹配 AssignRule — project-scoped"""
        from itsm.models.assign_rule import AssignRule

        rules = AssignRule.objects.filter(is_active=True)
        if self.project_id:
            rules = rules.filter(project_id=self.project_id)
        rules = rules.order_by('priority')
        for rule in rules:
            if rule.match_itsm_type and rule.match_itsm_type != self.ticket.itsm_type:
                continue
            if rule.match_category and rule.match_category_id != self.ticket.category_id:
                continue
            if rule.match_priority and rule.match_priority != self.ticket.priority:
                continue
            return rule
        return None

    def _assign_to_group(self, group, rule):
        """分派到组（不指定具体人）"""
        from itsm.models.transfer_log import TicketTransferLog

        with transaction.atomic():
            meta = dict(self.ticket.meta or {})
            meta['assign_group'] = {'id': group.id, 'name': group.name, 'code': group.code}
            self.ticket.meta = meta
            self.ticket.current_status = 'receiving'
            self.ticket.save(update_fields=['meta', 'current_status'])

            TicketTransferLog.objects.create(
                ticket=self.ticket,
                to_group=group,
                transfer_type='auto_assign',
                reason=f'分派到组[{group.name}]，等待认领' + (f' (规则:{rule.name})' if rule else ''),
            )

        logger.info("Ticket %s assigned to group %s (receiving)", self.ticket.sn, group.code)
        return {'group': group, 'rule': rule}

    @staticmethod
    def manual_assign(ticket, to_user, to_group=None, reason=''):
        """手动分派/转派"""
        from itsm.models.transfer_log import TicketTransferLog

        meta = dict(ticket.meta or {})
        old_assignee = meta.get('assignee')

        with transaction.atomic():
            meta['assignee'] = {
                'id': to_user.id,
                'username': to_user.username,
                'name': to_user.name,
                'group': to_group.code if to_group else '',
            }
            ticket.meta = meta
            ticket.current_status = 'assigned'
            ticket.save(update_fields=['meta', 'current_status'])

            TicketTransferLog.objects.create(
                ticket=ticket,
                from_user_id=old_assignee.get('id') if old_assignee else None,
                to_user=to_user,
                to_group=to_group,
                transfer_type='manual',
                reason=reason or '手工分派',
            )

        logger.info("Ticket %s manually assigned to %s", ticket.sn, to_user.username)
