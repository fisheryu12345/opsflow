# 临时脚本：测试日历热力图API
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
django.setup()

from stock.models import DailyEquitySnapshot, TradingAccount

print('=== 测试日历热力图数据 ===')
account = TradingAccount.objects.get(id=1)
snapshots = DailyEquitySnapshot.objects.filter(
    account=account
).order_by('trade_date').values(
    'trade_date',
    'daily_return'
)[:10]  # 只取前10条用于测试

print(f'账户: {account.name}')
print(f'总快照数: {DailyEquitySnapshot.objects.filter(account=account).count()}')
print(f'\n前10条日收益率数据:')
for s in snapshots:
    print(f"  {s['trade_date']}: {s['daily_return']}%")
