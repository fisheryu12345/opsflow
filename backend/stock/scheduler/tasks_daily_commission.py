"""
Daily commission query — APScheduler entry point.
Queries each active account's cumulative daily commission from TqSDK at 14:58
and updates TradingAccount.total_commission for direct access in equity calculations.
"""
import time
from decimal import Decimal
from datetime import date
from django.db import close_old_connections
from django.db.models import Sum
from django_redis import get_redis_connection
from stock.infrastructure.trade_day import skip_if_not_trade_day
from stock.utils.log_util import log_trade, log_error
from stock.utils.redis_lock import redis_lock, LockAcquisitionError
from stock.infrastructure.tqapi import create_tqapi, safe_close_api
from stock.models import TradingAccount, DailyEquitySnapshot


def update_trading_account_total_commission(account: TradingAccount) -> None:
    """从 DailyEquitySnapshot 聚合累计手续费并更新 TradingAccount.total_commission"""
    total = DailyEquitySnapshot.objects.filter(
        account=account
    ).aggregate(total=Sum('commission'))['total'] or Decimal('0')
    if account.total_commission != total:
        account.total_commission = total
        account.save(update_fields=['total_commission', 'updated_at'])


def job_daily_commission_query():
    """
    每日 14:58 查询所有激活账户的当日累计手续费并更新 TradingAccount。
    遍历每个活跃账户创建对应模式的 TqApi 连接，获取 get_account() 中的 commission 字段，
    创建/更新当日权益快照中的手续费数据，并汇总更新 TradingAccount.total_commission。
    """
    redis = get_redis_connection('default')
    try:
        with redis_lock(redis, 'lock:daily_commission'):
            close_old_connections()
            # log_trade('job_daily_commission_query', "开始查询当日手续费", symbol='N/A', log_level='INFO')

            accounts = TradingAccount.objects.filter(is_active=True)
            if not accounts.exists():
                print("[WARN] 未找到活跃账户，跳过手续费查询任务")
                return

            # 用第一个账户检查是否为交易日
            first_api = create_tqapi(accounts.first())
            try:
                if skip_if_not_trade_day(api=first_api):
                    return
            finally:
                safe_close_api(first_api)

            today = date.today()

            for account in accounts:
                api = None
                try:
                    api = create_tqapi(account)
                    api_account = api.get_account()

                    # 【修复】等待数据到达，最多 10 秒
                    deadline = time.time() + 10
                    api.wait_update(deadline=deadline)

                    today_commission = Decimal(str(getattr(api_account, 'commission', 0))).quantize(Decimal('0.01'))

                    # 从 TqSDK 读取完整账户数据
                    raw_data = {
                        'commission': today_commission,
                        'balance': Decimal(str(getattr(api_account, 'balance', 0))).quantize(Decimal('0.01')),
                        'available': Decimal(str(getattr(api_account, 'available', 0))).quantize(Decimal('0.01')),
                        'float_profit': Decimal(str(getattr(api_account, 'float_profit', 0))).quantize(Decimal('0.01')),
                        'margin': Decimal(str(getattr(api_account, 'margin', 0))).quantize(Decimal('0.01')),
                        'risk_ratio': Decimal(str(getattr(api_account, 'risk_ratio', 0))).quantize(Decimal('0.0001')),
                        'closed_pnl': Decimal(str(getattr(api_account, 'close_profit', 0))).quantize(Decimal('0.01')),
                    }

                    # 【修复】0 值保护：如果 TqSDK 返回 0 但 DB 已有正值，保留 DB 值
                    existing = DailyEquitySnapshot.objects.filter(
                        account=account, trade_date=today
                    ).first()
                    defaults = {}
                    for field, tq_value in raw_data.items():
                        if tq_value == 0 and existing and getattr(existing, field, 0) > 0:
                            defaults[field] = getattr(existing, field)
                        else:
                            defaults[field] = tq_value

                    # 补充非 TqSDK 直接映射的字段
                    defaults['daily_pnl'] = Decimal('0')
                    defaults['daily_return'] = Decimal('0')

                    # 更新或创建今日权益快照
                    snapshot, created = DailyEquitySnapshot.objects.update_or_create(
                        account=account,
                        trade_date=today,
                        defaults=defaults,
                    )

                    update_trading_account_total_commission(account)
                    print(f"[INFO] ✅ {account.name} 当日手续费: {today_commission}, "
                          f"累计: {account.total_commission}")

                except Exception as e:
                    log_error('job_daily_commission_query',
                              f"账户 {account.name} 手续费查询失败: {str(e)}")
                    import traceback
                    traceback.print_exc()
                finally:
                    safe_close_api(api)

    except LockAcquisitionError:
        print("[INFO] 手续费查询任务正在执行中，跳过本次调度")
    except Exception as e:
        log_error('job_daily_commission_query', f"手续费查询任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
