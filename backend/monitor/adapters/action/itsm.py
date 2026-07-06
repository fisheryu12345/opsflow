# -*- coding: utf-8 -*-
"""ITSM action adapter — 创建 ITSM 工单（通过 Ticket 模型）"""

import logging

from .. import BaseActionAdapter, ActionContext, ActionResult

logger = logging.getLogger(__name__)
FSM = 'itsm_action'


class ItsmAction(BaseActionAdapter):
    """ITSM 工单创建适配器"""

    def execute(self, context: ActionContext) -> ActionResult:
        try:
            from itsm.models import Ticket

            severity_map = {1: 'P1', 2: 'P2', 3: 'P3'}
            ticket = Ticket.objects.create(
                title=f"[告警自愈] {context.alert_title}",
                itsm_type='incident',
                priority=severity_map.get(context.severity, 'P3'),
                current_status='assigned',
            )
            return ActionResult(success=True, message=f"Ticket created: {ticket.sn}")
        except ImportError:
            return ActionResult(success=False, message='ITSM module not available')
        except Exception as e:
            logger.error(f"[ItsmAction] Error: {e}")
            return ActionResult(success=False, message=str(e))
