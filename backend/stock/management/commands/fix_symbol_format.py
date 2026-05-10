"""
修复数据库中 symbol 字段格式：为所有裸合约代码补上交易所前缀。

用法：
    python manage.py fix_symbol_format                      # 更新所有表
    python manage.py fix_symbol_format --dry-run             # 仅预览，不执行更新
    python manage.py fix_symbol_format --table kline         # 仅更新指定表

问题背景：
    原先 FullContractList.symbol 存储的是裸合约代码（如 rb2510），
    但 TqSDK 的 API（TargetPosTask、get_kline_serial、get_quote 等）
    需要使用完整格式 SHFE.rb2510 才能保证正确解析。
    见知识库 MEDIUM-11。
"""
from django.core.management.base import BaseCommand
from django.db import connection
from stock.models import FullContractList, PositionState, DailyStrategySignal, KlineData, ClosedPositionRecord


class Command(BaseCommand):
    help = "修复 symbol 字段格式：补上交易所前缀（rb2510 → SHFE.rb2510）"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='仅预览，不执行更新')
        parser.add_argument('--table', type=str, choices=['fullcontract', 'position', 'signal', 'kline', 'closed'],
                            help='仅更新指定表')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        table = options.get('table', None)

        tables_to_check = []

        if table == 'fullcontract' or table is None:
            tables_to_check.append(('FullContractList', self._fix_fullcontractlist))
        if table == 'position' or table is None:
            tables_to_check.append(('PositionState', self._fix_positionstate))
        if table == 'signal' or table is None:
            tables_to_check.append(('DailyStrategySignal', self._fix_dailystrategysignal))
        if table == 'kline' or table is None:
            tables_to_check.append(('KlineData', self._fix_klinedata))
        if table == 'closed' or table is None:
            tables_to_check.append(('ClosedPositionRecord', self._fix_closedpositionrecord))

        total_updated = 0
        for name, fix_func in tables_to_check:
            count = fix_func(dry_run)
            total_updated += count
            if dry_run:
                self.stdout.write(f"  [{name}] 待更新: {count} 条")
            else:
                self.stdout.write(self.style.SUCCESS(f"  [{name}] 已更新: {count} 条"))

        if dry_run:
            self.stdout.write(f"\n总览: {total_updated} 条记录需要更新（dry-run，未实际修改）")
        else:
            self.stdout.write(self.style.SUCCESS(f"\n完成: 共更新 {total_updated} 条记录"))

    def _needs_fix(self, qs, symbol_field='symbol'):
        """筛选出需要修复的记录：symbol 值不含 '.'（裸合约代码）"""
        from django.db.models import Q
        return qs.filter(~Q(**{f'{symbol_field}__contains': '.'})).exclude(**{f'{symbol_field}__isnull': True}).exclude(**{f'{symbol_field}__exact': ''})

    def _fix_fullcontractlist(self, dry_run):
        """FullContractList: 用 exchange.symbol 拼接"""
        needs_fix = self._needs_fix(FullContractList.objects.all())
        count = needs_fix.count()
        if count == 0 or dry_run:
            return count

        from django.db.models import F, Value, Func
        from django.db.models.functions import Concat
        for obj in needs_fix.iterator():
            obj.symbol = f"{obj.exchange}.{obj.symbol}"
            obj.save(update_fields=['symbol'])

        return count

    def _fix_positionstate(self, dry_run):
        """PositionState: 通过 FullContractList 映射补前缀"""
        needs_fix = self._needs_fix(PositionState.objects.all())
        count = needs_fix.count()
        if count == 0 or dry_run:
            return count

        fcl_map = dict(FullContractList.objects.filter(
            product_code__in=needs_fix.values_list('product_code', flat=True).distinct()
        ).values_list('product_code', 'exchange'))

        updated = 0
        for obj in needs_fix.iterator():
            exchange = fcl_map.get(obj.product_code)
            if exchange:
                obj.symbol = f"{exchange}.{obj.symbol}"
                obj.save(update_fields=['symbol'])
                updated += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f"  [SKIP] PositionState id={obj.id}: 未找到品种 {obj.product_code} 的交易所信息"
                ))

        return updated

    def _fix_dailystrategysignal(self, dry_run):
        """DailyStrategySignal: 通过 FullContractList 映射补前缀"""
        needs_fix = self._needs_fix(DailyStrategySignal.objects.all())
        count = needs_fix.count()
        if count == 0 or dry_run:
            return count

        fcl_map = dict(FullContractList.objects.filter(
            product_code__in=needs_fix.values_list('product_code', flat=True).distinct()
        ).values_list('product_code', 'exchange'))

        updated = 0
        for obj in needs_fix.iterator():
            exchange = fcl_map.get(obj.product_code)
            if exchange and obj.symbol:
                obj.symbol = f"{exchange}.{obj.symbol}"
                obj.save(update_fields=['symbol'])
                updated += 1

        return updated

    def _fix_klinedata(self, dry_run):
        """KlineData: 通过 exchange 字段直接拼接"""
        needs_fix = self._needs_fix(KlineData.objects.all())
        count = needs_fix.count()
        if count == 0 or dry_run:
            return count

        # 批量更新（KlineData 通常数据量大，逐条 save 太慢）
        from django.db.models import F, Value
        from django.db.models.functions import Concat
        updated = needs_fix.update(
            symbol=Concat(F('exchange'), Value('.'), F('symbol'))
        )
        return updated

    def _fix_closedpositionrecord(self, dry_run):
        """ClosedPositionRecord: 通过 FullContractList 映射补前缀"""
        needs_fix = self._needs_fix(ClosedPositionRecord.objects.all())
        count = needs_fix.count()
        if count == 0 or dry_run:
            return count

        fcl_map = dict(FullContractList.objects.filter(
            product_code__in=needs_fix.values_list('product_code', flat=True).distinct()
        ).values_list('product_code', 'exchange'))

        updated = 0
        for obj in needs_fix.iterator():
            exchange = fcl_map.get(obj.product_code)
            if exchange and obj.symbol:
                obj.symbol = f"{exchange}.{obj.symbol}"
                obj.save(update_fields=['symbol'])
                updated += 1

        return updated
