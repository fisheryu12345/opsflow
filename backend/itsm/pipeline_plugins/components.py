# -*- coding: utf-8 -*-
"""ITSM Pipeline 组件注册

通过 pipeline.component_framework 注册 ITSM 专属组件:
- itsm_fill_form: 填单节点
- itsm_approval: 审批节点（单签/多签）
- itsm_sign: 会签节点
- itsm_auto_task: 自动任务节点
"""

import json
import logging

from pipeline.core.flow.activity import Service
from pipeline.component_framework.component import Component

from itsm.models.ticket import Ticket, TicketStatus, SignTask

logger = logging.getLogger(__name__)


class ItsmFillFormService(Service):
    """填单节点 — 等待用户提交表单"""
    __need_schedule__ = True

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_before_enter_state(state_id)
            logger.info(f'[itsm_fill] Enter fill form state #{state_id} for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True

    def schedule(self, data, parent_data, callback_data=None):
        if not callback_data:
            return False
        ticket_id = callback_data.get('ticket_id')
        state_id = callback_data.get('state_id')
        fields = callback_data.get('fields', {})
        operator = callback_data.get('operator', '')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_in_state(state_id, fields, operator)
            ticket.do_before_exit_state(state_id, operator)
            self.finish(data)
            logger.info(f'[itsm_fill] Fill form done for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True


class ItsmApprovalService(Service):
    """审批节点 — 支持单签/会签"""
    __need_schedule__ = True

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_before_enter_state(state_id)
            logger.info(f'[itsm_approval] Enter approval state #{state_id} for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True

    def schedule(self, data, parent_data, callback_data=None):
        if not callback_data:
            return False
        ticket_id = callback_data.get('ticket_id')
        state_id = callback_data.get('state_id')
        operator = callback_data.get('operator', '')
        approve_result = callback_data.get('approve_result', 'false')
        comment = callback_data.get('comment', '')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            # Record sign task
            status_record = TicketStatus.objects.filter(
                ticket=ticket, state_id=state_id
            ).first()
            if status_record:
                SignTask.objects.create(
                    ticket=ticket,
                    status=status_record,
                    processor=operator,
                    status_val='passed' if approve_result == 'true' else 'rejected',
                    comment=comment,
                )
            # Check if approval is finished
            if approve_result != 'true':
                # Rejected — terminate pipeline
                ticket.set_status('terminated', operator)
                self.finish(data)
                return True
            if ticket.check_approval_finished(state_id):
                ticket.do_in_state(state_id, {'approve_result': approve_result}, operator)
                ticket.do_before_exit_state(state_id, operator)
                self.finish(data)
                logger.info(f'[itsm_approval] Approval finished for ticket #{ticket_id}')
            else:
                # More signers needed — keep waiting
                logger.info(f'[itsm_approval] Waiting for more approvals on ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True


class ItsmSignService(Service):
    """会签节点 — 多审批人，根据 finish_condition 决定"""
    __need_schedule__ = True
    __multi_callback_enabled__ = True

    def execute(self, data, parent_data):
        return ItsmApprovalService().execute(data, parent_data)

    def schedule(self, data, parent_data, callback_data=None):
        return ItsmApprovalService().schedule(data, parent_data, callback_data)


class ItsmAutoTaskService(Service):
    """自动任务节点 — 执行自动化操作"""
    __need_schedule__ = False

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_before_enter_state(state_id)
            ticket.do_in_state(state_id, {'auto_executed': True}, 'system')
            ticket.do_before_exit_state(state_id, 'system')
            logger.info(f'[itsm_auto] Auto task executed for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True


# Component registrations
class ItsmFillFormComponent(Component):
    name = 'ITSM 填单'
    code = 'itsm_fill_form'
    bound_service = ItsmFillFormService


class ItsmApprovalComponent(Component):
    name = 'ITSM 审批'
    code = 'itsm_approval'
    bound_service = ItsmApprovalService


class ItsmSignComponent(Component):
    name = 'ITSM 会签'
    code = 'itsm_sign'
    bound_service = ItsmSignService


class ItsmAutoTaskComponent(Component):
    name = 'ITSM 自动任务'
    code = 'itsm_auto_task'
    bound_service = ItsmAutoTaskService
