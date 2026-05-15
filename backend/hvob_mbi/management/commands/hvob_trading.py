"""
HVOB-MBI 日内突破交易系统

启动后持续运行（TqSDK 事件循环），完成当日全部日内交易后退出。

用法:
  python manage.py hvob_trading --account=1
  python manage.py hvob_trading --account=1 --dry-run
"""
import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from stock.models import TradingAccount
from stock.infrastructure.tqapi import create_tqapi, safe_close_api


class Command(BaseCommand):
    help = 'HVOB-MBI 日内突破交易系统'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=int, required=True, help='账户ID')
        parser.add_argument('--dry-run', action='store_true', default=False, help='仅观察不交易')

    def handle(self, *args, **options):
        account = TradingAccount.objects.get(id=options['account'], is_active=True)
        close_old_connections()

        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)

            from hvob_mbi.trading_engine import HvobTradingEngine
            engine = HvobTradingEngine(api, account, dry_run=options['dry_run'])
            engine.run()
        except Exception as e:
            self.stderr.write(f"[HVOB] 运行失败: {e}")
            raise
        finally:
            safe_close_api(api)
