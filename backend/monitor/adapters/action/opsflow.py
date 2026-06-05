# -*- coding: utf-8 -*-
"""OpsFlow action adapter — 触发 OpsFlow 自动化流程执行"""

import logging
import requests

from .. import BaseActionAdapter, ActionContext, ActionResult

logger = logging.getLogger(__name__)
FSM = 'opsflow_action'


class OpsflowAction(BaseActionAdapter):
    """OpsFlow 流程触发适配器 — 通过 OpsFlow API 触发自愈流程"""

    def execute(self, context: ActionContext) -> ActionResult:
        template_id = self.config.get('template_id', '')
        api_url = self.config.get('api_url', 'http://localhost:8000')
        api_token = self.config.get('api_token', '')

        if not template_id:
            return ActionResult(success=False, message='template_id not configured')

        try:
            headers = {'Authorization': f'Bearer {api_token}'} if api_token else {}
            payload = {
                'template_id': template_id,
                'title': f'[告警自愈] {context.alert_title}',
                'context': {
                    'alert_id': context.alert_id,
                    'severity': context.severity,
                    'config': context.config,
                },
            }
            resp = requests.post(
                f'{api_url}/api/v2/open/trigger_execution/',
                json=payload, headers=headers, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get('code') == 2000:
                return ActionResult(success=True, message=f"Execution created: {data.get('data', {}).get('id', '')}")
            return ActionResult(success=False, message=data.get('msg', ''))
        except requests.RequestException as e:
            logger.error(f"[OpsflowAction] Execute failed: {e}")
            return ActionResult(success=False, message=str(e))
        except Exception as e:
            logger.error(f"[OpsflowAction] Error: {e}")
            return ActionResult(success=False, message=str(e))
