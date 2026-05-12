"""
Daily position reconciliation — compare DB PositionState vs TqSDK actual positions.
Detects discrepancies and sends email notification. No auto-repair.
Runs at 15:35 as a standalone scheduled task.
"""
import traceback
from decimal import Decimal
from django.utils import timezone
from django.template.loader import render_to_string
from stock.models import PositionState, FullContractList
from stock.utils.log_util import log_trade, log_error
from stock.tasks.send_mail import send_email_task
import time


def reconcile_positions(api, account):
    """
    Compare DB positions vs TqSDK actual positions for a single account.
    Returns a list of discrepancies found (does NOT auto-repair).
    """
    discrepancies = []
    db_positions = PositionState.objects.filter(account=account, units__gt=0)
    if not db_positions.exists():
        return discrepancies

    tq_proxies = {}
    for db_pos in db_positions:
        tq_proxies[db_pos.symbol] = api.get_position(db_pos.symbol)
    api.wait_update(deadline=time.time() + 5)

    for db_pos in db_positions:
        try:
            tq_pos = tq_proxies[db_pos.symbol]
            tq_net_pos = _safe_int(tq_pos.pos)
            has_position = (tq_net_pos != 0)

            if not has_position:
                discrepancies.append({
                    'type': 'DB_HAS_TQ_HAS_NOT',
                    'symbol': db_pos.symbol,
                    'detail': (f"DB有持仓({db_pos.contract_total_position}手, "
                              f"方向={'多' if db_pos.direction==1 else '空'}), 但交易所无此持仓"),
                    'db_volume': db_pos.contract_total_position,
                    'db_direction': '多' if db_pos.direction == 1 else '空',
                })
                continue

            tq_direction = 1 if tq_net_pos > 0 else -1
            if tq_direction != db_pos.direction:
                discrepancies.append({
                    'type': 'DIRECTION_MISMATCH',
                    'symbol': db_pos.symbol,
                    'detail': (f"方向不一致: DB={'多' if db_pos.direction==1 else '空'}, "
                              f"交易所={'多' if tq_direction==1 else '空'}"),
                    'db_volume': db_pos.contract_total_position,
                    'tq_volume': abs(tq_net_pos),
                })

            tq_volume = abs(tq_net_pos)
            if tq_volume != db_pos.contract_total_position:
                discrepancies.append({
                    'type': 'VOLUME_MISMATCH',
                    'symbol': db_pos.symbol,
                    'detail': (f"手数不一致: DB={db_pos.contract_total_position}手, "
                              f"交易所={tq_volume}手"),
                    'db_volume': db_pos.contract_total_position,
                    'tq_volume': tq_volume,
                })

        except Exception as e:
            discrepancies.append({
                'type': 'CHECK_ERROR',
                'symbol': db_pos.symbol,
                'detail': f"校验异常: {e}",
            })
            log_error('reconcile_positions',
                      f"{db_pos.symbol} 校验异常: {e}\n{traceback.format_exc()}", account=account)

    unknown = _check_unknown_positions(api, account, db_positions)
    discrepancies.extend(unknown)
    return discrepancies


def reconcile_all_accounts():
    """
    Run reconciliation for all active accounts. Called by 15:35 scheduler task.
    """
    from stock.models import TradingAccount
    from stock.infrastructure.tqapi import create_tqapi, safe_close_api

    accounts = TradingAccount.objects.filter(is_active=True)
    if not accounts.exists():
        print("[INFO] 无活跃账户，跳过持仓校验")
        return

    all_discrepancies = []
    for account in accounts:
        api = None
        try:
            api = create_tqapi(account)
            api.wait_update(deadline=time.time() + 10)
            discrepancies = reconcile_positions(api, account)
            for d in discrepancies:
                d['account'] = account.name
            all_discrepancies.extend(discrepancies)

            for d in discrepancies:
                msg = f"[RECONCILE] [{account.name}] {d['detail']}"
                print(msg)
                log_trade('reconcile_positions', msg, symbol=d['symbol'],
                         log_level='WARNING', account=account)
        except Exception as e:
            log_error('reconcile_positions',
                      f"账户 {account.name} 校验失败: {e}\n{traceback.format_exc()}", account=account)
        finally:
            safe_close_api(api)

    if all_discrepancies:
        _send_reconciliation_email(all_discrepancies)
        print(f"[INFO] 持仓差异邮件已发送，共 {len(all_discrepancies)} 项差异")
    else:
        print("[INFO] 持仓校验完成，无差异")


# ── helpers ──────────────────────────────────────────────────────────────


def _safe_int(value):
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _check_unknown_positions(api, account, db_positions):
    """Find positions that exist in TqSDK but not in DB."""
    from stock.models import AccountContractConfig

    db_symbols = set(db_positions.values_list('symbol', flat=True))
    configs = AccountContractConfig.objects.filter(account=account, is_active=True)
    if not configs.exists():
        return []

    check_symbols = []
    for cfg in configs:
        contract = FullContractList.objects.filter(
            product_code=cfg.product_code
        ).exclude(symbol__isnull=True).first()
        if contract and contract.symbol not in db_symbols:
            check_symbols.append(contract.symbol)

    if not check_symbols:
        return []

    tq_proxies = {}
    for sym in check_symbols:
        tq_proxies[sym] = api.get_position(sym)
    api.wait_update(deadline=time.time() + 5)

    found = []
    for sym in check_symbols:
        try:
            tq_pos = tq_proxies[sym]
            tq_net_pos = _safe_int(tq_pos.pos)
            if tq_net_pos == 0:
                continue
            direction = 1 if tq_net_pos > 0 else -1
            volume = abs(tq_net_pos)
            found.append({
                'type': 'TQ_HAS_DB_HAS_NOT',
                'symbol': sym,
                'detail': f"交易所持有({volume}手, 方向={'多' if direction==1 else '空'}), 但DB无记录",
                'tq_volume': volume,
            })
        except Exception:
            continue
    return found


def _send_reconciliation_email(discrepancies):
    """Send email notification about all discrepancies found."""
    account_groups = {}
    for d in discrepancies:
        acc = d.get('account', '未知')
        account_groups.setdefault(acc, []).append(d)

    html = render_to_string('reconciliation_report.html', {
        'total_count': len(discrepancies),
        'check_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'account_groups': sorted(account_groups.items()),
    })

    receiver = '312711936@qq.com'
    send_email_task(
        subject=f"[持仓校验] 发现 {len(discrepancies)} 项差异",
        body=html,
        receiver_email=receiver,
        is_html=True,
    )
