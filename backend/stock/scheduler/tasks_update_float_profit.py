"""
每小时定时任务：更新持仓浮动盈亏。

遍历所有活跃账户，通过 TqSDK 获取每个持仓合约的实时浮动盈亏，
写入 PositionState.float_profit 字段，供前端持仓明细直接展示。
"""
import time
import logging
from decimal import Decimal

from django.db import transaction, close_old_connections

from stock.models import PositionState, TradingAccount
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.infrastructure.trade_day import skip_if_not_trade_day

logger = logging.getLogger(__name__)


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
            logger.error("[%s] 无法创建 TqApi 连接", account.name)
            return

        # 获取 TqSDK 持仓对象引用（wait_update 前订阅）
        tq_positions = {}
        for pos in positions:
            try:
                tq_positions[pos.symbol] = api.get_position(pos.symbol)
            except Exception as e:
                logger.warning("[%s] %s get_position 失败: %s", account.name, pos.symbol, e)

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
                    PositionState.objects.filter(pk=pos_db.pk).update(float_profit=fp)
                    updated_count += 1
                except (TypeError, ValueError, AttributeError) as e:
                    logger.warning("[%s] %s 读取 float_profit 异常: %s",
                                   account.name, pos_db.symbol, e)

        logger.info("[%s] 更新完成 %d 笔持仓", account.name, updated_count)

    except Exception as e:
        logger.error("[%s] 更新浮动盈亏异常: %s", account.name, e, exc_info=True)
    finally:
        safe_close_api(api)


def job_update_float_profit():
    """
    APScheduler 入口：遍历所有活跃账户，更新持仓浮动盈亏。
    每小时执行一次，可通过 register_scheduler_jobs 注册。
    """
    close_old_connections()
    logger.info("[定时任务] 开始更新持仓浮动盈亏")

    if skip_if_not_trade_day():
        logger.info("[定时任务] 今日非交易日，跳过持仓浮动盈亏更新")
        return

    accounts = TradingAccount.objects.filter(is_active=True)
    for account in accounts:
        _update_account_float_profit(account)

    logger.info("[定时任务] 持仓浮动盈亏更新完成")
