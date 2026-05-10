"""
同步期货合约日K线数据到 KlineData 表。

用法:
    python manage.py sync_kline                       # 同步所有合约（默认全量）
    python manage.py sync_kline --product rb,MA        # 指定品种
"""
from django.core.management.base import BaseCommand
from stock.infrastructure.contract_sync import sync_kline_data_from_tqsdk
from stock.infrastructure.tqapi import create_tqapi, safe_close_api


class Command(BaseCommand):
    help = '同步期货合约日K线数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product', type=str, default='',
            help='指定品种代码，逗号分隔，如: rb,MA'
        )

    def handle(self, *args, **options):
        product = options.get('product', '')

        product_codes = None
        if product:
            product_codes = [p.strip() for p in product.split(',') if p.strip()]
            self.stdout.write(f"同步指定品种: {', '.join(product_codes)}")
        else:
            self.stdout.write("同步所有合约（全量）")

        api = create_tqapi()
        try:
            result = sync_kline_data_from_tqsdk(api=api, product_codes=product_codes)
            self.stdout.write(self.style.SUCCESS(
                f"K线同步完成: 成功 {result['success']} 个合约, "
                f"失败 {result['failed']} 个, "
                f"新增 {result['bars']} 根K线"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"K线同步失败: {e}"))
            raise
        finally:
            safe_close_api(api)
