"""
同步期货合约列表到数据库。

用法:
    python manage.py sync_contracts                  # 从 TqSDK 同步（需 TqSDK 环境）
    python manage.py sync_contracts --seed            # 用内置种子数据初始化（无 TqSDK 时使用）
    python manage.py sync_contracts --repair-accounts # 为缺失交易账户的用户补建账户
"""
from django.core.management.base import BaseCommand, CommandError
from stock.infrastructure.contract_sync import sync_contract_list_from_tqsdk
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from django.conf import settings
from decimal import Decimal

SEED_PRODUCTS = [
    # 上期所 SHFE
    {"exchange": "SHFE", "product_code": "au", "name": "黄金", "volume_multiple": 1000, "price_tick": 0.02, "night_trading": True},
    {"exchange": "SHFE", "product_code": "ag", "name": "白银", "volume_multiple": 15, "price_tick": 1, "night_trading": True},
    {"exchange": "SHFE", "product_code": "cu", "name": "铜", "volume_multiple": 5, "price_tick": 10, "night_trading": True},
    {"exchange": "SHFE", "product_code": "al", "name": "铝", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "SHFE", "product_code": "zn", "name": "锌", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "SHFE", "product_code": "pb", "name": "铅", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "SHFE", "product_code": "ni", "name": "镍", "volume_multiple": 1, "price_tick": 10, "night_trading": True},
    {"exchange": "SHFE", "product_code": "sn", "name": "锡", "volume_multiple": 1, "price_tick": 10, "night_trading": True},
    {"exchange": "SHFE", "product_code": "rb", "name": "螺纹钢", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "SHFE", "product_code": "hc", "name": "热轧卷板", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "SHFE", "product_code": "ru", "name": "天然橡胶", "volume_multiple": 10, "price_tick": 5, "night_trading": True},
    {"exchange": "SHFE", "product_code": "bu", "name": "沥青", "volume_multiple": 10, "price_tick": 2, "night_trading": True},
    {"exchange": "SHFE", "product_code": "fu", "name": "燃料油", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "SHFE", "product_code": "sp", "name": "纸浆", "volume_multiple": 10, "price_tick": 2, "night_trading": True},
    {"exchange": "SHFE", "product_code": "ss", "name": "不锈钢", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    # 大商所 DCE
    {"exchange": "DCE", "product_code": "c", "name": "玉米", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "cs", "name": "玉米淀粉", "volume_multiple": 10, "price_tick": 1, "night_trading": False},
    {"exchange": "DCE", "product_code": "a", "name": "豆一", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "b", "name": "豆二", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "m", "name": "豆粕", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "y", "name": "豆油", "volume_multiple": 10, "price_tick": 2, "night_trading": True},
    {"exchange": "DCE", "product_code": "p", "name": "棕榈油", "volume_multiple": 10, "price_tick": 2, "night_trading": True},
    {"exchange": "DCE", "product_code": "l", "name": "聚乙烯", "volume_multiple": 5, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "pp", "name": "聚丙烯", "volume_multiple": 5, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "v", "name": "聚氯乙烯", "volume_multiple": 5, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "eg", "name": "乙二醇", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "DCE", "product_code": "jd", "name": "鸡蛋", "volume_multiple": 5, "price_tick": 1, "night_trading": False},
    {"exchange": "DCE", "product_code": "lh", "name": "生猪", "volume_multiple": 16, "price_tick": 1, "night_trading": False},
    {"exchange": "DCE", "product_code": "jm", "name": "焦煤", "volume_multiple": 60, "price_tick": 0.5, "night_trading": True},
    {"exchange": "DCE", "product_code": "j", "name": "焦炭", "volume_multiple": 100, "price_tick": 0.5, "night_trading": True},
    {"exchange": "DCE", "product_code": "i", "name": "铁矿石", "volume_multiple": 100, "price_tick": 0.5, "night_trading": True},
    {"exchange": "DCE", "product_code": "rr", "name": "粳米", "volume_multiple": 10, "price_tick": 1, "night_trading": False},
    # 郑商所 CZCE
    {"exchange": "CZCE", "product_code": "SR", "name": "白糖", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "CF", "name": "棉花", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "CZCE", "product_code": "TA", "name": "PTA", "volume_multiple": 5, "price_tick": 2, "night_trading": True},
    {"exchange": "CZCE", "product_code": "MA", "name": "甲醇", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "FG", "name": "玻璃", "volume_multiple": 20, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "RM", "name": "菜粕", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "OI", "name": "菜油", "volume_multiple": 10, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "SA", "name": "纯碱", "volume_multiple": 20, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "UR", "name": "尿素", "volume_multiple": 20, "price_tick": 1, "night_trading": True},
    {"exchange": "CZCE", "product_code": "SF", "name": "硅铁", "volume_multiple": 5, "price_tick": 2, "night_trading": True},
    {"exchange": "CZCE", "product_code": "SM", "name": "锰硅", "volume_multiple": 5, "price_tick": 2, "night_trading": True},
    {"exchange": "CZCE", "product_code": "AP", "name": "苹果", "volume_multiple": 10, "price_tick": 1, "night_trading": False},
    {"exchange": "CZCE", "product_code": "CY", "name": "棉纱", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "CZCE", "product_code": "PK", "name": "花生", "volume_multiple": 5, "price_tick": 2, "night_trading": False},
    {"exchange": "CZCE", "product_code": "ZC", "name": "动力煤", "volume_multiple": 100, "price_tick": 0.2, "night_trading": True},
    # 中金所 CFFEX
    # {"exchange": "CFFEX", "product_code": "IF", "name": "沪深300", "volume_multiple": 300, "price_tick": 0.2, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "IH", "name": "上证50", "volume_multiple": 300, "price_tick": 0.2, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "IC", "name": "中证500", "volume_multiple": 200, "price_tick": 0.2, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "IM", "name": "中证1000", "volume_multiple": 200, "price_tick": 0.2, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "T", "name": "10年期国债", "volume_multiple": 10000, "price_tick": 0.005, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "TF", "name": "5年期国债", "volume_multiple": 10000, "price_tick": 0.005, "night_trading": False},
    # {"exchange": "CFFEX", "product_code": "TS", "name": "2年期国债", "volume_multiple": 20000, "price_tick": 0.005, "night_trading": False},
    # 广期所 GFEX
    {"exchange": "GFEX", "product_code": "si", "name": "工业硅", "volume_multiple": 5, "price_tick": 5, "night_trading": True},
    {"exchange": "GFEX", "product_code": "lc", "name": "碳酸锂", "volume_multiple": 1, "price_tick": 50, "night_trading": True},
]


class Command(BaseCommand):
    help = '同步或初始化期货合约列表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--seed',
            action='store_true',
            help='使用内置种子数据初始化（无 TqSDK 环境时使用）',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新所有合约信息',
        )
        parser.add_argument(
            '--repair-accounts',
            action='store_true',
            help='为缺失交易账户的用户补建账户',
        )
        parser.add_argument(
            '--activate-user',
            type=int,
            help='为指定用户ID激活默认品种（原 PRODUCT_CODES 的22个合约）',
        )

    def handle(self, *args, **options):
        if options['repair_accounts']:
            self._repair_accounts()
        elif options['activate_user']:
            self._activate_products_for_user(options['activate_user'])
        elif options['seed']:
            self._seed_data()
        else:
            self._sync_from_tqsdk()

    def _sync_from_tqsdk(self):
        """从 TqSDK 同步"""
        self.stdout.write(self.style.SUCCESS('开始从 TqSDK 同步合约列表...'))
        api = None
        try:
            api = create_tqapi()
            result = sync_contract_list_from_tqsdk(api=api)
            if result.get('error'):
                raise CommandError(f"同步失败: {result['error']}")
            self.stdout.write(self.style.SUCCESS(f"\n同步完成！新增: {result.get('synced', 0)}, 更新: {result.get('updated', 0)}"))
        except ImportError:
            raise CommandError("TqSDK 未安装，请使用 --seed 参数用内置数据初始化，或在 TqSDK 环境中运行")
        finally:
            safe_close_api(api)

    def _repair_accounts(self):
        """为所有缺失 TradingAccount 的用户补建交易账户"""
        try:
            from dvadmin.system.models import Users
        except ImportError:
            Users = settings.AUTH_USER_MODEL
        from stock.models import TradingAccount

        UserModel = Users
        repaired = 0
        for user in UserModel.objects.all():
            _, created = TradingAccount.objects.get_or_create(
                user=user,
                defaults={
                    'name': f"{user.name}的交易账户",
                    'initial_balance': Decimal('1000000.00'),
                    'current_equity': Decimal('1000000.00'),
                    'is_active': True,
                }
            )
            if created:
                repaired += 1
                self.stdout.write(f"  为用户 {user.username} (id={user.id}) 创建了交易账户")
        self.stdout.write(self.style.SUCCESS(f'账户修复完成！共修复 {repaired} 个用户'))

    def _activate_products_for_user(self, user_id):
        """为指定用户激活默认品种列表（原 PRODUCT_CODES 的 22 个合约）"""
        from stock.models import TradingAccount, AccountContractConfig
        from django.db import transaction
        # 原 PRODUCT_CODES 默认品种
        default_products = [
            'rb', 'hc', 'al', 'ao', 'MA', 'TA', 'SA', 'FG',
            'fu', 'ru', 'UR', 'm', 'p', 'CF', 'RM', 'AP',
            'lh', 'jd', 'sp', 'si', 'lc', 'SR',
        ]
        try:
            from dvadmin.system.models import Users
            user = Users.objects.get(id=user_id)
        except Exception:
            self.stdout.write(self.style.ERROR(f'用户 id={user_id} 不存在'))
            return
        accounts = TradingAccount.objects.filter(user=user)
        if not accounts.exists():
            self.stdout.write(self.style.ERROR(f'用户 {user.username} 没有关联的交易账户'))
            return
        count = 0
        with transaction.atomic():
            for acct in accounts:
                for code in default_products:
                    _, created = AccountContractConfig.objects.get_or_create(
                        account=acct,
                        product_code=code,
                        defaults={'is_active': True}
                    )
                    if created:
                        count += 1
        self.stdout.write(self.style.SUCCESS(f'为用户 {user.username} (id={user_id}) 激活了 {count} 个品种配置'))

    def _seed_data(self):
        """用内置种子数据初始化 FullContractList"""
        from stock.models import FullContractList
        from django.db import transaction

        self.stdout.write(self.style.SUCCESS(f'开始写入 {len(SEED_PRODUCTS)} 个内置合约...'))
        count = 0
        with transaction.atomic():
            for p in SEED_PRODUCTS:
                _, created = FullContractList.objects.update_or_create(
                    exchange=p['exchange'],
                    product_code=p['product_code'],
                    defaults={
                        'symbol': f"{p['product_code']}888",
                        'name': p['name'],
                        'volume_multiple': p['volume_multiple'],
                        'price_tick': p['price_tick'],
                        'night_trading': p['night_trading'],
                    }
                )
                if created:
                    count += 1
        self.stdout.write(self.style.SUCCESS(f'种子数据写入完成！新增: {count}, 已存在: {len(SEED_PRODUCTS) - count}'))
