# -*- coding: utf-8 -*-
"""ITSM services — state machine, SLA timer, escalation engine
"""

import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

FSM = 'itsm_state_machine'

# ─── 状态机转换表 ───
INCIDENT_TRANSITIONS = {
    'new': ['assigned', 'closed'],
    'assigned': ['in_progress', 'escalated'],
    'in_progress': ['resolved', 'escalated'],
    'resolved': ['closed'],
    'closed': [],
    'escalated': ['in_progress', 'resolved'],
}

CHANGE_TRANSITIONS = {
    'draft': ['pending_approval', 'cancelled'],
    'pending_approval': ['approved', 'rejected'],
    'approved': ['in_progress', 'cancelled'],
    'rejected': ['closed'],
    'in_progress': ['completed', 'rolled_back'],
    'completed': ['closed'],
    'rolled_back': ['closed'],
    'closed': [],
}


def can_transition(current_status: str, target_status: str, transitions: dict) -> bool:
    """检查状态转换是否合法"""
    allowed = transitions.get(current_status, [])
    return target_status in allowed


def apply_sla_policy(incident, sla_policy) -> dict:
    """应用 SLA 策略，计算截止时间"""
    now = timezone.now()
    incident.sla_policy = sla_policy
    incident.sla_deadline = now + timedelta(minutes=sla_policy.resolve_minutes)
    incident.sla_status = 'ok'
    return {
        'sla_deadline': incident.sla_deadline,
        'sla_status': 'ok',
        'response_by': now + timedelta(minutes=sla_policy.response_minutes),
    }


def check_sla_compliance(incident) -> str:
    """检查 SLA 合规状态"""
    if not incident.sla_deadline:
        return 'ok'
    now = timezone.now()
    if now > incident.sla_deadline:
        return 'breached'
    remaining = (incident.sla_deadline - now).total_seconds()
    total = (incident.sla_deadline - incident.create_datetime).total_seconds()
    if total > 0 and remaining / total < 0.2:
        return 'warning'
    return 'ok'


def auto_escalate(incident) -> bool:
    """自动升级 — 超时未处理返回 True（已废弃，由 EscalationService 替代）"""
    return False
