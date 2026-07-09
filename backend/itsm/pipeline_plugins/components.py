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
            # Skip if already completed synchronously (service catalog auto-complete)
            existing = TicketStatus.objects.filter(
                ticket=ticket, state_id=state_id
            ).first()
            if existing and existing.status == 'FINISHED':
                logger.info(
                    '[itsm_fill] Node #%s already FINISHED, skip for ticket #%s',
                    state_id, ticket_id
                )
                return True  # Callback from _submit_flow() will handle schedule
            ticket.do_before_enter_state(state_id)
            logger.info(f'[itsm_fill] Enter fill form state #{state_id} for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True

    def schedule(self, data, parent_data, callback_data=None):
        # Check if node already completed synchronously (service catalog flow)
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        existing = TicketStatus.objects.filter(
            ticket_id=ticket_id, state_id=state_id
        ).first()
        if existing and existing.status == 'FINISHED':
            logger.info(
                '[itsm_fill] Node #%s already FINISHED (sync), skip for ticket #%s',
                state_id, ticket_id
            )
            self.finish_schedule()
            return True

        # 首次回调无 callback_data 时，检查 ticket.meta 是否有 form_data
        # （来自服务目录提交流程），有则自动完成
        if not callback_data:
            return self._try_auto_complete(data, parent_data)
        # 正常回调（用户主动提交表单）
        ticket_id = callback_data.get('ticket_id')
        state_id = callback_data.get('state_id')
        fields = callback_data.get('fields', {})
        operator = callback_data.get('operator', '')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_in_state(state_id, fields, operator)
            # 输出表单字段（供网关条件引用）
            for field_key, field_val in fields.items():
                data.set_outputs(f'field_{field_key}', field_val)
            ticket.do_before_exit_state(state_id, operator)
            self.finish_schedule()
            logger.info(f'[itsm_fill] Fill form done for ticket #{ticket_id}')
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False
        return True

    def _try_auto_complete(self, data, parent_data):
        """尝试从 ticket.meta.form_data 自动完成填单节点"""
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            form_data = (ticket.meta or {}).get('form_data', {})
            if not form_data:
                return False  # 无初始数据，继续等待用户提交
            logger.info(
                '[itsm_fill] Auto-completing node #%s with form_data for ticket #%s',
                state_id, ticket_id
            )
            ticket.do_in_state(state_id, form_data, 'system')
            for field_key, field_val in form_data.items():
                data.set_outputs(f'field_{field_key}', field_val)
            ticket.do_before_exit_state(state_id, 'system')
            # 清除 form_data，防止后续其他 NORMAL 节点误自动完成
            meta = dict(ticket.meta or {})
            meta.pop('form_data', None)
            ticket.meta = meta
            ticket.save(update_fields=['meta'])
            self.finish_schedule()
            return True
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False


class ItsmApprovalService(Service):
    """审批节点 — 支持单签/会签"""
    __need_schedule__ = True

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        try:
            ticket = Ticket.objects.get(id=ticket_id)
            ticket.do_before_enter_state(state_id)
            logger.info(f'[itsm_approval] Enter approval state #{state_id} for ticket #{ticket_id} pipeline={ticket.pipeline_id}')
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
        logger.info(f'[itsm_approval] schedule callback: ticket={ticket_id} state={state_id} approve={approve_result}')
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
                # Rejected — revoke pipeline first, then finish + reset to draft
                data.set_outputs('field_approve_result', 'rejected')
                from bamboo_engine import api as pipeline_api
                from pipeline.eri.runtime import BambooDjangoRuntime
                revoke_result = pipeline_api.revoke_pipeline(BambooDjangoRuntime(), ticket.pipeline_id)
                if not revoke_result.result:
                    logger.error(f'[itsm_approval] Failed to revoke pipeline {ticket.pipeline_id}: {revoke_result.message}')
                ticket.set_status('draft', operator)
                ticket.pipeline_id = ''
                ticket.save(update_fields=['pipeline_id'])
                self.finish_schedule()
                return True
            # Save form fields + approval result
            form_fields = callback_data.get('fields', {}) or {}
            state_fields = {**form_fields, 'approve_result': approve_result, 'comment': comment}
            if ticket.check_approval_finished(state_id):
                ticket.do_in_state(state_id, state_fields, operator)
                data.set_outputs('field_approve_result', 'approved')  # 供条件引用
                ticket.do_before_exit_state(state_id, operator)
                self.finish_schedule()
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
        if not hasattr(self, '_approval_svc'):
            self._approval_svc = ItsmApprovalService()
        return self._approval_svc.execute(data, parent_data)

    def schedule(self, data, parent_data, callback_data=None):
        if not hasattr(self, '_approval_svc'):
            self._approval_svc = ItsmApprovalService()
        result = self._approval_svc.schedule(data, parent_data, callback_data)
        # 只在底层的审批服务也认为已完成时才标记会签完成
        if result and self._approval_svc.is_schedule_finished():
            self.finish_schedule()
        return result


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
