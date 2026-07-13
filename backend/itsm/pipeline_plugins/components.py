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
            # Verify outputs are set
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
                # Rejected — reset node states, revoke pipeline, return to draft
                data.set_outputs('field_approve_result', 'rejected')
                from bamboo_engine import api as pipeline_api
                from pipeline.eri.runtime import BambooDjangoRuntime
                revoke_result = pipeline_api.revoke_pipeline(BambooDjangoRuntime(), ticket.pipeline_id)
                if not revoke_result.result:
                    logger.error(f'[itsm_approval] Failed to revoke pipeline {ticket.pipeline_id}: {revoke_result.message}')
                TicketStatus.objects.filter(ticket=ticket, status='RUNNING').update(status='WAIT')
                ticket.set_status('draft', operator)
                ticket.pipeline_id = ''
                ticket.node_status = {}
                ticket.save(update_fields=['pipeline_id', 'node_status'])
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
    """自动任务节点 — OpsFlow 集成：用户填写参数后启动 OpsFlow，等待完成后继续"""

    __need_schedule__ = True
    # Two callbacks are expected: (1) user submits parameters → start OpsFlow,
    # (2) OpsFlow execution finishes → finalize the node. Multi-callback keeps
    # the schedule alive between them.
    __multi_callback_enabled__ = True

    def need_schedule(self):
        # A TASK node not bound to an OpsFlow template auto-completes in
        # execute() (legacy pass-through behavior) and must NOT wait for a
        # callback that will never arrive — otherwise the node hangs forever.
        if getattr(self, '_auto_completed', False):
            return False
        return super().need_schedule()

    def execute(self, data, parent_data):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        extras = data.get_one_of_inputs('extras') or {}
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False

        template_id = extras.get('opsflow_template_id')
        if not template_id:
            # No OpsFlow bound → behave as a legacy pass-through auto task:
            # complete synchronously, no schedule/callback needed.
            ticket.do_before_enter_state(state_id)
            ticket.do_in_state(state_id, {'auto_executed': True}, 'system')
            ticket.do_before_exit_state(state_id, 'system')
            self._auto_completed = True
            logger.info('[itsm_auto_task] No OpsFlow template — auto-completed for ticket #%s', ticket_id)
            return True

        # Record the bound OpsFlow template id so the frontend knows to render
        # the parameter form. The variable definitions themselves are fetched
        # live from the /global-variables/ API, so we don't duplicate them here.
        ticket.meta = ticket.meta or {}
        ticket.meta['_opsflow_params'] = {'template_id': template_id}
        ticket.save(update_fields=['meta'])
        ticket.do_before_enter_state(state_id)
        return True

    def schedule(self, data, parent_data, callback_data=None):
        ticket_id = data.get_one_of_inputs('ticket_id')
        state_id = data.get_one_of_inputs('state_id')
        extras = data.get_one_of_inputs('extras') or {}

        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            logger.error(f'Ticket #{ticket_id} not found')
            return False

        # ── Phase 2: OpsFlow already started → this callback signals completion ──
        # Detected by the execution id persisted in Phase 1 (not by callback_data,
        # since the completion callback also carries data).
        exec_id = data.get_one_of_outputs('opsflow_execution_id')
        if exec_id:
            return self._finalize_opsflow(data, ticket, state_id, exec_id)

        # ── Phase 1: user submitted parameters → start OpsFlow, then wait ──
        # NOTE: returning a falsy value from schedule() marks the bamboo node
        # FAILED. To keep a MULTIPLE_CALLBACK node waiting we must return True
        # WITHOUT calling finish_schedule().
        if not callback_data:
            return True  # still waiting for the user to submit parameters
        form_fields = callback_data.get('fields', {}) or {}
        ticket.do_in_state(state_id, form_fields,
                           callback_data.get('operator', 'system'))

        template_id = extras.get('opsflow_template_id')
        if not template_id:
            # No OpsFlow configured — backward compat: complete immediately
            ticket.do_before_exit_state(state_id, 'system')
            self.finish_schedule()
            return True

        resolved = self._resolve_vars(extras, form_fields, ticket)
        execution = self._create_opsflow_execution(template_id, extras, resolved, ticket, state_id)
        # Persist the execution id BEFORE kicking off the engine so the
        # completion callback (Phase 2) can always resolve it. Do NOT
        # finish_schedule — the node stays alive until OpsFlow completes and
        # flow_execution_finished fires a second callback.
        data.set_outputs('opsflow_execution_id', execution.id)
        self._start_opsflow_engine(execution, extras)
        logger.info('[itsm_auto_task] Started OpsFlow execution #%s for ticket #%s, '
                    'awaiting completion', execution.id, ticket_id)
        return True

    def _finalize_opsflow(self, data, ticket, state_id, exec_id):
        """Phase 2 — OpsFlow execution finished: record result and exit node.

        Returning False here would mark the bamboo node FAILED, so the
        keep-waiting paths return True (without finish_schedule) instead.
        """
        from opsflow.models import FlowExecution as OpsFlowExecution
        try:
            execution = OpsFlowExecution.objects.get(id=exec_id)
        except OpsFlowExecution.DoesNotExist:
            logger.error('[itsm_auto_task] OpsFlow execution #%s not found — keep waiting', exec_id)
            return True  # keep the node alive; do NOT fail it on a transient miss

        if execution.status in ('running', 'pending'):
            return True  # spurious/early callback — keep waiting, don't fail

        ticket.meta = ticket.meta or {}
        if execution.status == 'completed':
            merged, by_node = self._collect_execution_outputs(execution)
            ticket.meta['opsflow_result'] = {
                'execution_id': execution.id,
                'status': 'FINISHED',
                'outputs': by_node,
            }
            # Flat outputs (opsflow_<key>) keep the existing gateway-reference
            # contract but collide when two nodes emit the same key (last wins);
            # also expose node-scoped keys (opsflow_<node>_<key>) so gateways can
            # disambiguate, and warn when a flat key is overwritten.
            seen = {}
            for node_id, out in by_node.items():
                for k, v in out.items():
                    if k in seen and seen[k] != node_id:
                        logger.warning('[itsm_auto_task] output name collision on %r '
                                       '(nodes %s, %s) — flat opsflow_%s keeps last value',
                                       k, seen[k], node_id, k)
                    seen[k] = node_id
                    data.set_outputs(f'opsflow_{node_id}_{k}', v)
            for k, v in merged.items():
                data.set_outputs(f'opsflow_{k}', v)
            data.set_outputs('opsflow_result', 'FINISHED')
            if hasattr(ticket, 'add_comment'):
                ticket.add_comment(f"OpsFlow「{execution.template.name}」执行完成")
        else:
            ticket.meta['opsflow_result'] = {
                'execution_id': execution.id,
                'status': 'FAILED',
            }
            # Expose the result so a downstream gateway can branch on failure.
            data.set_outputs('opsflow_result', 'FAILED')
            if hasattr(ticket, 'add_comment'):
                ticket.add_comment("OpsFlow执行失败")

        ticket.save(update_fields=['meta'])
        ticket.do_before_exit_state(state_id, 'system')
        self.finish_schedule()
        logger.info('[itsm_auto_task] OpsFlow execution #%s %s → node finished for ticket #%s',
                    exec_id, execution.status, ticket.id)
        return True

    @staticmethod
    def _collect_execution_outputs(execution):
        """Aggregate node outputs (FlowExecution has no execution-level outputs).

        Returns (merged, by_node): merged is a flat dict of all node outputs
        with later nodes winning; by_node maps node_id → that node's outputs.
        """
        from opsflow.models.execution import NodeExecutionTrace
        merged, by_node = {}, {}
        traces = NodeExecutionTrace.objects.filter(
            execution=execution).order_by('entered_at')
        for tr in traces:
            out = tr.outputs or {}
            if not isinstance(out, dict):
                continue
            by_node[tr.node_id] = out
            merged.update(out)
        return merged, by_node

    @staticmethod
    def _resolve_vars(extras, form_fields, ticket):
        """Merge static variable mapping + runtime form fields"""
        import re
        mapping = extras.get('opsflow_variable_mapping', {})
        result = {}
        ctx = {
            'ticket_id': ticket.id,
            'ticket_sn': getattr(ticket, 'sn', ''),
            'ticket_title': ticket.title if hasattr(ticket, 'title') else '',
            'ticket_type': ticket.itsm_type if hasattr(ticket, 'itsm_type') else '',
            'ticket_priority': ticket.priority if hasattr(ticket, 'priority') else '',
            'ticket_creator': str(ticket.creator or ''),
            'ticket_status': ticket.status if hasattr(ticket, 'status') else '',
        }
        fm = (ticket.meta or {}).get('form_data', {})
        for k, v in fm.items():
            ctx[f'field.{k}'] = v
        # The just-submitted values take precedence over any stale form_data
        # when interpolating ${field.X}.
        for k, v in (form_fields or {}).items():
            ctx[f'field.{k}'] = v
        for k, v in mapping.items():
            if isinstance(v, str):
                result[k] = re.sub(
                    r'\$\{(\w+(?:\.\w+)?)\}',
                    lambda m: str(ctx.get(m.group(1), m.group(0))),
                    v,
                )
            else:
                # Non-string mapping values (int/bool/list/dict) pass through as-is.
                result[k] = v
        result.update(form_fields)  # runtime overrides static
        return result

    @staticmethod
    def _create_opsflow_execution(template_id, extras, resolved_vars, ticket, state_id):
        """Create an OpsFlow execution (not started yet).

        The ITSM state_id is stored in context so on_opsflow_finished can resolve
        the waiting TASK node via the ticket's _pipeline_id_map.
        """
        from opsflow.models import FlowTemplate as FlowTemplateModel
        from opsflow.models import FlowExecution as OpsFlowExecution
        template = FlowTemplateModel.objects.get(id=template_id)
        # Build execution snapshot and inject resolved runtime values into its
        # global_vars (FlowExecution reads global_vars from template_snapshot at
        # run time — there is no separate global_vars model field).
        snapshot = dict(template.snapshot or {}) or {
            'pipeline_tree': template.pipeline_tree or {},
            'global_vars': template.global_vars or {},
        }
        frozen_vars = dict(snapshot.get('global_vars', {}))
        for key, value in (resolved_vars or {}).items():
            existing = frozen_vars.get(key)
            if isinstance(existing, dict) and 'value' in existing:
                frozen_vars[key] = {**existing, 'value': value}
            else:
                frozen_vars[key] = value
        snapshot['global_vars'] = frozen_vars
        execution = OpsFlowExecution.objects.create(
            template=template,
            created_by_id=ticket.creator,  # ticket.creator is a user-id int, not an instance
            context={
                'trigger': 'itsm_auto_task',
                'ticket_id': ticket.id,
                'ticket_sn': getattr(ticket, 'sn', ''),
                'state_id': state_id,  # ITSM State.id — used to wake this node on completion
            },
            template_snapshot=snapshot,
        )
        return execution

    @staticmethod
    def _start_opsflow_engine(execution, extras):
        """Apply optional scheme and start the OpsFlow execution asynchronously."""
        from opsflow.core.flow_engine import FlowEngine
        scheme_id = extras.get('opsflow_scheme_id')
        if scheme_id:
            execution.apply_scheme(scheme_id)
        FlowEngine(execution).start(sync=False)
        return execution


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
