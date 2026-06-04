# -*- coding: utf-8 -*-
"""ITSM SLA 检查命令 — 检查所有活跃工单的 SLA 状态

用法:
  python manage.py itsm_check_sla              # 单次检查
  python manage.py itsm_check_sla --watch      # 持续监控（每60秒）
"""

import time
import logging

from django.core.management.base import BaseCommand
from itsm.services.sla_engine import SlaEngine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check SLA status for all active ITSM tickets'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true', help='Run continuously (every 60s)')
        parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')

    def handle(self, *args, **options):
        watch = options.get('watch', False)
        interval = options.get('interval', 60)

        self.stdout.write('ITSM SLA checker started')

        while True:
            try:
                result = SlaEngine.check_all_active_sla()
                self.stdout.write(
                    f'Checked {result["checked"]} tickets, '
                    f'{result["warnings"]} warnings, '
                    f'{result["violations"]} violations'
                )
            except Exception as e:
                self.stderr.write(f'Error: {e}')

            if not watch:
                break
            time.sleep(interval)
