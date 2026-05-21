"""
HVOB-MBI 交易引擎：TqSDK wait_update 事件循环，时间相位驱动。

相位流程：
  screening(启动) → night_or(21:00-21:30) → night_breakout(21:30-23:00)
  → gap_check(9:00) → day_or(9:00-9:30) → day_breakout(9:30-14:30)
  → force_close(14:55) → done
"""
import time
import json
from datetime import datetime, date
from decimal import Decimal
from collections import defaultdict

from tqsdk import TargetPosTask
from django.db import close_old_connections

from stock.models import FullContractList, TradingAccount
from .config import (
    NIGHT_OR_CLOSE, DAY_OPEN, DAY_OR_CLOSE, FORCE_CLOSE_TIME,
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
        self.target_pos_tasks = {}    # {symbol: TargetPosTask}
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

        # Phase 1: 盘前筛选
        self._do_screening()

        # 订阅 watchlist 数据
        self._subscribe_all()

        # 等待数据就绪
        print("[HVOB] 等待行情数据就绪...")
        self.api.wait_update(deadline=time.time() + 20)

        # 进入事件循环
        last_phase_log = ''
        while self.phase != 'done':
            self.api.wait_update()
            now = datetime.now()

            # 定时重启连接（8:55 / 13:25 / 20:55）
            self._check_restart(now)

            self._check_phase(now, last_phase_log)

        # 收盘后记录
        self._finalize()

    def _check_phase(self, now, last_phase_log):
        """时间相位切换"""
        t = now.time()

        if self.phase == 'night_or' and t >= NIGHT_OR_CLOSE:
            self._close_night_opening_range()
            self.phase = 'night_breakout'
            print(f"[HVOB] → night_breakout")

        elif self.phase == 'night_breakout':
            if t >= DAY_OPEN:
                self._check_gap()
                self.phase = 'gap_check'
                print(f"[HVOB] → gap_check")
            else:
                self._on_quote('night_breakout')

        elif self.phase == 'gap_check' and t >= DAY_OR_CLOSE:
            self._close_day_opening_range()
            self._calc_mbi()
            self.phase = 'day_breakout'
            print(f"[HVOB] → day_breakout (MBI={self.mbi_value:.4f})")

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
        restart_key = None
        if (now.hour == 8 and now.minute == 55) or \
           (now.hour == 13 and now.minute == 25) or \
           (now.hour == 20 and now.minute == 55):
            restart_key = now.strftime('%Y-%m-%d-%H%M')
        if restart_key and restart_key != self._last_restart_key:
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
        # 旧的 TargetPosTask 已绑定旧连接，清空后按需重新创建
        self.target_pos_tasks.clear()
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
        self.phase = 'night_or'
        print(f"[HVOB] → night_or (等待夜盘开盘区间)")

    # ==================== 订阅 ====================

    def _subscribe_all(self):
        """订阅所有 watchlist 品种的 Quote + 5min Kline"""
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
            if current_phase == 'night_breakout' and not self._is_night_product(product_code):
                continue

            quote = self.api.get_quote(symbol)
            if quote is None or quote.last_price is None or quote.last_price == 0:
                continue

            price = float(quote.last_price)

            # 开盘区间跟踪
            if current_phase in ('night_breakout',):
                self._track_opening_range(symbol, price, is_night=True)
            elif current_phase == 'day_breakout':
                self._track_opening_range(symbol, price, is_night=False)

            # 检查已有持仓的止损/止盈
            if symbol in self.positions:
                self._check_exit(symbol, price)

            # 突破检查（只在对应阶段检查）
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
        """关闭夜盘开盘区间"""
        print("[HVOB] 夜盘开盘区间关闭")
        for sym, or_ in self.opening_ranges.items():
            if or_.get('night') and not or_['closed']:
                or_['R'] = or_['H'] - or_['L']
                or_['closed'] = True
                print(f"  {sym}: H={or_['H']:.2f} L={or_['L']:.2f} R={or_['R']:.2f}")

    def _close_day_opening_range(self):
        """关闭日盘开盘区间"""
        print("[HVOB] 日盘开盘区间关闭")
        for sym, or_ in self.opening_ranges.items():
            if not or_.get('night') and not or_['closed']:
                or_['R'] = or_['H'] - or_['L']
                or_['closed'] = True
                print(f"  {sym}: H={or_['H']:.2f} L={or_['L']:.2f} R={or_['R']:.2f}")

    # ==================== 跳空检查 ====================

    def _check_gap(self):
        """夜盘品种跳空检查：开盘价在夜盘区间外 → 拉黑"""
        print("[HVOB] 跳空检查")
        for item in self.watchlist:
            if not self._is_night_product(item['product_code']):
                continue
            symbol = item['symbol']
            quote = self.api.get_quote(symbol)
            if quote is None or quote.last_price is None:
                continue
            or_ = self.opening_ranges.get(symbol)
            if or_ is None or or_['R'] is None:
                continue
            open_price = float(getattr(quote, 'open', 0) or 0)
            if open_price <= 0:
                continue
            if open_price < or_['L'] or open_price > or_['H']:
                self.banned.add(symbol)
                print(f"  ⛔ {symbol} 跳空穿越: 区间[{or_['L']:.2f},{or_['H']:.2f}] 开盘{open_price:.2f} → 拉黑")
            else:
                print(f"  ✓ {symbol} 正常: 开盘{open_price:.2f} 在区间内")

    # ==================== MBI ====================

    def _calc_mbi(self):
        """计算 MBI"""
        from .mbi import calculate_mbi
        self.mbi_value, self.mbi_label = calculate_mbi(self.api, self.watchlist, self.opening_ranges)

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

        # 计算手数
        volume = self._calc_volume(symbol, direction, r)
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
        # stop_distance = or_r * STOP_OFFSET_RATIO * 2 (双向止损总距离)
        risk_amount = balance * risk_pct
        stop_distance = float(or_r) * STOP_OFFSET_RATIO * 2
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

        try:
            # TargetPosTask
            if symbol not in self.target_pos_tasks:
                self.target_pos_tasks[symbol] = TargetPosTask(self.api, symbol)
            target = volume if direction == 1 else -volume
            self.target_pos_tasks[symbol].set_target_volume(target)
            self.api.wait_update(deadline=time.time() + 5)

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
            if symbol in self.target_pos_tasks:
                self.target_pos_tasks[symbol].set_target_volume(0)
                self.api.wait_update(deadline=time.time() + 5)

            record_stop_loss_signal(
                self.account, symbol, pos.product_code, self.trade_date,
                pos.direction, float(price), exit_pnl, pos.entry_price, pos.volume,
            )

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
            if symbol in self.target_pos_tasks:
                self.target_pos_tasks[symbol].set_target_volume(0)
                self.api.wait_update(deadline=time.time() + 5)

            record_exit_signal(
                self.account, symbol, pos.product_code, self.trade_date,
                pos.direction, float(price), reason, exit_pnl, pos.entry_price, pos.volume,
            )

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
            price = float(quote.last_price) if quote and quote.last_price else 0
            if price <= 0:
                continue

            exit_pnl = self._calc_pnl(pos, price)

            if not self.dry_run:
                if symbol in self.target_pos_tasks:
                    self.target_pos_tasks[symbol].set_target_volume(0)
                    self.api.wait_update(deadline=time.time() + 5)

                record_exit_signal(
                    self.account, symbol, pos.product_code, self.trade_date,
                    pos.direction, price, '强制平仓', exit_pnl, pos.entry_price, pos.volume,
                )

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
                self.api.wait_update()
                account_info = self.api.get_account()
                balance = float(getattr(account_info, 'balance', 0) or 0)
                record_daily_equity(self.account, self.trade_date, balance, self.daily_pnl)
            except Exception as e:
                print(f"[HVOB] 记录日权益失败: {e}")

        # 保存日状态
        self._save_daily_state()

    def _save_daily_state(self):
        """保存每日状态到 HvobMbiDailyState，同时写入独立观察池条目"""
        try:
            from .models import HvobMbiDailyState, HvobMbiWatchlistItem
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

            # 写入独立观察池条目
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
            if items:
                HvobMbiWatchlistItem.objects.bulk_create(items, ignore_conflicts=True)
        except Exception as e:
            print(f"[HVOB] 保存日状态失败: {e}")
