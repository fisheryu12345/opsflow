# -*- coding: utf-8 -*-
"""ITSM action adapter — 创建 ITSM 工单"""

import logging

from .. import BaseActionAdapter, ActionContext, ActionResult

logger = logging.getLogger(__name__)
FSM = 'itsm_action'


class ItsmAction(BaseActionAdapter):
    """ITSM 工单创建适配器"""

    def execute(self, context: ActionContext) -> ActionResult:
        try:
            from itsm.models.incident import Incident
            import uuid

            severity_map = {1: 'P1', 2: 'P2', 3: 'P3'}
            incident = Incident.objects.create(
                incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
                title=f"[告警自愈] {context.alert_title}",
                description=context.config.get('description', ''),
                priority=severity_map.get(context.severity, 'P3'),
                source='alert',
                alert_id=context.alert_id,
            )
            return ActionResult(success=True, message=f"Incident created: {incident.incident_id}")
        except ImportError:
            return ActionResult(success=False, message='ITSM module not available')
        except Exception as e:
            logger.error(f"[ItsmAction] Error: {e}")
            return ActionResult(success=False, message=str(e))
