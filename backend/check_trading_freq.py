# 临时脚本：检查交易频率计算
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from stock.models import ClosedPositionRecord, AccountPerformanceSummary
from django.utils import timezone

print('=== 详细分析 ===')
records = ClosedPositionRecord.objects.all().order_by('executed_at')
first_trade = records.first()
last_trade = records.last()
summary = AccountPerformanceSummary.objects.first()

if first_trade and summary:
    print(f'第一笔交易时间: {first_trade.executed_at}')
    print(f'最后一笔交易时间: {last_trade.executed_at}')
    print(f'快照日期: {summary.snapshot_date}')
    trading_days = (summary.snapshot_date - first_trade.executed_at.date()).days
    print(f'交易天数: {trading_days}天')
    print(f'总交易数: {summary.total_trades_all_time}')
    print(f'当前交易频率: {summary.trading_frequency}')
    if trading_days > 0:
        calculated_freq = summary.total_trades_all_time / trading_days
        print(f'计算的交易频率: {calculated_freq:.4f}')
    else:
        print('交易天数为0，无法计算')
    
    # 检查持仓天数
    print('\n=== 持仓天数详情 ===')
    for r in records:
        print(f'  {r.symbol}: holding_days={r.holding_days}, executed_at={r.executed_at.date()}')
else:
    print('没有数据')
