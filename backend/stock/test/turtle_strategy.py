"""
海龟交易系统实现 - 基于天勤量化框架
实盘与回测分离版本
策略核心：
1. 使用20日唐奇安通道突破作为入场信号
2. 使用20日ATR进行仓位管理和止损设置
3. 基于10/20/40日均线排列判断趋势强度
4. 采用分批加仓策略，最多持仓3个单位
"""

import dataclasses
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
import numpy as np
from tqsdk import TqApi, TqAuth, TqBacktest, TargetPosTask

# ==================== 策略参数配置 ====================
MAX_UNITS = 3                   # 最大持仓单位数
ENTRY_UNITS = 1                 # 初始建仓单位数
ADD_UNITS = 1                   # 加仓单位数
ENTRY_PERIOD = 20               # 入场突破周期
EXIT_PERIOD = 10                # 离场突破周期
ATR_PERIOD = 20                 # ATR计算周期
MA_PERIODS = (10, 20, 40)       # 均线周期
RISK_PER_UNIT = 40000.0         # 每个单位的风险金额(元)


@dataclasses.dataclass
class TrendInfo:
    """趋势信息数据类"""
    factor: float        # 趋势因子：-0.3~0.5
    label: str           # 趋势标签
    rank: int            # 趋势强度等级：-2~2


class TurtleStrategy:
    """海龟交易系统主类"""
    
    def __init__(self, api: TqApi, symbol: str, contract_multiplier: float = 1.0):
        """
        初始化策略
        
        Args:
            api: 天勤API实例
            symbol: 交易合约代码
            contract_multiplier: 合约乘数
        """
        self.api = api
        self.symbol = symbol
        self.contract_multiplier = contract_multiplier
        
        # 获取K线数据（日线）
        self.klines = api.get_kline_serial(symbol, 86400, data_length=200)
        
        # 目标持仓工具
        self.target_pos = TargetPosTask(api, symbol)
        
        # 记录上一次K线数量
        self.last_kline_len = len(self.klines)
        
        # 持仓状态
        self.position_units = 0          # 当前持仓单位数
        self.direction = 0               # 持仓方向：1多 -1空 0无
        self.contracts_per_unit = 1      # 每单位手数
        self.last_add_price = None       # 上次加仓价格
        self.highest_close = None        # 多头持仓期间最高收盘价
        self.lowest_close = None         # 空头持仓期间最低收盘价
        
        # 延迟执行机制
        self.pending_volume = None
        self.pending_signal_at = None
        
        # 交易日志
        self.trade_log = []
        
        self._log(f"策略初始化完成 | 品种: {symbol} | 合约乘数: {contract_multiplier}")
        self._log(f"参数: MAX_UNITS={MAX_UNITS} | ENTRY_PERIOD={ENTRY_PERIOD} | ATR_PERIOD={ATR_PERIOD}")
    
    def _log(self, message: str) -> None:
        """统一日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def calculate_atr(self) -> float:
        """计算ATR（平均真实波幅）"""
        if len(self.klines) < ATR_PERIOD + 1:
            return 0.0
        
        high = self.klines["high"]
        low = self.klines["low"]
        close = self.klines["close"]
        prev_close = close.shift(1)
        
        # 计算真实波幅TR
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        
        tr = tr.dropna()
        if len(tr) < ATR_PERIOD:
            return 0.0
        
        # 计算ATR（使用RMA平滑）
        atr = tr.iloc[:ATR_PERIOD].mean()
        for i in range(ATR_PERIOD, len(tr)):
            atr = ((atr * (ATR_PERIOD - 1)) + tr.iloc[i]) / ATR_PERIOD
        
        return float(atr) if not np.isnan(atr) else 0.0
    
    def calculate_sma(self, window: int) -> float:
        """计算简单移动平均线"""
        if len(self.klines) < window:
            return 0.0
        series = self.klines["close"].dropna()
        if len(series) < window:
            return 0.0
        result = float(series.iloc[-window:].mean())
        return result if not np.isnan(result) else 0.0
    
    def calculate_trend_factor(self) -> TrendInfo:
        """计算趋势因子"""
        ma10 = self.calculate_sma(MA_PERIODS[0])
        ma20 = self.calculate_sma(MA_PERIODS[1])
        ma40 = self.calculate_sma(MA_PERIODS[2])
        
        if any(v == 0 or np.isnan(v) for v in [ma10, ma20, ma40]):
            return TrendInfo(factor=0.0, label="neutral", rank=0)
        
        diff10_20 = ma10 - ma20
        diff20_40 = ma20 - ma40
        threshold = 0.0045 * abs(ma20)
        
        # 多头排列
        if ma10 > ma20 > ma40:
            if diff10_20 > threshold and diff20_40 > threshold:
                return TrendInfo(factor=0.5, label="strong_bull", rank=2)
            return TrendInfo(factor=-0.15, label="weak_bull", rank=1)
        
        # 空头排列
        if ma10 < ma20 < ma40:
            if -diff10_20 > threshold and -diff20_40 > threshold:
                return TrendInfo(factor=0.5, label="strong_bear", rank=-2)
            return TrendInfo(factor=-0.15, label="weak_bear", rank=-1)
        
        # 震荡市
        if abs(diff10_20) < threshold and abs(diff20_40) < threshold:
            return TrendInfo(factor=-0.3, label="choppy", rank=0)
        
        return TrendInfo(factor=-0.15, label="weak_trend", rank=0)
    
    def calculate_breakout_levels(self) -> Tuple[float, float]:
        """计算唐奇安通道突破价位"""
        if len(self.klines) < ENTRY_PERIOD + 2:
            return 0.0, 0.0
        
        try:
            # 入场通道：过去N日最高/最低
            prior = self.klines["close"].iloc[-ENTRY_PERIOD - 1:-1]
            if len(prior) == 0:
                return 0.0, 0.0
            entry_high = float(prior.max())
            entry_low = float(prior.min())
            
            # 离场通道：过去M日最低/最高
            exit_prior = self.klines["close"].iloc[-EXIT_PERIOD - 1:-1]
            exit_low = float(exit_prior.min()) if len(exit_prior) > 0 else entry_low
            
            return entry_high, exit_low
        except Exception:
            return 0.0, 0.0
    
    def calculate_stop_price(self, atr20: float, trend_factor: float) -> float:
        """计算动态止损价"""
        if atr20 == 0 or np.isnan(atr20):
            return 0.0
        
        multiplier = 2.0 * (1.0 + trend_factor)
        
        if self.direction > 0 and self.highest_close:
            return self.highest_close - multiplier * atr20
        elif self.direction < 0 and self.lowest_close:
            return self.lowest_close + multiplier * atr20
        
        return 0.0
    
    def calculate_units(self, atr20: float, trend_factor: float) -> int:
        """计算每单位应持仓手数"""
        stop_distance = 2.0 * (1.0 + trend_factor) * atr20
        if stop_distance <= 0 or self.contract_multiplier <= 0:
            return 1
        
        units = int(RISK_PER_UNIT / (stop_distance * self.contract_multiplier))
        return max(1, min(MAX_UNITS, units))
    
    def check_entry_signal(self, current_close: float, entry_high: float, 
                          entry_low: float, trend_info: TrendInfo) -> Optional[int]:
        """检查入场信号"""
        if entry_high == 0 or entry_low == 0:
            return None
        
        # 震荡市过滤
        if trend_info.label == "choppy":
            return None
        
        # 做多信号
        if current_close > entry_high:
            return 1
        
        # 做空信号
        if current_close < entry_low:
            return -1
        
        return None
    
    def check_exit_signal(self, current_close: float, exit_low: float) -> bool:
        """检查离场信号"""
        if self.direction > 0:
            return current_close < exit_low
        elif self.direction < 0:
            # 空头离场用上轨
            _, entry_low = self.calculate_breakout_levels()
            return current_close > entry_low
        return False
    
    def check_addon_signal(self, current_price: float, atr20: float) -> bool:
        """检查加仓信号"""
        if self.position_units >= MAX_UNITS or self.last_add_price is None:
            return False
        
        if self.direction > 0:
            add_threshold = self.last_add_price + 0.5 * atr20
            return current_price >= add_threshold
        elif self.direction < 0:
            add_threshold = self.last_add_price - 0.5 * atr20
            return current_price <= add_threshold
        
        return False
    
    def execute_entry(self, direction: int, current_close: float, 
                     atr20: float, trend_info: TrendInfo) -> None:
        """执行入场"""
        self.direction = direction
        self.position_units = ENTRY_UNITS
        self.last_add_price = current_close
        self.highest_close = current_close
        self.lowest_close = current_close
        self.contracts_per_unit = self.calculate_units(atr20, trend_info.factor)
        
        total_volume = self.position_units * self.contracts_per_unit
        if direction < 0:
            total_volume = -total_volume
        
        stop_price = self.calculate_stop_price(atr20, trend_info.factor)
        
        self._log(f"🐢 入场信号 | 方向: {'多' if direction > 0 else '空'} | "
                 f"价格: {current_close:.2f} | 手数: {abs(total_volume)} | "
                 f"止损: {stop_price:.2f}")
        
        self._schedule_order(total_volume, "entry")
    
    def execute_addon(self, current_price: float, atr20: float) -> None:
        """执行加仓"""
        self.position_units += ADD_UNITS
        self.last_add_price = current_price
        
        total_volume = self.position_units * self.contracts_per_unit
        if self.direction < 0:
            total_volume = -total_volume
        
        self._log(f"➕ 加仓信号 | 单位: {self.position_units}/{MAX_UNITS} | "
                 f"价格: {current_price:.2f} | 总手数: {abs(total_volume)}")
        
        self._schedule_order(total_volume, "addon")
    
    def execute_exit(self, reason: str) -> None:
        """执行离场"""
        total_volume = self.position_units * self.contracts_per_unit
        if self.direction < 0:
            total_volume = -total_volume
        
        self._log(f"🏁 离场信号 | 原因: {reason} | 平仓手数: {abs(total_volume)}")
        
        self._schedule_order(0, "exit")
        self._reset_position()
    
    def _schedule_order(self, target_volume: int, reason: str) -> None:
        """安排在下一根K线执行订单"""
        self.pending_volume = target_volume
        if len(self.klines) > 0:
            self.pending_signal_at = self.klines.index[-1]
    
    def _execute_pending_order(self) -> None:
        """执行延迟订单"""
        if self.pending_volume is not None and self.pending_signal_at is not None:
            if len(self.klines) > 0 and self.klines.index[-1] > self.pending_signal_at:
                self.target_pos.set_target_volume(self.pending_volume)
                self.pending_volume = None
                self.pending_signal_at = None
    
    def _reset_position(self) -> None:
        """重置持仓状态"""
        self.position_units = 0
        self.direction = 0
        self.contracts_per_unit = 1
        self.last_add_price = None
        self.highest_close = None
        self.lowest_close = None
    
    def update_position_tracking(self, current_close: float) -> None:
        """更新持仓跟踪价格"""
        if self.direction > 0:
            if self.highest_close is None:
                self.highest_close = current_close
            else:
                self.highest_close = max(self.highest_close, current_close)
        elif self.direction < 0:
            if self.lowest_close is None:
                self.lowest_close = current_close
            else:
                self.lowest_close = min(self.lowest_close, current_close)
    
    def check_stop_loss(self, current_close: float, atr20: float, 
                        trend_factor: float) -> bool:
        """检查是否触发止损"""
        stop_price = self.calculate_stop_price(atr20, trend_factor)
        if stop_price == 0:
            return False
        
        if self.direction > 0:
            return current_close <= stop_price
        elif self.direction < 0:
            return current_close >= stop_price
        
        return False
    
    def print_status(self, current_close: float, atr20: float, 
                     trend_info: TrendInfo) -> None:
        """打印当前状态"""
        entry_high, exit_low = self.calculate_breakout_levels()
        
        print(f"\n📊 [{self._get_current_date()}] 行情状态")
        print(f"  ├─ 收盘价: {current_close:.2f}")
        print(f"  ├─ ATR: {atr20:.2f}")
        print(f"  ├─ 趋势: {trend_info.label} (因子={trend_info.factor})")
        print(f"  ├─ 入场上轨: {entry_high:.2f} | 离场下轨: {exit_low:.2f}")
        
        if self.position_units > 0:
            stop_price = self.calculate_stop_price(atr20, trend_info.factor)
            direction_str = "多头" if self.direction > 0 else "空头"
            print(f"  └─ 持仓: {direction_str} {self.position_units}/{MAX_UNITS}单位 | "
                 f"止损: {stop_price:.2f}")
        else:
            print(f"  └─ 持仓: 空仓")
    
    def _get_current_date(self) -> str:
        """获取当前K线日期"""
        try:
            if len(self.klines) > 0:
                timestamp = self.klines.index[-1]
                if isinstance(timestamp, pd.Timestamp):
                    return timestamp.strftime("%Y-%m-%d")
        except:
            pass
        return datetime.now().strftime("%Y-%m-%d")
    
    def on_bar(self) -> None:
        """每根新K线触发一次的策略核心逻辑"""
        if len(self.klines) < max(MA_PERIODS) + ATR_PERIOD:
            return
        
        # 获取最新数据
        current_close = float(self.klines["close"].iloc[-1])
        
        # 计算技术指标
        atr20 = self.calculate_atr()
        if atr20 == 0:
            return
        
        trend_info = self.calculate_trend_factor()
        entry_high, exit_low = self.calculate_breakout_levels()
        
        # 打印状态（每天一次）
        if not hasattr(self, '_last_print_date') or self._last_print_date != self._get_current_date():
            self._last_print_date = self._get_current_date()
            self.print_status(current_close, atr20, trend_info)
        
        # ========== 策略逻辑 ==========
        
        # 更新持仓跟踪价格
        if self.position_units > 0:
            self.update_position_tracking(current_close)
            
            # 检查止损
            if self.check_stop_loss(current_close, atr20, trend_info.factor):
                self.execute_exit("止损")
            # 检查离场信号
            elif self.check_exit_signal(current_close, exit_low):
                self.execute_exit("通道离场")
            # 检查加仓
            elif self.check_addon_signal(current_close, atr20):
                self.execute_addon(current_close, atr20)
        
        # 检查入场（无持仓时）
        elif self.position_units == 0:
            direction = self.check_entry_signal(current_close, entry_high, 
                                                exit_low, trend_info)
            if direction:
                self.execute_entry(direction, current_close, atr20, trend_info)
        
        # 执行延迟订单
        self._execute_pending_order()
    
    # ==================== 实盘模式 ====================
    
    def run_live(self) -> None:
        """实盘/模拟盘模式运行"""
        self._log(f"🚀 启动实盘模式 | 合约: {self.symbol}")
        
        while True:
            try:
                # wait_update会阻塞，直到有行情变化
                self.api.wait_update()
                
                # 检查K线数据是否发生变化
                if self.api.is_changing(self.klines):
                    # 只有当K线长度增加（新K线生成）时才触发策略
                    if len(self.klines) > self.last_kline_len:
                        self.last_kline_len = len(self.klines)
                        self.on_bar()
                        
            except KeyboardInterrupt:
                self._log("👋 实盘策略已停止")
                break
            except Exception as e:
                self._log(f"❌ 实盘运行错误: {e}")
                break
    
    # ==================== 回测模式 ====================
    
    def run_backtest(self, start_dt, end_dt, init_balance=100000) -> None:
        """
        回测模式运行
        
        Args:
            start_dt: 回测开始时间
            end_dt: 回测结束时间
            init_balance: 初始资金
        """
        self._log(f"🚀 启动回测模式 | 合约: {self.symbol}")
        self._log(f"回测区间: {start_dt} 到 {end_dt} | 初始资金: {init_balance}")
        
        # 使用Backtest上下文
        with TqBacktest(start_dt=start_dt, end_dt=end_dt, 
                       init_balance=init_balance, auth=self.api.auth) as bk:
            # 在回测上下文中重新初始化API和K线
            self.api = bk
            self.target_pos = TargetPosTask(self.api, self.symbol)
            self.klines = self.api.get_kline_serial(self.symbol, 86400, data_length=200)
            self.last_kline_len = len(self.klines)
            
            # 回测主循环
            while True:
                try:
                    self.api.wait_update()
                    
                    # 检查K线更新
                    if self.api.is_changing(self.klines):
                        if len(self.klines) > self.last_kline_len:
                            self.last_kline_len = len(self.klines)
                            self.on_bar()
                    
                    # 检查回测是否结束
                    if self.api.is_changing(self.api.get_quote(self.symbol), "datetime"):
                        # 获取回测报告
                        if hasattr(self.api, 'get_report'):
                            report = self.api.get_report()
                            if report:
                                self._print_backtest_report(report)
                                break
                                
                except KeyboardInterrupt:
                    self._log("👋 回测已中断")
                    break
                except Exception as e:
                    self._log(f"❌ 回测运行错误: {e}")
                    break
    
    def _print_backtest_report(self, report: dict) -> None:
        """打印回测报告"""
        print("\n" + "="*50)
        print("📈 海龟交易系统回测报告")
        print("="*50)
        print(f"总收益率: {report.get('total_return_rate', 0):.2%}")
        print(f"年化收益率: {report.get('annual_return_rate', 0):.2%}")
        print(f"最大回撤: {report.get('max_drawdown', 0):.2%}")
        print(f"夏普比率: {report.get('sharpe_ratio', 0):.2f}")
        print(f"胜率: {report.get('win_rate', 0):.2%}")
        print(f"盈亏比: {report.get('profit_loss_ratio', 0):.2f}")
        print(f"总交易次数: {report.get('total_trade_count', 0)}")
        print("="*50)


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    # 配置参数
    USERNAME = "yupei1986"      # 请替换为实际用户名
    PASSWORD = "yupei1986"      # 请替换为实际密码
    SYMBOL = "KQ.m@SHFE.rb"         # 螺纹钢主力连续
    CONTRACT_MULTIPLIER = 10.0      # 螺纹钢10吨/手
    
    # 选择运行模式
    MODE = "BACKTEST"  # 可选: "BACKTEST" 或 "LIVE"
    
    # 创建认证对象
    auth = TqAuth(USERNAME, PASSWORD)
    
    if MODE == "BACKTEST":
        # ========== 回测模式 ==========
        from datetime import datetime
        
        # 创建API（回测模式）
        api = TqApi(auth=auth)
        
        # 创建策略实例
        strategy = TurtleStrategy(api, SYMBOL, CONTRACT_MULTIPLIER)
        
        # 运行回测
        strategy.run_backtest(
            start_dt=datetime(2026, 1, 1),
            end_dt=datetime(2026, 3, 20),
            init_balance=100000
        )
        
    else:
        # ========== 实盘/模拟盘模式 ==========
        
        # 创建API（实盘模式）
        api = TqApi(auth=auth)
        
        # 创建策略实例
        strategy = TurtleStrategy(api, SYMBOL, CONTRACT_MULTIPLIER)
        
        # 运行实盘
        strategy.run_live()
    
    # 关闭连接
    api.close()