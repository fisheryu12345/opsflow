# coding: utf-8
"""Apply type annotations to key functions in tasks_daily_close.py"""

with open('backend/stock/scheduler/tasks_daily_close.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line numbers are 0-indexed
# Line 21: def check_breakout_signal(symbol, product_code, trend_factor, trend_label,
# Line 22:                                           breakout_info, account,trade_type):
# Lines 23-36: docstring
# Line 87: def check_exit_signals():
# Line 160: def check_rollover_signals():
# Line 217: def check_add_position_signals():
# Line 344: def update_all_positions_high_low_price():
# Line 388: def update_all_positions_stop_loss_price(api):
# Line 546: def job_daily_close_calculation():

# 1. Replace check_breakout_signal signature
old_lines = lines[21:37]
new_sig = [
    '\tdef check_breakout_signal(\n',
    '\t\tsymbol: str,\n',
    '\t\tproduct_code: str,\n',
    '\t\ttrend_factor: float,\n',
    '\t\ttrend_label: str,\n',
    '\t\tbreakout_info: dict,\n',
    '\t\taccount,\n',
    '\t\ttrade_type: str,\n',
    '\t) -> bool:\n',
    '\t"""\n',
    '\t保存每日策略信号并更新持仓状态（检查是否需要开仓）。\n',
    '\t"""\n',
]
lines[21:37] = new_sig

# 2. check_exit_signals
for i, line in enumerate(lines):
    if 'def check_exit_signals():' in line:
        lines[i] = '\tdef check_exit_signals() -> None:\n'
        # Add/update docstring
        doc_end = i + 1
        while doc_end < len(lines) and '"""' not in lines[doc_end]:
            doc_end += 1
        if doc_end < len(lines):
            lines[i+1:i+doc_end+1] = [
                '\t"""\n',
                '\t检查是否需要平仓（基于止损价判断）。\n',
                '\t"""\n',
            ]
        break

# 3. check_rollover_signals
for i, line in enumerate(lines):
    if 'def check_rollover_signals():' in line:
        lines[i] = '\tdef check_rollover_signals() -> None:\n'
        doc_end = i + 1
        while doc_end < len(lines) and '"""' not in lines[doc_end]:
            doc_end += 1
        if doc_end < len(lines):
            lines[i+1:i+doc_end+1] = [
                '\t"""\n',
                '\t检查主力合约切换，生成移仓信号。\n',
                '\t"""\n',
            ]
        break

# 4. check_add_position_signals
for i, line in enumerate(lines):
    if 'def check_add_position_signals():' in line:
        lines[i] = '\tdef check_add_position_signals() -> None:\n'
        doc_end = i + 1
        while doc_end < len(lines) and '"""' not in lines[doc_end]:
            doc_end += 1
        if doc_end < len(lines):
            lines[i+1:i+doc_end+1] = [
                '\t"""\n',
                '\t检查海龟金字塔加仓条件，生成加仓信号。\n',
                '\t"""\n',
            ]
        break

# 5. update_all_positions_high_low_price
for i, line in enumerate(lines):
    if 'def update_all_positions_high_low_price():' in line:
        lines[i] = '\tdef update_all_positions_high_low_price() -> None:\n'
        break

# 6. update_all_positions_stop_loss_price
for i, line in enumerate(lines):
    if 'def update_all_positions_stop_loss_price(api):' in line:
        lines[i] = '\tdef update_all_positions_stop_loss_price(api) -> None:\n'
        break

# 7. job_daily_close_calculation
for i, line in enumerate(lines):
    if 'def job_daily_close_calculation():' in line:
        lines[i] = '\tdef job_daily_close_calculation() -> None:\n'
        break

with open('backend/stock/scheduler/tasks_daily_close.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('tasks_daily_close.py OK')

with open('backend/stock/scheduler/tasks_daily_open.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'def job_daily_open_process():' in line:
        lines[i] = 'def job_daily_open_process() -> None:\n'
        break

with open('backend/stock/scheduler/tasks_daily_open.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('tasks_daily_open.py OK')
