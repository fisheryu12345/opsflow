# -*- coding: utf-8 -*-
"""AWX/Tower action adapter — 触发 AWX 作业执行"""

import logging
import requests

from .. import BaseActionAdapter, ActionContext, ActionResult

logger = logging.getLogger(__name__)
FSM = 'awx_action'


class AwxAction(BaseActionAdapter):
    """AWX/Tower 作业触发适配器"""

    def execute(self, context: ActionContext) -> ActionResult:
        awx_url = self.config.get('awx_url', '').rstrip('/')
        username = self.config.get('username', '')
        password = self.config.get('password', '')
        template_id = self.config.get('template_id', '')

        if not awx_url or not template_id:
            return ActionResult(success=False, message='AWX not configured')

        try:
            session = requests.Session()
            session.auth = (username, password) if username else None

            resp = session.post(
                f'{awx_url}/api/v2/job_templates/{template_id}/launch/',
                json={'extra_vars': {
                    'alert_id': context.alert_id,
                    'alert_title': context.alert_title,
                    'severity': context.severity,
                    **context.config,
                }},
                timeout=30,
            )
            resp.raise_for_status()
            job_data = resp.json()
            job_id = job_data.get('id', '')
            return ActionResult(success=True, message=f'AWX job {job_id} launched')
        except requests.RequestException as e:
            logger.error(f"[AwxAction] Launch failed: {e}")
            return ActionResult(success=False, message=str(e))
