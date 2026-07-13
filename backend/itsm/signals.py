# -*- coding: utf-8 -*-
"""ITSM 信号处理器 — 工单状态变更时自动触发 SLA/通知 + post_set_state 同步"""

import json
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from opsflow.core.flow_engine import flow_execution_finished
from pipeline.eri.signals import post_set_state
from bamboo_engine import states
from pipeline.eri.models import Node as EriNode

logger = logging.getLogger(__name__)


@receiver(post_save, sender='itsm.Ticket')
def ticket_post_save(sender, instance, created, **kwargs):
    """工单保存后 — 根据状态变化触发 SLA"""
    if created:
        return
    try:
        current = instance.current_status
        from itsm.services.sla_engine import SlaEngine
        if current == 'suspended':
            SlaEngine.pause_ticket_sla(instance)
        elif current == 'running':
            SlaEngine.resume_ticket_sla(instance)
        elif current in ('finished', 'terminated', 'failed'):
            SlaEngine.stop_ticket_sla(instance)
    except Exception as e:
        logger.warning(f'SLA signal error: {e}')


@receiver(post_set_state)
def itsm_post_set_state_handler(sender, node_id, to_state, version, root_id, **kwargs):
    """监听 bamboo 节点状态变更 → 同步 ITSM 工单状态

    非 ITSM 工单的 pipeline（如 OpsFlow）会安静跳过。
    """
    pipeline_id = root_id or node_id
    from itsm.models import Ticket
    try:
        ticket = Ticket.objects.get(pipeline_id=pipeline_id)
    except Ticket.DoesNotExist:
        return  # 不是 ITSM 工单 pipeline，安静跳过

    # 更新节点状态快照
    node_status_before = dict(ticket.node_status or {})  # capture before mutation for LEAVE detection
    node_status = dict(ticket.node_status or {})
    # bamboo 状态 → ITSM 语义映射
    status_map = {
        states.READY: 'pending',
        states.RUNNING: 'running',
        states.FINISHED: 'finished',
        states.FAILED: 'failed',
        states.SUSPENDED: 'suspended',
        states.REVOKED: 'cancelled',
        states.BLOCKED: 'blocked',
    }
    mapped = status_map.get(to_state, to_state)
    node_status[node_id] = mapped
    ticket.node_status = node_status

    # 更新 TicketStatus（含 SLA 启动）
    if to_state == states.RUNNING:
        ticket.state_history = list(ticket.state_history or []) + [{
            'state_id': node_id,
            'status': 'running',
            'timestamp': str(ticket.update_datetime or ticket.create_datetime),
        }]

    ticket.save(update_fields=['node_status', 'state_history'])

    # pipeline 结束检测：EndEvent 节点 FINISHED → 更新工单状态
    if to_state == states.FINISHED:
        try:
            nd = EriNode.objects.values_list('detail', flat=True).get(node_id=node_id)
            if nd:
                detail_data = json.loads(nd) if isinstance(nd, str) else nd
                if detail_data.get('type') in ('EmptyEndEvent', 'ExecutableEndEvent'):
                    ticket.do_before_end_pipeline()
        except (EriNode.DoesNotExist, json.JSONDecodeError, TypeError, AttributeError):
            pass

    # SLA start unified in ITSMEngine.run() — no longer triggered per-node

    # ---- Trigger enqueue for ENTER_STATE / LEAVE_STATE ----
    # Resolve bamboo node_id → ITSM State.id via _pipeline_id_map (stored on ticket.meta)
    _enqueue_triggers(ticket, node_id, to_state, node_status_before, status_map)


def _resolve_state_id(ticket, node_id):
    """Map bamboo element node_id → ITSM State.id via _pipeline_id_map_rev."""
    meta = ticket.meta or {}
    # Use pre-built reverse map if available
    rev_map = meta.get('_pipeline_id_map_rev')
    if rev_map and node_id in rev_map:
        return rev_map[node_id]
    # Fallback: build reverse map from forward map (one-time linear scan)
    id_map = meta.get('_pipeline_id_map', {})
    if not id_map:
        return None
    rev_map = {}
    for state_id_str, elem_id in id_map.items():
        try:
            rev_map[elem_id] = int(state_id_str)
        except (ValueError, TypeError):
            pass
    # Cache in ticket.meta for subsequent calls
    ticket.meta['_pipeline_id_map_rev'] = rev_map
    ticket.save(update_fields=['meta'])
    return rev_map.get(node_id)


def _enqueue_triggers(ticket, node_id, to_state, node_status_before, status_map):
    """Enqueue trigger executions for ENTER_STATE / LEAVE_STATE events."""
    state_id = _resolve_state_id(ticket, node_id)
    if not state_id:
        return

    from itsm.models.state import State as StateModel
    from itsm.services.trigger_service import TriggerExecutor

    try:
        st = StateModel.objects.get(id=state_id)
    except StateModel.DoesNotExist:
        return

    # Exclude START/END nodes — FLOW_START/FLOW_END cover these
    if st.type in ('START', 'END'):
        return

    # ENTER_STATE: node becomes READY (about to execute)
    if to_state == states.READY:
        TriggerExecutor.enqueue(ticket, 'ENTER_STATE', state_id)

    # LEAVE_STATE: node was RUNNING → now transitioning away
    previous_mapped = node_status_before.get(node_id)
    if previous_mapped == status_map.get(states.RUNNING, 'running'):
        TriggerExecutor.enqueue(ticket, 'LEAVE_STATE', state_id)


# ── OpsFlow completion → bamboo callback ──

@receiver(flow_execution_finished)
def on_opsflow_finished(sender, execution, status, **kwargs):
    """OpsFlow execution done → callback ITSM pipeline's waiting TASK node."""
    ctx = execution.context or {}
    if ctx.get('trigger') != 'itsm_auto_task':
        return
    ticket_id = ctx.get('ticket_id')
    state_id = ctx.get('state_id')
    logger.info('[opsflow_finished] execution=%s status=%s ticket=%s state=%s',
                execution.id, status, ticket_id, state_id)
    if not ticket_id or not state_id:
        logger.warning('[opsflow_finished] missing ticket_id/state_id in context — abort')
        return
    from itsm.models.ticket import Ticket
    ticket = Ticket.objects.filter(id=ticket_id).first()
    if not ticket or not ticket.pipeline_id:
        logger.warning('[opsflow_finished] ticket %s missing or has no pipeline_id — abort', ticket_id)
        return
    # Resolve state_id → bamboo activity id the same way form/approval callbacks do
    # (_pipeline_id_map is keyed by node_key, NOT state_id).
    from itsm.services.bamboo_engine import resolve_activity_id, activity_callback
    node_id = resolve_activity_id(ticket, state_id)
    logger.info('[opsflow_finished] resolved activity_id=%s for ticket=%s state=%s',
                node_id, ticket_id, state_id)
    if not node_id:
        logger.error('[opsflow_finished] could not resolve activity_id for state %s — node will hang', state_id)
        return
    # Wake the waiting TASK node. activity_callback resolves the node's current
    # unfinished Schedule version; the node reads the execution result from its
    # own outputs, so callback_data is only informational.
    ok = activity_callback(node_id, {'source': 'opsflow_finished', 'opsflow_status': status})
    logger.info('[opsflow_finished] activity_callback(%s) → %s', node_id, ok)
