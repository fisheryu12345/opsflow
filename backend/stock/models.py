from django.db import models
from django.db.models import CheckConstraint, Q
from decimal import Decimal

# ==================== 1. 基础架构层 ====================
'''
这份 models.py 文件构建了一个非常完整且专业的量化交易系统数据库架构。它不仅仅记录了交易结果，更重要的是实现了策略逻辑的持久化、状态管理以及参数化配置。
这套设计将原本“一次性运行”的脚本策略，升级为了一个可监控、可回溯、可配置的系统工程。
以下是针对该文件中各个表的详细作用汇总分析：

️ 1. 基础架构层 (基础设施)
这一层定义了系统运行的物理环境和标的物，是整个系统的基石。
TradingAccount (交易账户表)
● 核心作用：资金总账
● 功能解析：
○ 它是策略的“根节点”。系统支持多账户并行（例如：同时跑一个“激进版海龟”和一个“稳健版海龟”）。
○ 记录初始资金（计算收益率的基准）和当前动态权益（实时净值）。
○ 通过 is_active 字段实现“软删除”，暂停策略时不丢失历史数据。
FullContractList (全合约基础信息表 / 交易标的池)
● 核心作用：交易白名单与元数据中心
● 功能解析：
○ 开关控制：这是策略的“水龙头”。只有 is_active=True 的品种，策略主循环才会去订阅和计算。
○ 元数据映射：存储了 volume_multiple (合约乘数)、price_tick (最小变动价位) 等关键信息。策略在计算仓位（如：开仓手数 = 风险金额 / (ATR * 乘数)）时，直接从数据库读取这些参数，无需写死在代码中。
○ 板块分类：通过 sector 字段，方便后续做板块轮动策略（如：只做化工板块）。
StrategyConfig (策略参数配置表)
● 核心作用：策略逻辑的遥控器
● 功能解析：
○ 实现了配置与代码分离。原本代码中写死的 ATR_PERIOD=20 或 MAX_UNITS=3 现在都提取到了数据库。
○ 允许针对不同合约应用不同的参数（例如：股指期货波动大，可以单独给它配一套更保守的参数）。
○ 修改参数后，无需重启 Python 程序（或只需热重载），策略即可按新参数运行。



2. 信号与分析层 (大脑)
这一层记录了策略“思考”的过程，用于解释“为什么买”或“为什么不买”。
TrendInfo (品种趋势信息表)
● 核心作用：市场状态快照
● 功能解析：
○ 对应策略中的趋势过滤逻辑（如 calculate_trend_factor）。
○ 它记录了某一天、某个品种的市场状态（强多、震荡、弱空等）。
○ 价值：当策略没有开仓时，你可以通过查询这张表，发现是因为市场处于“震荡”状态被过滤掉了，而不是程序出错了。
DailyStrategySignal (每日策略信号表)
● 核心作用：决策日志
● 功能解析：
○ 记录了具体的交易触发条件。它回答了：“今天突破了吗？上轨价格是多少？”
○ 记录了 donchian_upper (唐奇安上轨) 和 donchian_lower (下轨)。
○ 如果产生了信号但未交易（例如因为资金不足或跳空过大），remark 字段会记录原因。这是排查策略“漏单”问题的关键依据。



3. 状态管理层 (记忆)
这一层解决了 Python 脚本重启后“失忆”的问题，是实盘交易连续性的保障。
PositionState (策略持仓状态表)
● 核心作用：策略的内存条
● 功能解析：
○ 这是最关键的表之一。它存储了策略运行时的上下文变量。
○ 记录了：当前持有多少单位 (units)、上次加仓价 (last_add_price)、持仓期间的最高价 (highest_close，用于移动止损)。
○ 挂单状态：处理了“信号已出但未成交”的中间状态（如 pending_direction），防止程序重启后重复发单或漏单。
○ 移仓管理：包含 is_rollover_needed 等字段，辅助主力合约切换。
RolloverLog (移仓换月日志表)
● 核心作用：合约切换记录
● 功能解析：
○ 专门记录主力合约切换的操作（例如从 rb2405 换到 rb2410）。
○ 记录了旧合约、新合约、换月时间和状态，方便统计移仓成本。



4. 交易与绩效层 (结果)
这一层记录了最终的执行结果和账户表现，用于事后分析和报表展示。
TradeExecution (交易执行明细表)
● 核心作用：资金流水账
● 功能解析：
○ 每一笔实际发生的买卖操作都会在这里留痕。
○ 区分了交易类型：ENTRY (首仓)、ADD_ON (加仓)、STOP_LOSS (止损)。这对于分析策略的加仓逻辑是否有效至关重要。
○ 关联了 DailyStrategySignal，可以将一笔成交追溯到具体的触发信号。
DailyPerformance (每日绩效指标表)
● 核心作用：账户体检报告
● 功能解析：
○ 每天收盘后计算并存储的“成绩单”。
○ 包含核心量化指标：sharpe_ratio (夏普比率)、max_drawdown (最大回撤)、calmar_ratio (卡尔玛比率)。
○ 前端 Dashboard 的图表数据主要来源于此表。



总结：数据流向图
为了帮助后续人员理解，可以将数据流向概括为：
1. 初始化：读取 FullContractList (交易谁?) 和 StrategyConfig (怎么交易?)。
2. 盘中计算：
○ 根据行情计算 TrendInfo (趋势如何?)。
○ 生成 DailyStrategySignal (有无信号?)。
3. 状态检查：读取 PositionState (现在持仓如何?)。
4. 决策与执行：
○ 结合信号和状态，决定是否下单。
○ 下单后写入 TradeExecution (流水)。
○ 更新 PositionState (更新记忆)。
5. 盘后结算：
○ 更新 TradingAccount (更新净值)。
○ 计算并写入 DailyPerformance (生成报表)。
'''

class TradingAccount(models.Model):
    """
    【交易账户表】
    
    💡 为什么需要这张表？
    这是整个系统的"根"。虽然你的策略代码里定义了初始资金，但在实盘或长期回测中，
    我们需要一个持久化的实体来记录"我有多少钱"以及"现在的总权益是多少"。
    它支持多账户管理（比如你可以同时跑一个激进版和一个稳健版策略）。
    """
    # 账户名称：用于区分不同的策略实例（例如："海龟策略_甲醇605"）
    name = models.CharField("账户名称", max_length=50, unique=True, db_index=True,
                           help_text="用于区分不同的策略实例，如：海龟策略_甲醇605")
    
    # 初始资金：策略启动时的本金，用于计算累计收益率的基准
    initial_balance = models.DecimalField(
        "初始资金", 
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('1000000.00'),
        help_text="策略启动时的本金，作为计算累计收益率的基准"
    )
    
    # 当前动态权益：
    # 这是最核心的实时数据。每次策略循环结束，都应该用 TqApi 返回的最新权益更新这里。
    # 公式：现金 + 持仓盈亏
    current_equity = models.DecimalField(
        "当前权益", 
        max_digits=15, 
        decimal_places=2, 
        default=Decimal('1000000.00'),
        help_text="实时净值 = 现金 + 持仓盈亏，每次策略循环后更新"
    )
    
    # 启用状态：软删除标记，如果不想跑策略了，改为 False 即可，保留历史数据
    is_active = models.BooleanField("启用状态", default=True, db_index=True,
                                   help_text="软删除标记，False时暂停策略但保留历史数据")
    
    # 自动记录创建和更新时间
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.name} (权益: {self.current_equity})"

    class Meta:
        verbose_name = "交易账户"
        verbose_name_plural = "交易账户"
        ordering = ['-created_at']


class FullContractList(models.Model):
    """
    【全合约基础信息表 / 交易标的池】
    
    💡 核心作用：
    1. 交易开关：只有在这里面且 is_active=True 的品种，策略才会去订阅和交易。
    2. 元数据源：提供合约乘数、最小变动价位等，用于计算仓位和止损金额。
    3. 板块分类：用于区分品种属性（如黑色、化工、农产品）。
    """
    
    # --- 基础身份信息 ---
    # 交易所代码：SHFE, DCE, CZCE, CFFEX, GFEX
    exchange = models.CharField("交易所", max_length=10, db_index=True,
                               help_text="交易所代码：SHFE, DCE, CZCE, CFFEX, GFEX")
    
    # 品种代码：例如 "rb" (螺纹钢), "MA" (甲醇), "IF" (沪深300)
    # 注意：这是不带年份的缩写，用于区分品种属性
    product_code = models.CharField("品种代码", max_length=10, db_index=True,
                                   help_text="品种代码（不带年份），如：rb, MA, IF")
    
    # 合约代码：例如 "rb2405", "MA605"。这是实盘中交易的具体标的
    # 对于主力合约切换，这个字段会频繁更新，或者我们只存主力合约的代码
    symbol = models.CharField("当前主力合约", max_length=20, unique=True, 
                             help_text="当前正在交易的主力合约代码，如：rb2405, MA605")
    
    # 合约名称：例如 "螺纹钢2405"
    name = models.CharField("合约名称", max_length=50, blank=True, null=True,
                           help_text="合约中文名称，如：螺纹钢2405")

    # --- 交易控制开关 ---
    is_active = models.BooleanField("开启交易", default=False, db_index=True,
                                   help_text="核心开关：False则策略完全忽略此品种")
    allow_open = models.BooleanField("允许开仓", default=True,
                                    help_text="如果是False，只能平仓不能开新仓（用于逐步退市）")
    
    # --- 合约规格 (用于计算仓位) ---
    volume_multiple = models.IntegerField("合约乘数", default=10, 
                                         help_text="每手合约的价值乘数，如螺纹钢10，IF是300")
    price_tick = models.DecimalField("最小变动价位", max_digits=10, decimal_places=4, 
                                    default=Decimal('1.0'), 
                                    help_text="价格最小变动单位，跳动一个tick的价格变化")
    margin_ratio = models.DecimalField("保证金比例(预估)", max_digits=6, decimal_places=4, 
                                      default=Decimal('0.1'),
                                      help_text="用于预估占用保证金，范围0-1")

    # --- 分类信息 ---
    sector = models.CharField("所属板块", max_length=20, blank=True, null=True, 
                             help_text="例如：黑色金属、化工、农产品、金融")
    category = models.CharField("详细分类", max_length=20, blank=True, null=True,
                               help_text="例如：螺纹类、PTA类")

    # --- 移仓换月辅助 ---
    # 标记该品种是否需要进行主力换月（有些品种如股指期货可能不需要频繁换月，或者换月逻辑不同）
    need_rollover = models.BooleanField("需移仓换月", default=True,
                                       help_text="标记是否需要进行主力合约换月操作")

    # --- 时间戳 ---
    created_at = models.DateTimeField("录入时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        status = "启用" if self.is_active else "停用"
        return f"{self.exchange}.{self.symbol} ({self.name or '未知'}) - {status}"

    class Meta:
        verbose_name = "交易合约列表"
        verbose_name_plural = "交易合约列表"
        # 方便前端按交易所或板块筛选
        ordering = ['exchange', 'sector', 'product_code']
        constraints = [
            CheckConstraint(
                check=Q(margin_ratio__gte=0) & Q(margin_ratio__lte=1),
                name='margin_ratio_between_0_and_1'
            ),
        ]

class StrategyConfig(models.Model):
    """
    【策略参数配置表】
    
    💡 为什么需要这张表？
    你的原代码中，MAX_UNITS, ATR_PERIOD 等都是写死的全局变量。
    这张表实现了"配置与代码分离"。
    1. 如果你想测试"把ATR周期改成14效果如何"，不需要改代码重启，直接在数据库改这里。
    2. 不同品种可以应用不同的配置（例如：螺纹钢波动大，风险参数可以单独设）。
    """
    name = models.CharField("配置名称", max_length=50, unique=True, help_text="例如: 海龟策略_标准版")
    symbol = models.CharField("适用合约", max_length=20, db_index=True, help_text="例如: CZCE.MA605")
    is_active = models.BooleanField("是否启用", default=True, db_index=True)

    # --- 资金管理参数 ---
    max_units = models.IntegerField("最大持仓单位", default=3, help_text="对应代码 MAX_UNITS，限制最大加仓次数")
    entry_units = models.IntegerField("初始建仓单位", default=1, help_text="对应代码 ENTRY_UNITS")
    risk_per_unit = models.DecimalField("每单位风险金额", max_digits=15, decimal_places=2, default=Decimal('40000'), help_text="对应代码 RISK_PER_UNIT，决定开仓手数")
    
    # --- 技术指标参数 ---
    atr_period = models.IntegerField("ATR周期", default=20, help_text="对应代码 ATR_PERIOD")
    entry_period = models.IntegerField("入场突破周期", default=20, help_text="对应代码 ENTRY_PERIOD，唐奇安通道上轨周期")
    exit_period = models.IntegerField("离场突破周期", default=10, help_text="对应代码 EXIT_PERIOD，唐奇安通道下轨周期")
    
    # --- 均线参数 ---
    ma_periods = models.CharField("均线周期(逗号分隔)", max_length=20, default="10,20,40", help_text="用于计算趋势因子")
    
    # --- 过滤参数 ---
    gap_threshold = models.DecimalField("跳空放弃阈值(%)", max_digits=5, decimal_places=2, default=Decimal('1.0'), help_text="对应代码中的跳空过滤逻辑，超过1%放弃开仓")

    class Meta:
        verbose_name = "策略参数配置"
        verbose_name_plural = "策略参数配置"

    def __str__(self):
        return self.name


# ==================== 2. 信号与分析层 (大脑) ====================

class TrendInfo(models.Model):
    """
    【品种趋势信息表】

    💡 为什么需要这张表？
    对应你代码中的 `calculate_trend_factor` 函数。
    这张表存储的是"每日情报"。它记录了市场当下的状态（是强多、震荡还是弱空）。
    作用：
    1. 解释性：当策略不开仓时，你可以查这张表，发现是因为 trend_label 是 'choppy' (震荡)。
    2. 筛选：你可以快速找出所有处于 'strong_bull' 状态的品种进行重点关注。
    """
    TREND_LABEL_CHOICES = [
        ('strong_bull', '强多'),
        ('weak_bull', '弱多'),
        ('choppy', '震荡'),
        ('weak_bear', '弱空'),
        ('strong_bear', '强空'),
        ('transition', '过渡'),
        ('neutral', '中性'),
    ]

    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='trend_infos', verbose_name="所属账户")
    symbol = models.CharField("合约代码", max_length=20, db_index=True)
    calc_date = models.DateField("计算日期", db_index=True, help_text="该趋势判断对应的日期")

    # 核心因子：-0.3 到 0.5 之间，数值越大代表趋势越强
    factor = models.DecimalField("趋势因子", max_digits=6, decimal_places=4)

    # 标签：人类可读的趋势描述
    label = models.CharField("趋势标签", max_length=20, choices=TREND_LABEL_CHOICES, db_index=True)

    # 等级：-2 (极强空) 到 2 (极强多)，用于量化排序
    rank = models.IntegerField("趋势强度等级", default=0)

    # 辅助字段：记录当时的均线价格，用于验证均线排列状态
    ma10 = models.DecimalField("MA10", max_digits=12, decimal_places=2, null=True, blank=True)
    ma20 = models.DecimalField("MA20", max_digits=12, decimal_places=2, null=True, blank=True)
    ma40 = models.DecimalField("MA40", max_digits=12, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    def __str__(self):
        return f"{self.symbol} - {self.calc_date} - {self.get_label_display()}"

    class Meta:
        verbose_name = "品种趋势信息"
        verbose_name_plural = "品种趋势信息"
        unique_together = ('symbol', 'calc_date') # 每天每个品种只存一条
        ordering = ['-calc_date']
        indexes = [
            models.Index(fields=['symbol', '-calc_date']),
            models.Index(fields=['label', '-calc_date']),
        ]


class DailyStrategySignal(models.Model):
    """
    【每日策略信号表】
    
    💡 为什么需要这张表？
    这是最详细的"决策日志"。TrendInfo 只记录趋势状态，而这张表记录了**具体的交易信号**。
    它对应代码中的 `calculate_breakout_levels` 和 `check_entry_signal`。
    它回答了："今天突破了吗？上轨是多少？为什么没买？"
    """
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='daily_signals')
    symbol = models.CharField("合约代码", max_length=20, db_index=True)
    trade_date = models.DateField("交易日期", db_index=True)

    # --- 决策依据 ---
    trend_factor = models.DecimalField("趋势因子", max_digits=6, decimal_places=4, help_text="当时的趋势因子值")
    trend_label = models.CharField("趋势标签", max_length=20, help_text="当时的趋势标签")
    trend_rank = models.IntegerField("趋势强度等级")
    
    # --- 通道数据 ---
    donchian_upper = models.DecimalField("唐奇安上轨", max_digits=12, decimal_places=2, null=True, blank=True, help_text="突破这个价格开多")
    donchian_lower = models.DecimalField("唐奇安下轨", max_digits=12, decimal_places=2, null=True, blank=True, help_text="跌破这个价格开空")
    
    # --- 信号结果 ---
    is_breakout = models.BooleanField("是否突破", default=False, db_index=True, help_text="收盘价是否突破了上轨或下轨")
    signal_direction = models.IntegerField("信号方向", default=0, db_index=True, help_text="1:多, -1:空, 0:无")
    
    # 备注：记录过滤原因，例如 "突破但处于震荡市过滤"
    remark = models.TextField("备注", blank=True, null=True)

    class Meta:
        verbose_name = "每日策略信号"
        verbose_name_plural = "每日策略信号"
        unique_together = ('account', 'symbol', 'trade_date')
        ordering = ['-trade_date']
        indexes = [
            models.Index(fields=['symbol', '-trade_date']),
            models.Index(fields=['is_breakout', '-trade_date']),
        ]


# ==================== 3. 状态管理层 (记忆) ====================

class PositionState(models.Model):
    """
    【策略持仓状态表】
    
    💡 为什么需要这张表？
    这是策略的"记忆体"。对应你 main() 函数里的所有状态变量。
    如果没有这张表，程序一重启，就不知道自己持有多少仓、上次加仓价是多少、止损线在哪里。
    它保证了策略的连续性。
    """
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='positions', verbose_name="所属账户")
    symbol = models.CharField("合约代码", max_length=20, db_index=True)
    
    # --- 核心持仓 ---
    units = models.IntegerField("持仓单位数", default=0, help_text="对应 position_units，0表示空仓")
    direction = models.IntegerField("持仓方向 (1多/-1空/0无)", default=0, db_index=True)
    contracts_per_unit = models.IntegerField("每单位手数", default=1, help_text="对应 contracts_per_unit")
    
    # --- 关键价格 (用于计算止损和加仓) ---
    last_add_price = models.DecimalField("上次加仓价", max_digits=12, decimal_places=2, null=True, blank=True, help_text="用于计算下一次加仓阈值")
    highest_close = models.DecimalField("持仓期最高价", max_digits=12, decimal_places=2, null=True, blank=True, help_text="多头持仓期间的最高收盘价，用于移动止损")
    lowest_close = models.DecimalField("持仓期最低价", max_digits=12, decimal_places=2, null=True, blank=True, help_text="空头持仓期间的最低收盘价，用于移动止损")
    
    # --- 挂单状态 (Pending) ---
    # 对应代码中的 pending_entry_... 变量
    # 用于处理"突破信号产生，但需等待次日开盘价开仓"的中间状态
    pending_direction = models.IntegerField("待开仓方向", default=0)
    pending_contracts = models.IntegerField("待开仓手数", default=1)
    pending_trend_factor = models.DecimalField("待开仓趋势因子", max_digits=6, decimal_places=4, default=Decimal('0'))

    last_update_time = models.DateTimeField("最后更新时间", auto_now=True, help_text="最后收到行情的时间")

        # --- 加仓配置字段 ---
    
    # 是否开启加仓逻辑
    is_add_position_enabled = models.BooleanField("开启加仓", default=True)
    
    # 加仓触发价格 (由盘前/盘后任务计算写入)
    # 例如：对于多头，这是下一个唐奇安突破点
    add_position_trigger_price = models.DecimalField("加仓触发价", max_digits=12, decimal_places=2, null=True, blank=True)
    
    # 加仓手数 (可以是固定值，也可以是计算出的值)
    add_position_volume = models.IntegerField("加仓手数", default=1)
    
    # (可选) 加仓次数限制
    current_add_count = models.IntegerField("当前加仓次数", default=0)
    max_add_count = models.IntegerField("最大加仓次数", default=3)


       # --- 移仓换月相关字段 ---
    
    # 是否开启自动移仓
    is_rollover_enabled = models.BooleanField("开启自动移仓", default=True)
    
    # 是否检测到需要移仓
    is_rollover_needed = models.BooleanField("需移仓", default=False)
    
    # 目标主力合约代码
    target_rollover_symbol = models.CharField("目标合约", max_length=20, null=True, blank=True)


    def __str__(self):
        direction_map = {1: "多", -1: "空", 0: "空仓"}
        return f"{self.symbol} - {direction_map.get(self.direction, '未知')} - {self.units}单位"

    class Meta:
        verbose_name = "策略持仓状态"
        verbose_name_plural = "策略持仓状态"
        unique_together = ('account', 'symbol')
        constraints = [
            CheckConstraint(
                check=Q(direction__in=[-1, 0, 1]),
                name='direction_must_be_minus1_0_or_1'
            ),
            CheckConstraint(
                check=Q(units__gte=0),
                name='units_must_be_non_negative'
            ),
        ]
        indexes = [
            models.Index(fields=['symbol', 'direction']),
            models.Index(fields=['account', 'units']),
        ]



class RolloverLog(models.Model):
    """
    【移仓换月日志表】
    
    💡 为什么需要这张表？
    专门记录主力合约切换的操作（例如从 rb2405 换到 rb2410）。
    记录了旧合约、新合约、换月时间和状态，方便统计移仓成本。
    """
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
        ('CANCELLED', '已取消'),
    ]
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE, related_name='rollover_logs', verbose_name="所属账户")
    old_symbol = models.CharField("旧合约", max_length=20, db_index=True)
    new_symbol = models.CharField("新合约", max_length=20, db_index=True)
    volume = models.IntegerField("手数")
    trade_time = models.DateTimeField("移仓时间", auto_now_add=True, db_index=True)
    status = models.CharField("状态", max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "移仓换月日志"
        verbose_name_plural = "移仓换月日志"
        ordering = ['-trade_time']
        indexes = [
            models.Index(fields=['account', '-trade_time']),
            models.Index(fields=['status', '-trade_time']),
        ]

    def __str__(self):
        return f"{self.old_symbol} -> {self.new_symbol} ({self.get_status_display()})"

    
# ==================== 4. 交易与绩效层 (结果) ====================

class TradeExecution(models.Model):
    """
    【交易执行明细表】
    
    💡 为什么需要这张表？
    这是最底层的"流水账"。
    相比 TradeLog，它更强调"执行细节"。
    它可以区分这笔交易是"首仓"还是"加仓"，这对于分析策略的加仓逻辑是否有效至关重要。
    """
    TRADE_TYPE_CHOICES = [
        ('ENTRY', '首次开仓'),
        ('ADD_ON', '加仓'),
        ('CLOSE_SIGNAL', '信号平仓'),
        ('STOP_LOSS', '止损平仓'),
    ]

    account = models.ForeignKey(TradingAccount, on_delete=models.PROTECT, related_name='trades', verbose_name="所属账户")
    symbol = models.CharField("合约代码", max_length=20, db_index=True)
    
    direction = models.IntegerField("方向 (1多/-1空)", default=0, db_index=True)
    trade_type = models.CharField("交易类型", max_length=20, choices=TRADE_TYPE_CHOICES, db_index=True)
    
    price = models.DecimalField("成交价格", max_digits=12, decimal_places=2)
    volume = models.IntegerField("手数")
    trade_time = models.DateTimeField("交易时间", db_index=True)
    
    # 关联信号：可以追溯到具体是哪一天的突破信号触发了这次交易
    signal = models.ForeignKey(DailyStrategySignal, on_delete=models.SET_NULL, null=True, blank=True, related_name='executions')
    trigger_price = models.DecimalField("触发价格", max_digits=12, decimal_places=2, null=True, blank=True, help_text="触发这次交易的具体价格点位")

    class Meta:
        verbose_name = "交易执行明细"
        verbose_name_plural = "交易执行明细"
        ordering = ['-trade_time']
        constraints = [
            CheckConstraint(
                check=Q(direction__in=[-1, 1]),
                name='trade_direction_must_be_minus1_or_1'
            ),
        ]
        indexes = [
            models.Index(fields=['symbol', '-trade_time']),
            models.Index(fields=['trade_type', '-trade_time']),
            models.Index(fields=['account', '-trade_time']),
        ]


class DailyPerformance(models.Model):
    """
    【每日绩效指标表】
    
    💡 为什么需要这张表？
    这是系统的"体检报告"。
    每天收盘后，根据账户权益和交易记录计算得出。
    它不记录过程，只记录结果（夏普比率、回撤、胜率），用于评估策略长期的表现。
    """
    account = models.ForeignKey(TradingAccount, on_delete=models.PROTECT, related_name='daily_perfs', verbose_name="所属账户")
    trade_date = models.DateField("交易日期", db_index=True)
    
    # --- 资金与收益 ---
    daily_equity = models.DecimalField("当日净值", max_digits=15, decimal_places=2)
    daily_return = models.DecimalField("当日收益率", max_digits=10, decimal_places=4, default=Decimal('0'))
    cumulative_return = models.DecimalField("累计收益率", max_digits=10, decimal_places=4, default=Decimal('0'))
    daily_pnl = models.DecimalField("当日盈亏金额", max_digits=15, decimal_places=2, default=Decimal('0'))

    # --- 风险调整后收益 ---
    sharpe_ratio = models.DecimalField("夏普比率(20日滚动)", max_digits=10, decimal_places=4, null=True, blank=True, help_text="衡量性价比，越高越好")
    sortino_ratio = models.DecimalField("索提诺比率(20日滚动)", max_digits=10, decimal_places=4, null=True, blank=True, help_text="只考虑下行风险的夏普比率")
    calmar_ratio = models.DecimalField("卡尔玛比率", max_digits=10, decimal_places=4, null=True, blank=True, help_text="年化收益/最大回撤，趋势策略核心指标")

    # --- 风险与回撤 ---
    max_drawdown = models.DecimalField("最大回撤", max_digits=10, decimal_places=4, default=Decimal('0'), help_text="历史最大回撤百分比")
    current_drawdown = models.DecimalField("当前回撤", max_digits=10, decimal_places=4, default=Decimal('0'), help_text="当前净值距离最高净值的回撤")
    max_drawdown_duration = models.IntegerField("最大回撤持续天数", default=0, help_text="最长的一次挨打时间")
    volatility = models.DecimalField("年化波动率", max_digits=10, decimal_places=4, null=True, blank=True)
    beta = models.DecimalField("Beta系数", max_digits=10, decimal_places=4, null=True, blank=True)

    # --- 交易统计 (滚动窗口) ---
    win_rate = models.DecimalField("胜率", max_digits=6, decimal_places=2, null=True, blank=True)
    profit_loss_ratio = models.DecimalField("盈亏比", max_digits=6, decimal_places=2, null=True, blank=True)
    trade_count = models.IntegerField("统计期内交易次数", default=0)

    class Meta:
        verbose_name = "每日绩效"
        verbose_name_plural = "每日绩效"
        unique_together = ('account', 'trade_date')
        ordering = ['trade_date']
        indexes = [
            models.Index(fields=['account', '-trade_date']),
            models.Index(fields=['-sharpe_ratio']),
            models.Index(fields=['-max_drawdown']),
        ]

    def __str__(self):
        return f"{self.account.name} - {self.trade_date} - 净值:{self.daily_equity} - 夏普:{self.sharpe_ratio}"