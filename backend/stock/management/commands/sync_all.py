"""
全量同步：合约列表 + K 线数据一步完成。

用法:
    python manage.py sync_all                           # 从 TqSDK 同步合约 + K 线
    python manage.py sync_all --seed                     # 种子数据初始化 + K 线
    python manage.py sync_all --product rb,MA            # 只同步指定品种
    python manage.py sync_all --skip-kline               # 只同步合约，跳过 K 线
    python manage.py sync_all --skip-contract            # 只同步 K 线，跳过合约
"""
from django.core.management.base import BaseCommand, CommandError
from stock.infrastructure.contract_sync import sync_contract_list_from_tqsdk, sync_kline_data_from_tqsdk
from stock.infrastructure.tqapi import create_tqapi, safe_close_api


class Command(BaseCommand):
    help = '全量同步：合约列表 + K 线数据'

    def add_arguments(self, parser):
        parser.add_argument('--seed', action='store_true', help='使用内置种子数据初始化合约（无 TqSDK 时使用）')
        parser.add_argument('--product', type=str, default='', help='指定品种代码，逗号分隔，如: rb,MA')
        parser.add_argument('--skip-kline', action='store_true', help='跳过 K 线同步')
        parser.add_argument('--skip-contract', action='store_true', help='跳过合约同步')

    def handle(self, *args, **options):
        product = options.get('product', '')
        product_codes = [p.strip() for p in product.split(',') if p.strip()] if product else None

        skip_kline = options.get('skip_kline', False)
        skip_contract = options.get('skip_contract', False)

        if options['seed'] and not skip_contract:
            self._seed_contracts()
        elif not skip_contract:
            self._sync_contracts()

        if not skip_kline:
            self._sync_kline(product_codes)

    def _sync_contracts(self):
        """从 TqSDK 同步合约列表"""
        self.stdout.write(self.style.SUCCESS('=== 第1步: 同步合约列表 ==='))
        api = None
        try:
            api = create_tqapi()
            result = sync_contract_list_from_tqsdk(api=api)
            if result.get('error'):
                raise CommandError(f"合约同步失败: {result['error']}")
            self.stdout.write(self.style.SUCCESS(
                f"合约同步完成: 新增 {result.get('synced', 0)}, "
                f"更新 {result.get('updated', 0)}"
            ))
        except ImportError:
            raise CommandError("TqSDK 未安装，请使用 --seed 参数用内置数据初始化")
        finally:
            safe_close_api(api)

    def _seed_contracts(self):
        """用内置种子数据初始化"""
        self.stdout.write(self.style.SUCCESS('=== 第1步: 初始化种子合约 ==='))
        from stock.management.commands.sync_contracts import Command as SeedCommand
        seed_cmd = SeedCommand()
        seed_cmd._seed_data()

    def _sync_kline(self, product_codes=None):
        """同步 K 线数据"""
        self.stdout.write(self.style.SUCCESS('=== 第2步: 同步 K 线数据 ==='))
        api = None
        try:
            api = create_tqapi()
            result = sync_kline_data_from_tqsdk(api=api, product_codes=product_codes)
            self.stdout.write(self.style.SUCCESS(
                f"K 线同步完成: 成功 {result['success']} 个合约, "
                f"失败 {result['failed']} 个, "
                f"新增 {result['bars']} 根 K 线"
            ))
        except ImportError:
            raise CommandError("TqSDK 未安装，无法同步 K 线数据")
        finally:
            safe_close_api(api)
