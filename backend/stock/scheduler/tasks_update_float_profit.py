"""
定时任务：更新持仓浮动盈亏。

遍历所有活跃账户，通过 TqSDK 获取每个持仓合约的实时浮动盈亏 → PositionState.float_profit。

供前端持仓明细实时展示。手续费累加统一由收盘任务处理。
"""
import time
from decimal import Decimal

from django.db import transaction, close_old_connections
from django.utils import timezone

from stock.utils.log_util import log_trade, log_error
from stock.models import PositionState, TradingAccount
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.trade_day import skip_if_not_trade_day

FSM = 'job_update_float_profit'


def _update_account_float_profit(account: TradingAccount):
    """更新单个账户下所有持仓的浮动盈亏。"""
    positions = PositionState.objects.filter(
        account=account,
        direction__in=[1, -1],
    )
    if not positions.exists():
        return

    api = None
    try:
        api = create_tqapi(account)
        if api is None:
            log_error(FSM, f"无法创建 TqApi 连接: {account.name}", account=account)
            return

        # 获取 TqSDK 持仓对象引用（wait_update 前订阅）
        tq_positions = {}
        for pos in positions:
            try:
                tq_positions[pos.symbol] = api.get_position(pos.symbol)
            except Exception as e:
                log_trade(FSM, f"{pos.symbol} get_position 失败: {e}", symbol=pos.symbol, log_level='WARNING', account=account)

        if not tq_positions:
            return

        # 等待数据更新，最多 30 秒
        deadline = time.time() + 30
        while time.time() < deadline:
            api.wait_update(deadline=deadline)

        # 批量写入 DB
        updated_count = 0
        with transaction.atomic():
            for pos_db in positions:
                tq_pos = tq_positions.get(pos_db.symbol)
                if tq_pos is None:
                    continue
                try:
                    fp = Decimal(str(tq_pos.float_profit)).quantize(Decimal('0.01'))

                    # 【修复】0 值保护：TqSDK 返回 0 但 DB 已有非零值 → 跳过本次更新
                    if fp == 0:
                        existing_fp = PositionState.objects.filter(pk=pos_db.pk).values_list('float_profit', flat=True).first()
                        if existing_fp and existing_fp != 0:
                            continue

                    # 同步成本价：多仓用 open_price_long，空仓用 open_price_short
                    cp_raw = tq_pos.open_price_long if pos_db.direction == 1 else tq_pos.open_price_short
                    cp = Decimal(str(cp_raw)).quantize(Decimal('0.01')) if cp_raw else None

                    PositionState.objects.filter(pk=pos_db.pk).update(
                        float_profit=fp,
                        cost_price=cp,
                        last_update_time=timezone.now(),
                    )
                    updated_count += 1
                except (TypeError, ValueError, AttributeError) as e:
                    log_trade(FSM, f"{pos_db.symbol} 读取 float_profit 异常: {e}", symbol=pos_db.symbol, log_level='WARNING', account=account)

        # log_trade(FSM, f"更新完成 {updated_count} 笔持仓", log_level='INFO', account=account)

    except Exception as e:
        log_error(FSM, f"更新浮动盈亏异常: {e}", account=account)
    finally:
        safe_close_api(api)


def job_update_float_profit():
    """
    APScheduler 入口：遍历所有活跃账户，更新持仓浮动盈亏。
    每小时执行一次，可通过 register_scheduler_jobs 注册。
    """
    close_old_connections()
    # log_trade(FSM, "开始更新持仓浮动盈亏", log_level='INFO')

    if skip_if_not_trade_day():
        # log_trade(FSM, "今日非交易日，跳过持仓浮动盈亏更新", log_level='INFO')
        return

    accounts = TradingAccount.objects.filter(is_active=True)
    for account in accounts:
        _update_account_float_profit(account)

    # log_trade(FSM, '持仓浮动盈亏更新完成', log_level='INFO')
