"""
HVOB-MBI 纯逻辑测试（无需 Django DB）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Minimal Django setup for imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
import django
django.setup()

from decimal import Decimal
from hvob_mbi.mbi import score_for_symbol, mbi_to_label, get_trading_permission
from hvob_mbi.trading_engine import Position

pass_count = 0
fail_count = 0

def test(name, fn):
    global pass_count, fail_count
    try:
        fn()
        pass_count += 1
        print(f'  OK {name}')
    except AssertionError as e:
        fail_count += 1
        print(f'  FAIL {name}: assertion failed')
    except Exception as e:
        fail_count += 1
        print(f'  FAIL {name}: {e}')


print('=== MBI Score Tests ===')
test('all bullish -> +3', lambda: (
    score_for_symbol('RB', 4000, 3950, 4020, 3980, 4050) == 3))
test('all bearish -> -3', lambda: (
    score_for_symbol('RB', 3900, 3950, 3920, 3880, 3850) == -3))
test('neutral -> 0', lambda: (
    score_for_symbol('RB', 3950, 3950, 3960, 3940, 3950) == 0))
test('mixed -> +1', lambda: (
    score_for_symbol('RB', 3960, 3950, 3970, 3940, 3930) == 1))
test('gap below threshold -> 0', lambda: (
    score_for_symbol('RB', 3951, 3950, 3960, 3940, 3955) == 0))
test('negative gap -> -1', lambda: (
    score_for_symbol('RB', 3947, 3950, 3960, 3940, 3955) == -1))

print()
print('=== MBI Label Tests ===')
test('0.80 -> extreme_bull', lambda: mbi_to_label(Decimal('0.80')) == '极强多头')
test('0.70 -> bull', lambda: mbi_to_label(Decimal('0.70')) == '多头')
test('0.55 -> neutral', lambda: mbi_to_label(Decimal('0.55')) == '中性')
test('0.40 -> bear', lambda: mbi_to_label(Decimal('0.40')) == '空头')
test('0.30 -> extreme_bear', lambda: mbi_to_label(Decimal('0.30')) == '极强空头')

test('0.751 -> extreme_bull', lambda: mbi_to_label(Decimal('0.751')) == '极强多头')
test('0.75 -> bull', lambda: mbi_to_label(Decimal('0.75')) == '多头')
test('0.651 -> bull', lambda: mbi_to_label(Decimal('0.651')) == '多头')
test('0.65 -> neutral', lambda: mbi_to_label(Decimal('0.65')) == '中性')
test('0.451 -> neutral', lambda: mbi_to_label(Decimal('0.451')) == '中性')
test('0.45 -> bear', lambda: mbi_to_label(Decimal('0.45')) == '空头')

print()
print('=== Trading Permission Tests ===')
test('extreme_bull long=1.0', lambda: get_trading_permission(Decimal('0.80'), 1) == 1.0)
test('extreme_bull short=0.0', lambda: get_trading_permission(Decimal('0.80'), -1) == 0.0)
test('extreme_bear long=0.0', lambda: get_trading_permission(Decimal('0.30'), 1) == 0.0)
test('extreme_bear short=1.0', lambda: get_trading_permission(Decimal('0.30'), -1) == 1.0)
test('bear long=0.5', lambda: get_trading_permission(Decimal('0.40'), 1) == 0.5)
test('bull short=0.5', lambda: get_trading_permission(Decimal('0.70'), -1) == 0.5)
test('neutral both=1.0', lambda: (
    get_trading_permission(Decimal('0.55'), 1) == 1.0 and
    get_trading_permission(Decimal('0.55'), -1) == 1.0))
test('0.751 long=1.0', lambda: get_trading_permission(Decimal('0.751'), 1) == 1.0)
test('0.75 long=1.0', lambda: get_trading_permission(Decimal('0.75'), 1) == 1.0)
test('0.751 short=0.0', lambda: get_trading_permission(Decimal('0.751'), -1) == 0.0)
test('0.75 short=0.5', lambda: get_trading_permission(Decimal('0.75'), -1) == 0.5)
test('0.35 long=0.0', lambda: get_trading_permission(Decimal('0.35'), 1) == 0.0)

print()
print('=== Position Init Tests ===')
pos_long = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
pos_short = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
test('long stop_loss=3972', lambda: pos_long.stop_loss == Decimal('3972'))
test('short stop_loss=4028', lambda: pos_short.stop_loss == Decimal('4028'))
test('long breakeven_trigger=4040', lambda: pos_long.breakeven_trigger == Decimal('4040'))
test('short breakeven_trigger=3960', lambda: pos_short.breakeven_trigger == Decimal('3960'))

print()
print('=== Position Trailing Tests ===')

# Trailing high update
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(4050)
test('long trailing_high=4050', lambda: p.trailing_high == Decimal('4050'))

# No trailing high update on drop
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(3950)
test('long trailing_high unchanged on drop', lambda: p.trailing_high == Decimal('4000'))

# Stop moves when profit >= 2*stop_distance
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)  # stop_dist=28, 2*28=56
p.update_trailing(4060)  # profit=60 >= 56
test('long stop moves to 4032', lambda: p.stop_loss == Decimal('4032'))

# Stop does not move when profit < 2*stop_distance
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(4050)  # profit=50 < 56
test('long stop stays 3972', lambda: p.stop_loss == Decimal('3972'))

# Monotonic: stop doesn't drop on retrace
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(4060)  # stop -> 4032
p.update_trailing(4030)  # retrace
test('long stop monotonic', lambda: p.stop_loss == Decimal('4032'))

# Short trailing
p = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
p.update_trailing(3940)  # profit=60 >= 56
test('short stop moves to 3968', lambda: p.stop_loss == Decimal('3968'))

# Breakeven long
p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(4040)
test('long breakeven activated + stop=4000', lambda: (
    p.breakeven_activated == True and p.stop_loss == Decimal('4000')))

p = Position('RB', 'RB', 1, 5, 4000, 4020, 3980, 40)
p.update_trailing(4039)
test('long breakeven NOT activated at 4039', lambda: (
    p.breakeven_activated == False and p.stop_loss == Decimal('3972')))

# Breakeven short
p = Position('RB', 'RB', -1, 5, 4000, 4020, 3980, 40)
p.update_trailing(3960)
test('short breakeven activated + stop=4000', lambda: (
    p.breakeven_activated == True and p.stop_loss == Decimal('4000')))

print()
print(f'=== Results: {pass_count} passed, {fail_count} failed ({pass_count+fail_count} total) ===')
sys.exit(0 if fail_count == 0 else 1)
