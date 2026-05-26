"""
Check ATR and unit_lots for rb2610 on TURTLE account
"""
import os, sys, time
sys.path.insert(0, '.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'application.settings'

import django
django.setup()

from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.models import TradingAccount
from stock.core.atr import calculate_atr
from stock.core.position_sizing import calculate_unit_lots

acct = TradingAccount.objects.get(name='510988')
api = create_tqapi(acct)

symbol = 'SHFE.rb2610'
quote = api.get_quote(symbol)
for i in range(10):
    api.wait_update(deadline=time.time() + 1)
    if api.is_changing(quote, 'last_price'):
        break

atr = calculate_atr(api, symbol)
unit_lots = calculate_unit_lots(api, symbol, atr=atr)

print(f'rb2610 last_price={quote.last_price} volume_multiple={quote.volume_multiple}')
print(f'ATR(20) = {atr}')
if atr:
    raw = 4000 / (atr * 2 * 10)
    print(f'Formula: 4000 / ({atr} * 2 * 10) = {raw}')
    print(f'round({raw}) = {round(raw)}')
    print(f'unit_lots = {unit_lots}')
    print(f'If ATR were 33.33: raw={4000/(33.33*20):.2f} unit={round(4000/(33.33*20))}')
    print(f'If ATR were 28.57: raw={4000/(28.57*20):.2f} unit={round(4000/(28.57*20))}')

safe_close_api(api)
