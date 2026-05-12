"""
回填 KlineData 的 Phase 2/3 指标字段（ATR、Donchian、MA、趋势因子、K线形态等）。

说明：
  - 利用已存在的 OHLCV 数据计算指标，不需要 TqSDK 连接
  - Phase 1 字段（settlement、limits 等）需要 TqSDK quote 数据，不做回填
  - Phase 2/3 字段全部由 OHLCV 派生，可以完整回填

用法：
    python manage.py backfill_kline_enrichment                       # 回填所有合约
    python manage.py backfill_kline_enrichment --product rb,MA       # 指定品种
    python manage.py backfill_kline_enrichment --dry-run             # 只预览不写入
    python manage.py backfill_kline_enrichment --batch-size 1000     # 批量大小
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
import pandas as pd
import numpy as np
import math
import traceback
from stock.models import KlineData
from stock.core.indicators import compute_batch_kline_indicators


class Command(BaseCommand):
    help = '回填 KlineData 的 Phase 2/3 指标字段'

    INDICATOR_FIELDS = [
        'atr_20', 'donchian_upper_20', 'donchian_lower_20',
        'ma_10', 'ma_20', 'ma_40', 'trend_factor', 'trend_label', 'true_range',
        'body_ratio', 'upper_shadow_ratio', 'lower_shadow_ratio', 'close_in_range',
        'volume_ratio_20', 'gap_from_pre_close', 'hit_upper_limit', 'hit_lower_limit',
    ]

    def add_arguments(self, parser):
        parser.add_argument('--product', type=str, default='',
                            help='指定品种代码，逗号分隔，如: rb,MA')
        parser.add_argument('--dry-run', action='store_true',
                            help='只预览不回写')
        parser.add_argument('--batch-size', type=int, default=500,
                            help='批量更新大小（默认 500）')

    def handle(self, *args, **options):
        product = options.get('product', '')
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 500)

        # 查询需要回填的合约列表
        qs = KlineData.objects.all()
        if product:
            product_codes = [p.strip() for p in product.split(',') if p.strip()]
            qs = qs.filter(product_code__in=product_codes)
            self.stdout.write(f"指定品种: {', '.join(product_codes)}")

        symbols = qs.values_list('symbol', flat=True).distinct().order_by('symbol')
        total_symbols = symbols.count()
        self.stdout.write(f"共 {total_symbols} 个合约需要回填")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 模式：不会写入数据库"))

        total_updated = 0
        total_errors = 0

        for idx, symbol in enumerate(symbols, 1):
            try:
                updated = self._backfill_symbol(symbol, batch_size, dry_run)
                total_updated += updated
                status = f"[DRY] 将更新 {updated}" if dry_run else f"更新 {updated}"
                self.stdout.write(f"  [{idx}/{total_symbols}] {symbol}: {status} 条")
            except Exception as e:
                total_errors += 1
                self.stdout.write(self.style.ERROR(
                    f"  [{idx}/{total_symbols}] {symbol}: 失败 - {e}"
                ))
                traceback.print_exc()
                continue

        self.stdout.write(self.style.SUCCESS(
            f"\n完成! 共处理 {total_symbols} 个合约, "
            f"更新 {total_updated} 条K线, "
            f"失败 {total_errors} 个"
        ))

    def _backfill_symbol(self, symbol: str, batch_size: int, dry_run: bool) -> int:
        """回填单个合约的指标"""
        records = KlineData.objects.filter(symbol=symbol).order_by('date').values(
            'id', 'date', 'open', 'high', 'low', 'close', 'volume',
            'open_interest', 'upper_limit', 'lower_limit'
        )

        if len(records) < 20:
            return 0  # 数据不足无法计算指标

        df = pd.DataFrame(records)

        # 数值列转 float
        for col in ['open', 'high', 'low', 'close', 'volume', 'upper_limit', 'lower_limit']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 计算指标
        df2 = compute_batch_kline_indicators(df)

        if dry_run:
            return len(df2)

        # 构建更新对象
        update_objs = []
        for _, row in df2.iterrows():
            rid = row.get('id')
            if pd.isna(rid):
                continue
            obj = KlineData(id=int(rid))
            has_value = False
            for field in self.INDICATOR_FIELDS:
                val = row.get(field)
                if val is not None and not (isinstance(val, float) and (pd.isna(val) or math.isinf(val))):
                    if field in ('hit_upper_limit', 'hit_lower_limit'):
                        setattr(obj, field, bool(val))
                    elif field == 'trend_label':
                        setattr(obj, field, str(val) if val else None)
                    else:
                        setattr(obj, field, Decimal(str(val)))
                    has_value = True
            if has_value:
                # 只更新有计算结果的字段
                update_objs.append(obj)

        if update_objs:
            KlineData.objects.bulk_update(
                update_objs,
                fields=self.INDICATOR_FIELDS,
                batch_size=batch_size
            )

        return len(update_objs)
