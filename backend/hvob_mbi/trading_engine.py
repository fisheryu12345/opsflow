"""
HVOB-MBI 交易引擎：TqSDK wait_update 事件循环，时间相位驱动。

相位流程：
  screening(启动) → night_or(21:00-21:30) → night_breakout(21:30-9:00)
  → gap_check(9:00-9:30) → day_breakout(9:30-14:55)
  → force_close → done
"""
import time
import math
import json
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict
from stock.utils.log_util import log_trade, log_error
from tqsdk import TargetPosTask
from django.db import close_old_connections

from stock.models import FullContractList, TradingAccount
from stock.infrastructure.order_execution import (
    wait_for_target_position,
    check_min_position_requirement,
    execute_two_step_opening,
)
from .config import (
    NIGHT_OPEN, NIGHT_OR_CLOSE, DAY_OPEN, DAY_OR_CLOSE, FORCE_CLOSE_TIME,
    BREAKOUT_OFFSET_RATIO, STOP_OFFSET_RATIO, DEFAULT_RISK_PERCENT,
    TIME_DECAY_SLOTS,
)
from .mbi import get_trading_permission
from .signal_recorder import (
    record_entry_signal, record_exit_signal, record_stop_loss_signal,
    record_daily_equity,
)


class Position:
    """HVOB 日内持仓记录"""
    def __init__(self, symbol, product_code, direction, volume, entry_price,
                 or_h, or_l, or_r, weight=1.0):
        self.symbol = symbol
        self.product_code = product_code
        self.direction = direction  # 1=多, -1=空
        self.volume = volume
        self.entry_price = Decimal(str(entry_price))
        self.or_h = Decimal(str(or_h))
        self.or_l = Decimal(str(or_l))
        self.or_r = Decimal(str(or_r))
        self.weight = weight
        # 止损价（永久锚定，永不重算）
        self.stop_loss = self._calc_stop_loss()
        # 保本触发价
        self.breakeven_trigger = self.entry_price + self.or_r if direction == 1 else self.entry_price - self.or_r
        self.breakeven_activated = False
        # 移动止盈
        self.trailing_high = self.entry_price  # 多: 跟踪最高
        self.trailing_low = self.entry_price   # 空: 跟踪最低

    def _calc_stop_loss(self):
        if self.direction == 1:
            return self.or_l - Decimal(str(STOP_OFFSET_RATIO)) * self.or_r
        else:
            return self.or_h + Decimal(str(STOP_OFFSET_RATIO)) * self.or_r

    def update_trailing(self, current_price):
        price = Decimal(str(current_price))
        if self.direction == 1:
            if price > self.trailing_high:
                self.trailing_high = price
                # 移动止盈：浮盈超过 2 倍止损距离，止损上移
                stop_distance = self.entry_price - self.stop_loss
                if price - self.entry_price >= stop_distance * Decimal('2'):
                    self.stop_loss = max(self.stop_loss, price - stop_distance)
            # 保本检查
            if not self.breakeven_activated and price >= self.breakeven_trigger:
                self.breakeven_activated = True
                self.stop_loss = max(self.stop_loss, self.entry_price)
        else:
            if price < self.trailing_low:
                self.trailing_low = price
                stop_distance = self.stop_loss - self.entry_price
                if self.entry_price - price >= stop_distance * Decimal('2'):
                    self.stop_loss = min(self.stop_loss, price + stop_distance)
            if not self.breakeven_activated and price <= self.breakeven_trigger:
                self.breakeven_activated = True
                self.stop_loss = min(self.stop_loss, self.entry_price)


class HvobTradingEngine:
    """
    日内交易引擎，TqSDK 事件循环驱动。
    """

    def __init__(self, api, account, config=None, dry_run=False):
        self.api = api
        self.account = account
        self.config = config
        self.dry_run = dry_run
        self.trade_date = date.today()

        # 状态
        self.phase = 'screening'
        self.watchlist = []           # [{symbol, product_code, score, ...}]
        self.positions = {}           # {symbol: Position}
        self.opening_ranges = {}      # {symbol: {H, L, R, closed}}
        self.banned = set()           # 跳空穿越拉黑
        self.traded = set()           # 已交易品种
        self.mbi_value = Decimal('0.5')
        self.mbi_label = ''
        self.daily_pnl = Decimal('0')
        self.total_trades = 0
        self._night_trading_map = None  # {product_code: bool} 懒加载
        self._last_restart_key = None  # 定时重启防重复标记

    # ==================== 夜盘分类查询 ====================

    def _is_night_product(self, product_code):
        """查询品种是否有夜盘（从 FullContractList.night_trading 缓存读取）"""
        if self._night_trading_map is None:
            close_old_connections()
            qs = FullContractList.objects.values('product_code', 'night_trading')
            self._night_trading_map = {r['product_code']: r['night_trading'] for r in qs}
        return self._night_trading_map.get(product_code.upper(), True)

    # ==================== 主循环 ====================

    def run(self):
        """主事件循环"""
        print(f"[HVOB] 引擎启动 | 账户: {self.account.name} | 日期: {self.trade_date}")

        # 交易日检查
        from stock.infrastructure.trade_day import is_trade_day
        if not is_trade_day(self.trade_date, self.api):
            print(f"[HVOB] {self.trade_date} 非交易日，引擎退出")
            self.phase = 'done'
            return

        # 根据当前时间确定初始相位
        self._init_phase()

        # Phase 1: 盘前筛选（不改变相位）
        self._do_screening()

        # 订阅 watchlist 数据（仅注册引用，未实际发送）
        self._subscribe_all()

        # 先 pump 一次以实际发送订阅请求到服务器
        self.api.wait_update()

        # 等待行情数据就绪（循环检测，最多等 30 秒）
        print("[HVOB] 等待行情数据就绪...")
        wait_start = time.time()
        data_ready = False
        while time.time() - wait_start < 30:
            self.api.wait_update(deadline=time.time() + 5)
            # 检查是否有任意 watchlist 品种收到行情
            for item in self.watchlist:
                quote = self.api.get_quote(item['symbol'])
                if quote and quote.last_price and quote.last_price > 0:
                    data_ready = True
                    break
            if data_ready:
                elapsed = time.time() - wait_start
                print(f"[HVOB] 行情数据就绪 ({elapsed:.1f}s)")
                break
            print(f"[HVOB] 等待行情中... ({int(time.time()-wait_start)}s)")

        if not data_ready:
            print(f"[HVOB] ⚠️ 等待行情超时 (30s)，部分品种可能无数据，继续运行")

        # night_breakout 阶段启动：从 DB 恢复夜盘 OR（应对夜盘中重启）
        if self.phase == 'night_breakout':
            self._restore_night_breakout_state()

        # day_breakout 阶段启动：从 DB 恢复 OR/MBI/banned/traded
        if self.phase == 'day_breakout':
            if not self._restore_day_breakout_state():
                print(f"[HVOB] ❌ 无已保存 OR 数据，day_breakout 阶段无法交易，跳过今日")
                self.phase = 'done'
                return

        # 进入事件循环
        last_phase_log = ''
        last_heartbeat = 0.0
        while self.phase != 'done':
            if not self.api.wait_update(deadline=time.time() + 30):
                # 30 秒无任何行情更新 → 保底 pump
                continue
            now = datetime.now()

            # 定时重启连接（8:55 / 13:25 / 20:55）
            self._check_restart(now)

            self._check_phase(now, last_phase_log)

            # 每 5 分钟心跳，确认引擎存活
            elapsed = time.time() - last_heartbeat
            if elapsed >= 300:
                last_heartbeat = time.time()
                now_str = now.strftime('%H:%M:%S')
                print(f"[HVOB] 心跳 | phase={self.phase} | {now_str} | {'持仓中' if self.positions else '等待突破信号'}")

        # 收盘后记录
        self._finalize()

    def _init_phase(self):
        """根据当前时间确定启动相位"""
        t = datetime.now().time()
        if t >= NIGHT_OR_CLOSE:          # 21:30+
            self.phase = 'night_breakout'
        elif t >= NIGHT_OPEN:             # 21:00-21:30
            self.phase = 'night_or'       # 保持，正常跟踪夜盘 OR
        elif t >= FORCE_CLOSE_TIME:       # 14:55-21:00（收盘后→等待夜盘）
            self.phase = 'idle'
        elif t >= DAY_OR_CLOSE:           # 9:30-14:55
            self.phase = 'day_breakout'
        elif t >= DAY_OPEN:               # 9:00-9:30
            self.phase = 'gap_check'
        else:                              # 0:00-9:00
            self.phase = 'night_breakout'
        print(f"[HVOB] 初始化相位: {self.phase}")

    def _check_phase(self, now, last_phase_log):
        """时间相位切换"""
        t = now.time()

        if self.phase == 'night_or':
            if t >= NIGHT_OR_CLOSE:
                self._close_night_opening_range()
                self.phase = 'night_breakout'
                print(f"[HVOB] → night_breakout")
            else:
                self._on_quote('night_or')

        elif self.phase == 'idle':
            if t >= NIGHT_OPEN:
                self.phase = 'night_or'
                print(f"[HVOB] → night_or")
            # idle 阶段不处理行情，仅等待时间到达

        elif self.phase == 'night_breakout':
            # 9:00-9:30 切换到 gap_check；其他时间仍属夜盘
            if DAY_OPEN <= t < DAY_OR_CLOSE:
                self._check_gap()
                self.phase = 'gap_check'
                print(f"[HVOB] → gap_check")
            else:
                self._on_quote('night_breakout')

        elif self.phase == 'gap_check':
            if t >= DAY_OR_CLOSE:
                self._close_day_opening_range()
                self._calc_mbi()
                self._save_midday_state()
                self.phase = 'day_breakout'
                # 恢复持仓（night_breakout 阶段启动的重启后，仓位于此时恢复）
                if not self.positions:
                    self._restore_positions()
                print(f"[HVOB] → day_breakout (MBI={self.mbi_value:.4f})")
            else:
                self._on_quote('gap_check')

        elif self.phase == 'day_breakout':
            if t >= FORCE_CLOSE_TIME:
                self._force_close_all()
                self.phase = 'done'
                print(f"[HVOB] → done")
            else:
                self._on_quote('day_breakout')

    # ==================== 连接管理 ====================

    def _check_restart(self, now):
        """检查是否需要定时重启 TqSDK 连接（8:55 / 13:25 / 20:55）"""
        restart_hour_minutes = [(8, 55), (13, 25), (20, 55)]
        now_total = now.hour * 60 + now.minute
        in_window = any(
            h * 60 + m - 1 <= now_total <= h * 60 + m + 1
            for h, m in restart_hour_minutes
        )
        if not in_window:
            return

        restart_key = now.strftime('%Y-%m-%d-%H%M')
        if restart_key == self._last_restart_key:
            return
        self._last_restart_key = restart_key
        print(f"[HVOB] ⏰ 触法定时重启 ({now.strftime('%H:%M')}, phase={self.phase})")
        self._reconnect()

    def _reconnect(self):
        """关闭旧 TqSDK 连接并重新建立，保留全部内存状态"""
        from stock.infrastructure.tqapi import create_tqapi, safe_close_api
        safe_close_api(self.api)
        print("[HVOB] 等待 35s 后重建连接...")
        time.sleep(35)
        self.api = create_tqapi(self.account)
        self.api.wait_update(deadline=time.time() + 15)
        # 重新订阅行情（新 api 实例需重新 get_quote/get_kline_serial）
        self._subscribe_all()
        self.api.wait_update(deadline=time.time() + 10)
        print(f"[HVOB] ✅ 连接已重建，继续运行 (phase={self.phase})")

    # ==================== 盘前筛选 ====================

    def _do_screening(self):
        """执行盘前筛选"""
        print("[HVOB] Phase: screening")
        close_old_connections()

        if not self.config:
            from .models import HvobMbiConfig
            try:
                self.config = HvobMbiConfig.objects.get(account=self.account, is_active=True)
            except HvobMbiConfig.DoesNotExist:
                print("[HVOB] 未找到策略配置，使用默认参数")
                self.config = None

        from .screening import select_watchlist
        self.watchlist = select_watchlist(self.api)
        self._save_watchlist_items()
        print(f"[HVOB] → {self.phase}")

    # ==================== 订阅 ====================

    def _subscribe_all(self):
        """订阅所有 watchlist 品种的 Quote + 60min Kline"""
        for item in self.watchlist:
            try:
                self.api.get_quote(item['symbol'])
                self.api.get_kline_serial(item['symbol'], 300, 50)
            except Exception as e:
                print(f"[HVOB] 订阅 {item['symbol']} 失败: {e}")

    # ==================== 行情回调 ====================

    def _on_quote(self, current_phase):
        """处理每个品种的行情更新"""
        for item in self.watchlist:
            symbol, product_code = item['symbol'], item['product_code']
            # 夜盘阶段跳过无夜盘品种
            if current_phase in ('night_or', 'night_breakout') and not self._is_night_product(product_code):
                continue

            quote = self.api.get_quote(symbol)
            if quote is None or quote.last_price is None or quote.last_price == 0 or math.isnan(quote.last_price):
                continue

            price = float(quote.last_price)

            # 开盘区间跟踪（仅在收集阶段）
            # 夜盘OR改用K线计算，见 _close_night_opening_range()
            if current_phase == 'gap_check':
                self._track_opening_range(symbol, price, is_night=False)

            # 检查已有持仓的止损/止盈（所有阶段）
            if symbol in self.positions:
                self._check_exit(symbol, price)

            # 突破检查（仅在突破阶段）
            if current_phase in ('night_breakout', 'day_breakout'):
                self._check_entry(symbol, product_code, price, current_phase)

    # ==================== 开盘区间跟踪 ====================

    def _track_opening_range(self, symbol, price, is_night):
        """跟踪开盘区间 H/L/R"""
        if symbol not in self.opening_ranges:
            self.opening_ranges[symbol] = {
                'H': price, 'L': price, 'R': None, 'closed': False, 'night': is_night
            }
        else:
            or_ = self.opening_ranges[symbol]
            if or_['closed']:
                return
            if is_night == or_.get('night', is_night):  # 同一阶段才更新
                or_['H'] = max(or_['H'], price)
                or_['L'] = min(or_['L'], price)

    def _close_night_opening_range(self):
        """使用1分钟K线计算夜盘开盘区间 H/L/R（崩溃安全，数据来源TqSDK服务器）"""
        print("[HVOB] 夜盘开盘区间关闭（基于1分钟K线）")
        count = 0
        for item in self.watchlist:
            if not self._is_night_product(item['product_code']):
                continue
            symbol = item['symbol']
            try:
                klines = self.api.get_kline_serial(symbol, 60, 30)
                for _ in range(10):
                    self.api.wait_update(deadline=time.time() + 1)
                    if len(klines) >= 30:
                        break

                if len(klines) < 30:
                    print(f"  ⚠️ {symbol} K线数据不足({len(klines)}根)，跳过")
                    continue

                h = float(max(klines.iloc[-i]['high'] for i in range(1, 31)))
                l_val = float(min(klines.iloc[-i]['low'] for i in range(1, 31)))
                r = round(h - l_val, 4)

                self.opening_ranges[symbol] = {
                    'H': h, 'L': l_val, 'R': r,
                    'closed': True, 'night': True,
                }
                print(f"  {symbol}: H={h:.2f} L={l_val:.2f} R={r:.2f}")
                count += 1
            except Exception as e:
                print(f"  ⚠️ {symbol} K线获取失败: {e}")

        if count > 0:
            self._save_night_or_state()
        print(f"[HVOB] ✅ 夜盘OR已关闭，共{count}个品种")

    def _close_day_opening_range(self):
        """关闭日盘开盘区间：用1分钟K线计算完整OR（崩溃安全，gap_check阶段启动也可正确计算）"""
        print("[HVOB] 日盘开盘区间关闭（基于1分钟K线）")
        count = 0
        for item in self.watchlist:
            symbol = item['symbol']
            try:
                klines = self.api.get_kline_serial(symbol, 60, 30)
                for _ in range(10):
                    self.api.wait_update(deadline=time.time() + 1)
                    if len(klines) >= 30:
                        break

                if len(klines) >= 30:
                    h = float(max(klines.iloc[-i]['high'] for i in range(1, 31)))
                    l_val = float(min(klines.iloc[-i]['low'] for i in range(1, 31)))
                    self.opening_ranges[symbol] = {
                        'H': h, 'L': l_val, 'R': round(h - l_val, 4),
                        'closed': True, 'night': False,
                    }
                    print(f"  {symbol}: H={h:.2f} L={l_val:.2f} R={h-l_val:.2f}")
                    count += 1
                else:
                    # K线不足，tick跟踪数据兜底
                    or_ = self.opening_ranges.get(symbol)
                    if or_ and not or_.get('night') and not or_['closed']:
                        or_['R'] = round(or_['H'] - or_['L'], 4)
                        or_['closed'] = True
                        print(f"  {symbol}: H={or_['H']:.2f} L={or_['L']:.2f} R={or_['R']:.2f} (tick兜底)")
                        count += 1
            except Exception as e:
                print(f"  ⚠️ {symbol} 日盘OR计算失败: {e}")

        # 清理未被覆盖的残余条目
        for sym, or_ in list(self.opening_ranges.items()):
            if not or_.get('night') and not or_['closed']:
                or_['R'] = round(or_['H'] - or_['L'], 4)
                or_['closed'] = True
                print(f"  {sym}: H={or_['H']:.2f} L={or_['L']:.2f} R={or_['R']:.2f} (残余)")
                count += 1

        if count > 0:
            print(f"[HVOB] ✅ 日盘OR已关闭，共{count}个品种")

    # ==================== 跳空检查 ====================

    def _check_gap(self):
        """夜盘品种跳空检查：开盘价在夜盘区间外 → 拉黑"""
        print("[HVOB] 跳空检查")
        for item in self.watchlist:
            if not self._is_night_product(item['product_code']):
                continue
            symbol = item['symbol']
            quote = self.api.get_quote(symbol)
            if quote is None or quote.last_price is None or math.isnan(quote.last_price):
                continue
            or_ = self.opening_ranges.get(symbol)
            if or_ is None or or_['R'] is None:
                continue
            # 用现价（9:00集合竞价后的第一口价）判断是否跳空穿越夜盘区间
            current_price = float(quote.last_price)
            if current_price <= 0:
                continue
            if current_price < or_['L'] or current_price > or_['H']:
                self.banned.add(symbol)
                print(f"  ⛔ {symbol} 跳空穿越: 区间[{or_['L']:.2f},{or_['H']:.2f}] 现价{current_price:.2f} → 拉黑")
            else:
                print(f"  ✓ {symbol} 正常: 现价{current_price:.2f} 在区间内")

        # 跳空检查完成，清理夜盘 OR 数据，让出日盘 OR 跟踪
        for sym in list(self.opening_ranges.keys()):
            if self.opening_ranges[sym].get('night'):
                del self.opening_ranges[sym]

        # 用当前行情价为所有 watchlist 品种初始化日盘 OR 基线
        # 防止 gap_check 阶段启动时已过 DAY_OR_CLOSE 导致 MBI 永远为 0.5
        for item in self.watchlist:
            symbol = item['symbol']
            quote = self.api.get_quote(symbol)
            if quote and quote.last_price and quote.last_price > 0:
                price = float(quote.last_price)
                if symbol not in self.opening_ranges:
                    self.opening_ranges[symbol] = {
                        'H': price, 'L': price, 'R': None, 'closed': False, 'night': False
                    }

    # ==================== MBI ====================

    def _calc_mbi(self):
        """计算 MBI"""
        from .mbi import calculate_mbi
        self.mbi_value, self.mbi_label = calculate_mbi(self.api, self.watchlist, self.opening_ranges)

    # ==================== 日中状态持久化 ====================

    def _save_midday_state(self):
        """gap_check→day_breakout 转换时保存 OR/MBI/banned/traded 到 HvobMbiDailyState"""
        try:
            from .models import HvobMbiDailyState
            close_old_connections()

            or_data = {}
            for sym, or_ in self.opening_ranges.items():
                or_data[sym] = {
                    'H': round(or_['H'], 4) if or_['H'] else None,
                    'L': round(or_['L'], 4) if or_['L'] else None,
                    'R': round(or_['R'], 4) if or_['R'] else None,
                }

            HvobMbiDailyState.objects.update_or_create(
                account=self.account,
                trade_date=self.trade_date,
                defaults={
                    'watchlist': [
                        {'symbol': item['symbol'], 'product_code': item['product_code'],
                         'score': item['score'], 'atr_pct': item['atr_pct'],
                         'avg_amp': item['avg_amp'], 'vol_ratio': item['vol_ratio'],
                         'atr_score': item['atr_score'], 'amp_score': item['amp_score'],
                         'vol_score': item['vol_score'], 'bonus': item['bonus'],
                         'open_interest': item['open_interest']}
                        for item in self.watchlist
                    ],
                    'mbi_value': self.mbi_value,
                    'mbi_label': self.mbi_label,
                    'opening_ranges': or_data,
                    'banned_symbols': list(self.banned),
                    'traded_symbols': list(self.traded),
                    'total_trades': self.total_trades,
                    'daily_pnl': self.daily_pnl,
                    'is_complete': False,
                }
            )
            print(f"[HVOB] 日中状态已保存 (OR={len(or_data)}, MBI={self.mbi_value:.4f})")
        except Exception as e:
            print(f"[HVOB] 保存日中状态失败: {e}")

    def _save_night_or_state(self):
        """夜盘 OR 持久化（崩溃恢复用：定时保存 + OR 关闭时保存）"""
        try:
            from .models import HvobMbiDailyState
            close_old_connections()
            or_data = {}
            for sym, or_ in self.opening_ranges.items():
                if or_.get('night'):
                    or_data[sym] = {
                        'H': round(or_['H'], 4) if or_['H'] else None,
                        'L': round(or_['L'], 4) if or_['L'] else None,
                        'R': round(or_['R'], 4) if or_['R'] else None,
                        'closed': or_['closed'],
                    }
            if not or_data:
                return
            HvobMbiDailyState.objects.update_or_create(
                account=self.account,
                trade_date=self.trade_date,
                defaults={'night_opening_ranges': or_data},
            )
        except Exception as e:
            print(f"[HVOB] 保存夜盘 OR 失败: {e}")

    def _restore_night_breakout_state(self):
        """night_breakout 启动时从 DB 恢复夜盘 OR，无数据时直接 K 线计算"""
        # 先尝试从 DB 恢复
        try:
            from .models import HvobMbiDailyState
            close_old_connections()
            state = HvobMbiDailyState.objects.filter(
                account=self.account, trade_date=self.trade_date
            ).first()
            if state is not None and state.night_opening_ranges:
                restored = 0
                for sym, data in state.night_opening_ranges.items():
                    if data.get('R') is None:
                        continue
                    self.opening_ranges[sym] = {
                        'H': data['H'], 'L': data['L'], 'R': data['R'],
                        'closed': data.get('closed', True), 'night': True,
                    }
                    restored += 1
                if restored > 0:
                    print(f"[HVOB] ✅ 夜盘 OR 已恢复: {restored} 个品种")
                    return True
        except Exception as e:
            print(f"[HVOB] 恢复夜盘 OR 失败: {e}")

        # 无已保存数据，且当前时间已过 21:30 → 直接 K 线计算
        now = datetime.now().time()
        if now >= NIGHT_OR_CLOSE:
            print("[HVOB] 无已保存夜盘 OR，从 K 线直接计算")
            self._close_night_opening_range()
            return True

        return False

    def _restore_day_breakout_state(self):
        """day_breakout 启动时从 HvobMbiDailyState 恢复 OR/MBI/banned/traded"""
        try:
            from .models import HvobMbiDailyState
            close_old_connections()

            state = HvobMbiDailyState.objects.filter(
                account=self.account, trade_date=self.trade_date
            ).first()
            if state is None or not state.opening_ranges:
                return False

            # 恢复 opening_ranges
            restored = 0
            for sym, data in state.opening_ranges.items():
                if data.get('R') is None:
                    continue
                self.opening_ranges[sym] = {
                    'H': data['H'], 'L': data['L'], 'R': data['R'],
                    'closed': True, 'night': False,
                }
                restored += 1

            if restored == 0:
                return False

            # 恢复 MBI
            if state.mbi_value is not None:
                self.mbi_value = state.mbi_value
                self.mbi_label = state.mbi_label or ''

            # 恢复 banned
            self.banned = set(state.banned_symbols or [])

            # 恢复 traded（保存状态 + DB 信号双保险）
            self.traded = set(state.traded_symbols or [])
            self._supplement_traded_from_db()

            # 恢复计数器
            self.total_trades = state.total_trades or 0
            self.daily_pnl = state.daily_pnl or Decimal('0')

            # 恢复持仓（从 PositionState 重建 self.positions）
            self._restore_positions()

            print(f"[HVOB] ✅ day_breakout 状态恢复: OR={restored}, "
                  f"MBI={self.mbi_value:.4f}, banned={len(self.banned)}, "
                  f"traded={len(self.traded)}, positions={len(self.positions)}")
            return True
        except Exception as e:
            print(f"[HVOB] 恢复日中状态失败: {e}")
            return False

    def _supplement_traded_from_db(self):
        """从 DailyStrategySignal 补全 traded 集合（捕获保存后已成交的品种）"""
        try:
            from stock.models import DailyStrategySignal
            close_old_connections()
            for sym in DailyStrategySignal.objects.filter(
                account=self.account, trade_date=self.trade_date,
                trade_type='ENTRY',
            ).values_list('symbol', flat=True):
                self.traded.add(sym)
        except Exception as e:
            print(f"[HVOB] 从DB补全traded失败: {e}")

    def _restore_positions(self):
        """从 PositionState 重建 self.positions（崩溃恢复后使用）"""
        try:
            from stock.models import PositionState as PsModel
            close_old_connections()
            qs = PsModel.objects.filter(account=self.account)
            restored = 0
            for ps in qs:
                if ps.h20_price is None or ps.l20_price is None:
                    continue
                or_r = ps.h20_price - ps.l20_price
                if or_r <= 0:
                    continue
                self.positions[ps.symbol] = Position(
                    symbol=ps.symbol,
                    product_code=ps.product_code or '',
                    direction=ps.direction,
                    volume=ps.contract_total_position,
                    entry_price=float(ps.cost_price or 0),
                    or_h=float(ps.h20_price),
                    or_l=float(ps.l20_price),
                    or_r=float(or_r),
                    weight=1.0,
                )
                restored += 1
            if restored:
                print(f"[HVOB] ✅ 恢复持仓: {restored} 个品种")
        except Exception as e:
            print(f"[HVOB] 恢复持仓失败: {e}")

    # ==================== 入场检查 ====================

    def _check_entry(self, symbol, product_code, price, phase):
        """突破检查 + MBI 过滤 + 开仓"""
        if symbol in self.traded or symbol in self.banned:
            return

        or_ = self.opening_ranges.get(symbol)
        if or_ is None or or_['R'] is None or or_['R'] <= 0:
            return

        r = Decimal(str(or_['R']))
        h = Decimal(str(or_['H']))
        l_ = Decimal(str(or_['L']))
        p = Decimal(str(price))

        h_break = h + Decimal(str(BREAKOUT_OFFSET_RATIO)) * r
        l_break = l_ - Decimal(str(BREAKOUT_OFFSET_RATIO)) * r

        direction = None
        if p >= h_break:
            direction = 1
        elif p <= l_break:
            direction = -1
        else:
            return

        # MBI 过滤
        if phase == 'day_breakout':
            weight = get_trading_permission(self.mbi_value, direction)
            if weight <= 0:
                print(f"[HVOB] MBI 禁止 {symbol} {'多' if direction > 0 else '空'}")
                return
        else:
            # 夜盘突破不受 MBI 限制
            weight = 1.0

        # 时间衰减（仅日盘非跳空 A 类）
        if phase == 'day_breakout':
            now = datetime.now().time()
            for slot_start, slot_end, slot_weight in TIME_DECAY_SLOTS:
                if slot_start <= now < slot_end:
                    weight *= slot_weight
                    break

        # 计算手数（基础风险敞口）
        volume = self._calc_volume(symbol, direction, r)
        # MBI 权重 + 时间衰减系数
        volume = max(1, int(volume * weight))
        if volume <= 0:
            return

        # 开仓
        self._execute_entry(symbol, product_code, direction, volume, float(p), or_, weight)

    def _calc_volume(self, symbol, direction, or_r):
        """计算开仓手数：风险敞口法"""
        if self.config is None:
            risk_pct = DEFAULT_RISK_PERCENT
        else:
            risk_pct = float(self.config.risk_percent)

        close_old_connections()
        contract = FullContractList.objects.filter(symbol=symbol).first()
        if contract is None:
            print(f"[HVOB] 找不到合约信息: {symbol}")
            return 0

        volume_multiple = contract.volume_multiple or 1
        account_info = self.api.get_account()
        balance = float(getattr(account_info, 'balance', 0) or 0)
        if balance <= 0:
            balance = 100000  # fallback

        # risk = balance * risk_pct
        # stop_distance = 入场到止损的实际距离 = R + 0.3R + 0.2R = 1.5R
        risk_amount = balance * risk_pct
        stop_distance = float(or_r) * (1 + BREAKOUT_OFFSET_RATIO + STOP_OFFSET_RATIO)
        if stop_distance <= 0:
            return 1

        vol = max(1, int(risk_amount / (stop_distance * volume_multiple)))
        max_pos = self.config.max_positions_per_day if self.config else 5
        return min(vol, max_pos)

    def _execute_entry(self, symbol, product_code, direction, volume, price, or_, weight):
        """执行开仓"""
        if self.dry_run:
            print(f"[HVOB] ⚠️ DRY-RUN 开仓: {symbol} {'多' if direction > 0 else '空'} {volume}手@{price}")
            self.traded.add(symbol)
            self.total_trades += 1
            return

        # 两步开仓：满足交易所最小开仓手数限制
        min_check = check_min_position_requirement(symbol, volume)
        if min_check['need_adjustment']:
            print(f"[HVOB] {symbol} 最小开仓限制{min_check['min_position']}手，采用两步开仓")
            two_step = execute_two_step_opening(
                api=self.api, symbol=symbol, direction=direction,
                adjusted_volume=min_check['adjusted_volume'],
                excess_to_close=min_check['excess_to_close'],
                target_volume=volume, function_name='hvob_entry',
                account=self.account,
            )
            if not two_step['success']:
                print(f"[HVOB] ❌ 两步开仓失败 {symbol}")
                self.banned.add(symbol)
                return
            fill_price = two_step['avg_price'] or price
            pos = Position(symbol, product_code, direction, volume, fill_price,
                           or_['H'], or_['L'], or_['R'], weight)
            self.positions[symbol] = pos
            self.traded.add(symbol)
            self.total_trades += 1
            record_entry_signal(
                self.account, symbol, product_code, self.trade_date,
                direction, volume, fill_price,
                or_['H'], or_['L'], or_['R'],
                self.mbi_value, weight,
            )
            print(f"[HVOB] ✅ 两步开仓: {symbol} {'多' if direction > 0 else '空'} {volume}手@{fill_price}")
            return

        try:
            # TargetPosTask: 开仓并等待成交
            target_pos = TargetPosTask(self.api, symbol, support_open_min_volume=True)
            target = volume if direction == 1 else -volume
            target_pos.set_target_volume(target)
            wait_for_target_position(self.api, target_pos, symbol, target, 'hvob_entry')

            # 记录持仓
            pos = Position(symbol, product_code, direction, volume, price,
                           or_['H'], or_['L'], or_['R'], weight)
            self.positions[symbol] = pos
            self.traded.add(symbol)
            self.total_trades += 1

            # 写入信号
            record_entry_signal(
                self.account, symbol, product_code, self.trade_date,
                direction, volume, price,
                or_['H'], or_['L'], or_['R'],
                self.mbi_value, weight,
            )
            print(f"[HVOB] ✅ 开仓: {symbol} {'多' if direction > 0 else '空'} {volume}手@{price}")
        except Exception as e:
            print(f"[HVOB] ❌ 开仓失败 {symbol}: {e}")

    # ==================== 出场检查 ====================

    def _check_exit(self, symbol, price):
        """检查止损/止盈"""
        pos = self.positions.get(symbol)
        if pos is None:
            return

        p = Decimal(str(price))

        # 更新移动止盈
        pos.update_trailing(p)

        # 止损检查
        if (pos.direction == 1 and p <= pos.stop_loss) or \
           (pos.direction == -1 and p >= pos.stop_loss):
            self._execute_stop_loss(symbol, p)
            return

        # 固定盈亏比止盈 (1:1.5)
        if pos.direction == 1:
            tp_price = pos.entry_price + pos.or_r * Decimal('1.5')
            if p >= tp_price:
                self._execute_take_profit(symbol, p, '固定止盈')
                return
        else:
            tp_price = pos.entry_price - pos.or_r * Decimal('1.5')
            if p <= tp_price:
                self._execute_take_profit(symbol, p, '固定止盈')
                return

    def _execute_stop_loss(self, symbol, price):
        """止损平仓"""
        pos = self.positions[symbol]
        exit_pnl = self._calc_pnl(pos, float(price))

        if self.dry_run:
            print(f"[HVOB] ⚠️ DRY-RUN 止损: {symbol} {pos.volume}手@{price} PnL={exit_pnl}")
        else:
            target_pos = TargetPosTask(self.api, symbol, support_open_min_volume=True)
            target_pos.set_target_volume(0)
            wait_for_target_position(self.api, target_pos, symbol, 0, 'hvob_stop_loss')

            try:
                record_stop_loss_signal(
                    self.account, symbol, pos.product_code, self.trade_date,
                    pos.direction, float(price), exit_pnl, pos.entry_price, pos.volume,
                )
            except Exception as e:
                print(f"[HVOB] ⚠️ 止损信号写入失败 {symbol}: {e}")
                log_error('execute_stop_loss', f"止损信号写入失败: {str(e)}",account=self.account,notify=True)

        self.daily_pnl += exit_pnl
        del self.positions[symbol]
        print(f"[HVOB] 🛑 止损: {symbol} {pos.volume}手@{price} PnL={exit_pnl}")

    def _execute_take_profit(self, symbol, price, reason):
        """止盈平仓"""
        pos = self.positions[symbol]
        exit_pnl = self._calc_pnl(pos, float(price))

        if self.dry_run:
            print(f"[HVOB] ⚠️ DRY-RUN 止盈: {symbol} {pos.volume}手@{price} PnL={exit_pnl} ({reason})")
        else:
            target_pos = TargetPosTask(self.api, symbol, support_open_min_volume=True)
            target_pos.set_target_volume(0)
            wait_for_target_position(self.api, target_pos, symbol, 0, 'hvob_take_profit')

            try:
                record_exit_signal(
                    self.account, symbol, pos.product_code, self.trade_date,
                    pos.direction, float(price), reason, exit_pnl, pos.entry_price, pos.volume,
                )
            except Exception as e:
                print(f"[HVOB] ⚠️ 止盈信号写入失败 {symbol}: {e}")
                log_error('execute_take_profit', f"止盈信号写入失败: {str(e)}",account=self.account,notify=True)

        self.daily_pnl += exit_pnl
        del self.positions[symbol]
        print(f"[HVOB] ✅ 止盈: {symbol} {pos.volume}手@{price} PnL={exit_pnl} ({reason})")

    def _force_close_all(self):
        """14:55 强制平仓所有持仓"""
        if not self.positions:
            print("[HVOB] 无持仓，无需强制平仓")
            return

        print(f"[HVOB] ⏰ 强制平仓 {len(self.positions)} 个持仓")
        for symbol, pos in list(self.positions.items()):
            quote = self.api.get_quote(symbol)
            if quote is None or quote.last_price is None or math.isnan(quote.last_price):
                continue
            price = float(quote.last_price)

            exit_pnl = self._calc_pnl(pos, price)

            if not self.dry_run:
                target_pos = TargetPosTask(self.api, symbol, support_open_min_volume=True)
                target_pos.set_target_volume(0)
                wait_for_target_position(self.api, target_pos, symbol, 0, 'hvob_force_close')

                try:
                    record_exit_signal(
                        self.account, symbol, pos.product_code, self.trade_date,
                        pos.direction, price, '强制平仓', exit_pnl, pos.entry_price, pos.volume,
                    )
                except Exception as e:
                    print(f"[HVOB] ⚠️ 强制平仓信号写入失败 {symbol}: {e}")
                    log_error('execute_force_close', f"强制平仓信号写入失败: {str(e)}",account=self.account,notify=True)

            self.daily_pnl += exit_pnl
            del self.positions[symbol]
            print(f"  {symbol}: {pos.volume}手@{price} PnL={exit_pnl}")

    @staticmethod
    def _calc_pnl(pos, exit_price):
        """计算盈亏"""
        contract = FullContractList.objects.filter(symbol=pos.symbol).first()
        mult = contract.volume_multiple if contract else 1
        if pos.direction == 1:
            return Decimal(str((exit_price - float(pos.entry_price)) * pos.volume * mult))
        else:
            return Decimal(str((float(pos.entry_price) - exit_price) * pos.volume * mult))

    # ==================== 收盘 ====================

    def _finalize(self):
        """收盘记录"""
        print(f"[HVOB] 交易结束 | 总交易: {self.total_trades} | 日盈亏: {self.daily_pnl:.2f}")

        if not self.dry_run:
            try:
                self.api.wait_update(deadline=time.time() + 5)
                account_info = self.api.get_account()
                balance = float(getattr(account_info, 'balance', 0) or 0)
                available = float(getattr(account_info, 'available', 0) or 0)
                float_profit = float(getattr(account_info, 'float_profit', 0) or 0)
                margin = float(getattr(account_info, 'margin', 0) or 0)
                risk_ratio = float(getattr(account_info, 'risk_ratio', 0) or 0)
                record_daily_equity(self.account, self.trade_date, balance, self.daily_pnl,
                                    available=available, float_profit=float_profit,
                                    margin=margin, risk_ratio=risk_ratio)
            except Exception as e:
                print(f"[HVOB] 记录日权益失败: {e}")

        # 保存日状态
        self._save_daily_state()

    def _save_watchlist_items(self):
        """将观察池条目写入 HvobMbiWatchlistItem（筛选完成后立即保存）"""
        if not self.watchlist:
            return
        try:
            from .models import HvobMbiWatchlistItem
            items = []
            for i, item in enumerate(self.watchlist, start=1):
                items.append(HvobMbiWatchlistItem(
                    account=self.account,
                    trade_date=self.trade_date,
                    rank=i,
                    symbol=item['symbol'],
                    product_code=item['product_code'],
                    score=item.get('score', 0),
                    atr_pct=item.get('atr_pct', 0),
                    avg_amp=item.get('avg_amp', 0),
                    vol_ratio=item.get('vol_ratio', 0),
                    atr_score=item.get('atr_score', 0),
                    amp_score=item.get('amp_score', 0),
                    vol_score=item.get('vol_score', 0),
                    bonus=item.get('bonus', 0),
                    open_interest=item.get('open_interest', 0),
                ))
            HvobMbiWatchlistItem.objects.bulk_create(items, ignore_conflicts=True)
            print(f"[HVOB] 观察池已写入数据库: {len(items)} 个品种")
        except Exception as e:
            print(f"[HVOB] 保存观察池失败: {e}")

    def _save_daily_state(self):
        """保存每日状态到 HvobMbiDailyState"""
        try:
            from .models import HvobMbiDailyState
            or_data = {}
            for sym, or_ in self.opening_ranges.items():
                or_data[sym] = {
                    'H': round(or_['H'], 4) if or_['H'] else None,
                    'L': round(or_['L'], 4) if or_['L'] else None,
                    'R': round(or_['R'], 4) if or_['R'] else None,
                }

            HvobMbiDailyState.objects.update_or_create(
                account=self.account,
                trade_date=self.trade_date,
                defaults={
                    'watchlist': [{'symbol': item['symbol'], 'product_code': item['product_code'],
                                   'score': item['score'], 'atr_pct': item['atr_pct'],
                                   'avg_amp': item['avg_amp'], 'vol_ratio': item['vol_ratio'],
                                   'atr_score': item['atr_score'], 'amp_score': item['amp_score'],
                                   'vol_score': item['vol_score'], 'bonus': item['bonus'],
                                   'open_interest': item['open_interest']}
                                  for item in self.watchlist],
                    'mbi_value': self.mbi_value,
                    'mbi_label': self.mbi_label,
                    'opening_ranges': or_data,
                    'banned_symbols': list(self.banned),
                    'traded_symbols': list(self.traded),
                    'total_trades': self.total_trades,
                    'daily_pnl': self.daily_pnl,
                    'is_complete': True,
                }
            )

            pass  # 观察池条目已在 _do_screening 中写入
        except Exception as e:
            print(f"[HVOB] 保存日状态失败: {e}")
