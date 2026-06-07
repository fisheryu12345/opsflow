"""Volume 2: Strategy Logic Details (Chapters 4-8)."""
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from generate_strategy_pdf.styles import *

CHART_DIR = "charts"


def build_volume2(gen):
    """Build Volume 2: V2 Flow, V3 Diff, Trend Factor, Stop Loss, Risk Analysis."""
    _add_chapter4(gen)
    _add_chapter5(gen)
    _add_chapter6(gen)
    _add_chapter7(gen)
    _add_chapter8(gen)


def _add_chapter4(gen):
    """Chapter 4: HFT V2 Complete Flow."""
    gen.add_heading1("第二卷  策略逻辑详解")
    gen.add_heading1("第4章  海龟增强V2交易全流程")

    gen.add_heading2("4.1 开仓逻辑 (ENTRY)")

    gen.add_heading3("4.1.1 触发条件")
    gen.add_body(
        "入场信号基于20日唐奇安通道突破。核心原则: 入场只看通道突破，不参考MA排列方向。"
        "MA10/20/40排列仅用于趋势因子计算，进而动态调整止损距离。"
    )
    gen.add_body(
        "breakout = close > max(high[-20:-1]) -> 做多 (direction=1)\n"
        "breakout = close < min(low[-20:-1])  -> 做空 (direction=-1)\n\n"
        "关键规则: 使用前20日高低点(不包含今日)、收盘后计算次日开盘执行、"
        "信号生成时检查 units=0 且不存在 PENDING 的 ENTRY 信号。"
    )

    gen.add_heading3("4.1.2 仓位计算 (Unit Lots)")
    gen.add_body(
        "unit_lots = POSITION_RISK_BASE_AMOUNT / (ATR x POSITION_RISK_MULTIPLIER x volume_multiple)\n"
        "         = 4000 / (ATR x 2 x 合约乘数)\n"
        "示例: 螺纹钢 ATR=50, 乘数=10 -> unit_lots = 4000 / (50x2x10) = 4手/Unit\n"
        "最大持仓 = 3 Unit x 4手 = 12手, 最大风险 = 3 x 4,000 = 12,000元"
    )

    gen.add_heading3("4.1.3 跳空保护")
    gen.add_body(
        "gap_ratio = |last_price - pre_close| / ATR\n"
        "当 gap_ratio > 1.5 x ATR 时，禁止开仓，信号状态设为 CANCELLED(备注: 跳空保护)。"
    )

    gen.add_heading3("4.1.4 两步开仓")
    gen.add_body(
        "当 planned_volume < min_position(交易所最小开仓手数) 时:\n"
        "第1步: 开立 min_position 手(满足交易所要求)\n"
        "第2步: 立即平仓 (min_position - planned_volume) 手\n"
        "结果: 最终持仓 = planned_volume 手，合规且达到目标"
    )

    gen.add_heading2("4.2 平仓逻辑 (STOP_LOSS)")
    gen.add_body("系统通过三重保险确保止损执行:")

    stop_types = [
        ["检查时机", "触发条件", "执行方式"],
        ["15:02 收盘后", "收盘价击穿止损价", "生成 STOP_LOSS 信号，次日开盘执行"],
        ["14:55 临收盘", "最新价击穿止损价(实时重算)", "立即市价平仓(紧急风控)"],
        ["09:02/21:02 开盘", "执行 PENDING 的 STOP_LOSS", "TargetPosTask 平仓"],
    ]
    gen.add_table(stop_types, col_widths=[35*mm, 60*mm, 65*mm])

    gen.add_body(
        "平仓趋势记录: 每次平仓时，ClosedPositionRecord 中写入入场趋势快照(entry_trend_factor/label/atr，"
        "从PositionState直接复制)、出场趋势状态(exit_trend_factor/label，从信号读取)、"
        "出场ATR(实时计算)、以及MFE/MAE(持仓期间的最高/最低价与成本价之差)。"
    )

    gen.add_heading2("4.3 金字塔加仓 (ADD_ON)")
    gen.add_body("加仓只检查 units in {1, 2} 的持仓，units=3 时不再加仓。")

    # Unit 1 add on table
    gen.add_heading3("4.3.1 当前1 Unit (基准价 = last_add_price)")
    add1 = [
        ["方向", "触发条件", "加仓数", "加仓后总Unit"],
        ["多头", "涨超 1.0 x ATR", "+2 (直接满仓)", "3"],
        ["多头", "涨超 0.5 x ATR", "+1", "2"],
        ["空头", "跌超 1.0 x ATR", "+2 (直接满仓)", "3"],
        ["空头", "跌超 0.5 x ATR", "+1", "2"],
    ]
    gen.add_table(add1, col_widths=[25*mm, 35*mm, 35*mm, 30*mm])

    gen.add_heading3("4.3.2 当前2 Unit (基准价 = first_open_price)")
    add2 = [
        ["方向", "触发条件", "加仓数", "加仓后总Unit"],
        ["多头", "从first_open_price累计涨超 1.0 x ATR", "+1", "3"],
        ["空头", "从first_open_price累计跌超 1.0 x ATR", "+1", "3"],
    ]
    gen.add_table(add2, col_widths=[25*mm, [55*mm, 20*mm, 30*mm][0], 20*mm, 30*mm])

    gen.add_body(
        "安全截断: units_current + add_units > 3 时, add_units = 3 - units_current\n"
        "防重复: 同一品种存在未执行的 ADD_ON 信号(PENDING)时跳过。"
    )

    gen.add_image("price_diagram.png", width=150*mm)
    gen.add_body(
        "价格坐标示例(多头): 开仓P0=5000 -> 涨超0.5xATR(price>=5020)加1Unit到总2 -> "
        "涨超1.0xATR(price>=5040)加2Unit直接满仓或从2Unit再+1Unit到满仓。"
    )

    gen.add_heading2("4.4 移仓换月 (ROLLOVER)")
    gen.add_body(
        "触发条件: sync_contract_list_from_tqsdk() 发现主力合约变更，标记 is_rollover_needed=True.\n"
        "操作流程: 平旧合约(TargetPosTask=0) -> 开新合约(同方向同手数) -> "
        "基于新合约20日历史数据初始化highest/lowest/止损价 -> 删除旧PositionState，创建新的。"
    )

    gen.add_heading2("4.5 信号状态流转")
    gen.add_body(
        "系统定义四类信号: ENTRY(开仓)、STOP_LOSS(止损)、ROLLOVER(移仓)、ADD_ON(加仓)。"
        "每个信号独立流转:"
    )
    gen.add_image("signal_state.png", width=150*mm)

    signal_states = [
        ["状态", "含义", "转换条件"],
        ["PENDING", "待执行", "初始状态，可跨日保留"],
        ["EXECUTING", "执行中", "开盘任务 pickup 后设置"],
        ["SUCCESS", "执行成功", "成交确认"],
        ["FAILED", "执行失败", "成交失败/超时"],
        ["CANCELLED", "已取消", "条件不满足(跳空/震荡/超限)"],
    ]
    gen.add_table(signal_states, col_widths=[30*mm, 30*mm, 100*mm])

    gen.add_heading2("4.6 执行优先级")
    gen.add_body(
        "开盘任务按四级优先级处理信号队列:\n"
        "1. STOP_LOSS (最高) — 止损平仓，控制风险\n"
        "2. ENTRY (次高) — 趋势开仓，捕捉机会\n"
        "3. ROLLOVER (中等) — 移仓换月，保持持仓\n"
        "4. ADD_ON (最低) — 金字塔加仓，扩大盈利"
    )
    gen.add_body(
        "设计原理: 止损优先级最高，防止加仓和止损冲突。若某品种同时触发止损和加仓，"
        "先平后开，避免持仓方向混乱。"
    )

    gen.story.append(PageBreak())


def _add_chapter5(gen):
    """Chapter 5: HFT V3 Differences."""
    gen.add_heading1("第5章  海龟增强V3差异说明")

    gen.add_heading2("5.1 V3 与 V2 的唯一差异")
    gen.add_body("V3 与 V2 仅有以下一处差异:")

    v3_diff = [
        ["场景", "V2", "V3"],
        ["趋势标签为 choppy/neutral", "正常开仓", "放弃开仓"],
        ["其余标签(strong_bull/weak_bull等)", "正常开仓", "正常开仓"],
        ["持仓止损、加仓、移仓逻辑", "同 V2", "完全一致"],
    ]
    gen.add_table(v3_diff, col_widths=[50*mm, 50*mm, 50*mm])

    gen.add_body(
        "即: V3 = V2 + 震荡行情不开仓。其余所有逻辑(入场条件、仓位计算、加仓规则、"
        "止损跟踪、移仓流程、信号流转、执行优先级)均与 V2 相同。"
    )

    gen.add_heading2("5.2 震荡过滤实现")
    gen.add_body(
        "在 execute_entry_order() 中，is_trading 检查之后、ATR 计算之前:\n"
        "if config.skip_choppy_entry and signal.trend_label in ('choppy', 'neutral'):\n"
        "    signal.executed_status = 'CANCELLED'\n"
        "    signal.remark = '震荡行情不入场'\n"
        "通过 StrategyConfig.skip_choppy_entry 字段控制。V3=True, V2=False。"
    )

    gen.add_heading2("5.3 A/B 验证设计")
    gen.add_body(
        "V2 和 V3 可在不同账户中并行运行，直接对比震荡行情开仓与不开仓的长期绩效差异。"
        "由于共享同一套代码库，差异仅在于 skip_choppy_entry 配置项，"
        "确保了比较结果的归因清晰。"
    )

    trend_filters = [
        ["趋势标签", "V2 (skip_choppy_entry=False)", "V3 (skip_choppy_entry=True)"],
        ["strong_bull / strong_bear", "正常开仓", "正常开仓"],
        ["weak_bull / weak_bear", "正常开仓", "正常开仓"],
        ["choppy / neutral", "正常开仓", "取消(备注: 震荡行情不入场)"],
    ]
    gen.add_table(trend_filters, col_widths=[40*mm, 55*mm, 55*mm])

    gen.story.append(PageBreak())


def _add_chapter6(gen):
    """Chapter 6: Trend Factor System."""
    gen.add_heading1("第6章  趋势因子指标体系")

    gen.add_heading2("6.1 计算公式")
    gen.add_body(
        "趋势因子(trend_factor)基于 MA10/MA20/MA40 的排列密度，通过均线间距线性映射计算:"
    )
    gen.add_body(
        "gap_10_20 = |MA10 - MA20| / |MA20|\n"
        "gap_20_40 = |MA20 - MA40| / |MA20|\n"
        "max_gap = max(gap_10_20, gap_20_40)\n"
        "trend_strength = min(max_gap / TREND_GAP_LIMIT, 1.0)\n"
        "trend_factor = round(trend_strength x TREND_FACTOR_MAX, 3)\n\n"
        "TREND_GAP_LIMIT = 0.03 (3%), TREND_FACTOR_MAX = 0.5"
    )

    gen.add_heading2("6.2 MA排列分类")
    ma_class = [
        ["均线排列", "trend_strength", "趋势标签", "trend_factor", "止损倍数"],
        ["MA10>MA20>MA40", ">= 80%", "strong_bull", "0.4~0.5", "2.8~3.0 ATR"],
        ["MA10>MA20>MA40", "30%~80%", "weak_bull", "0.15~0.4", "2.3~2.8 ATR"],
        ["MA10>MA20>MA40", "< 30%", "choppy", "0.0", "2.0 ATR"],
        ["MA10<MA20<MA40", ">= 80%", "strong_bear", "0.4~0.5", "2.8~3.0 ATR"],
        ["MA10<MA20<MA40", "30%~80%", "weak_bear", "0.15~0.4", "2.3~2.8 ATR"],
        ["交叉/混乱", "—", "choppy", "0.0", "2.0 ATR"],
    ]
    gen.add_table(ma_class, col_widths=[35*mm, 25*mm, 25*mm, 25*mm, 40*mm])

    gen.add_heading2("6.3 连续映射机制")
    gen.add_body(
        "与传统的离散等级不同，趋势因子采用连续映射: 均线间距从0到3%线性映射到 trend_factor [0, 0.5]，"
        "止损倍数随之连续变化 [2.0, 3.0] ATR。均线间距超过3%后封顶。"
    )
    gen.add_image("mapping_curve.png", width=150*mm)

    gen.add_heading2("6.4 参数调整影响")
    gen.add_body(
        "TREND_GAP_LIMIT 控制趋势强度的灵敏度: 值越小，相同均线间距下的 trend_strength 越高。\n"
        "TREND_FACTOR_MAX 控制趋势因子对止损的最大影响幅度: 值越大，强趋势时止损放宽越多。\n"
        "这两个参数独立可调，互不耦合。"
    )

    gen.story.append(PageBreak())


def _add_chapter7(gen):
    """Chapter 7: Stop Loss System."""
    gen.add_heading1("第7章  止损系统设计")

    gen.add_heading2("7.1 动态跟踪止损")
    gen.add_body("动态止损是止损体系的核心，价格向有利方向移动时跟踪调整:")

    gen.add_body(
        "多头: stop_loss = highest_close - 2 x (1 + factor) x ATR\n"
        "空头: stop_loss = lowest_close + 2 x (1 + factor) x ATR\n\n"
        "特性: 多头止损只升不降(基于highest_close)，空头止损只降不升(基于lowest_close)。"
    )

    factor_table = [
        ["factor", "止损倍数", "特性", "适用场景"],
        ["0.0", "2.0 ATR", "止损收紧", "震荡/无趋势"],
        ["0.25", "2.5 ATR", "中等", "弱趋势"],
        ["0.5", "3.0 ATR", "止损放宽，给足空间", "强趋势"],
    ]
    gen.add_table(factor_table, col_widths=[25*mm, 30*mm, 40*mm, 60*mm])

    gen.add_heading2("7.2 保本兜底")
    gen.add_body(
        "保本是动态止损的安全垫，在市场波动突然加大时保护盈利:\n"
        "触发条件: 盈利 > 2.5 x ATR -> protect_cost_enabled = True (单向开关，永不关闭)\n"
        "保本价: 多头 = 成本价 + tick x 1; 空头 = 成本价 - tick x 1\n"
        "最终止损: 多头 = max(动态止损, 保本价); 空头 = min(动态止损, 保本价)"
    )
    gen.add_image("stop_loss.png", width=170*mm)

    gen.add_heading2("7.3 止损示例(多头)")
    stop_example = [
        ["收盘价", "highest", "动态止损", "盈利", "保本状态", "最终止损"],
        ["100", "100", "94", "0", "未触发", "94"],
        ["106", "106", "100", "6", "未触发(6<7.5)", "100"],
        ["108", "108", "102", "8", "触发(8>7.5)", "102(动态>保本)"],
        ["120", "120", "114", "20", "已启用", "114(继续跟踪)"],
        ["ATR跳至12", "120", "96", "20", "已启用", "101(保本兜底)"],
    ]
    gen.add_table(stop_example, col_widths=[25*mm, 25*mm, 30*mm, 20*mm, 30*mm, 30*mm])

    gen.add_heading2("7.4 双向极值跟踪")
    gen.add_body(
        "update_all_positions_high_low_price() 双向跟踪最高价和最低价(原逻辑:多头只更新最高价,空头只更新最低价):\n"
        "if 最新价 > highest_close -> 更新最高价\n"
        "if 最新价 < lowest_close -> 更新最低价\n\n"
        "这对止损逻辑无影响(多头止损只用highest_close，空头只用lowest_close)，"
        "主要用于平仓时的 MFE/MAE 完整计算。"
    )

    gen.story.append(PageBreak())


def _add_chapter8(gen):
    """Chapter 8: Risk Analysis."""
    gen.add_heading1("第8章  实盘风险分析")

    gen.add_heading2("8.1 三层风控体系")
    gen.add_body("风控覆盖交易全生命周期:")

    risk_layers = [
        ["阶段", "规则", "实现"],
        ["事前风控", "最大持仓3 Unit", "POSITION_MAX_UNITS"],
        ["", "最小开仓手数检查", "check_min_position_requirement + 两步开仓"],
        ["", "跳空保护", "gap > 1.5xATR 跳过开仓"],
        ["", "非交易日不交易", "skip_if_not_trade_day"],
        ["", "信号防重复", "同品种同类只生成一个 PENDING 信号"],
        ["事中风控", "订单超时", "wait_for_target_position 60秒超时"],
        ["", "持仓超限取消加仓", "projected_units > 3 取消"],
        ["", "盘中击穿止损", "14:55 紧急平仓任务"],
        ["", "交易时间检查", "is_trading() 合约交易状态"],
        ["事后风控", "三层绩效监控", "日权益/滚动指标/账户总览"],
        ["", "邮件日报", "信号报告 + 执行报告"],
        ["", "错误日志", "ErrorLog / TradeLog"],
    ]
    gen.add_table(risk_layers, col_widths=[25*mm, 45*mm, 80*mm])

    gen.add_heading2("8.2 关键风险场景")
    gen.add_body("实盘操作中需重点关注以下风险场景:")

    risk_scenes = [
        ["风险场景", "类型", "缓解措施"],
        ["隔夜跳空开仓", "固有风险", "跳空保护(gap > 1.5xATR 跳过)"],
        ["涨跌停无法平仓", "固有风险", "14:55 提前检查 + 次日开盘继续处理"],
        ["主力合约切换延迟", "操作风险", "sync_contract_list 每日自动检测"],
        ["交易所停盘/休市", "固有风险", "skip_if_not_trade_day + 日历检查"],
        ["服务器宕机/断网", "操作风险", "Redis锁防重复 + 邮件通知"],
        ["TqSDK 连接异常", "第三方风险", "异常捕获 + ErrorLog 记录"],
        ["参数配置错误", "操作风险", "配置备份 + 启动验证"],
        ["策略过拟合", "模型风险", "A/B验证(V2 vs V3)对比"],
        ["盘中临时暂停交易", "政策风险", "临收盘止损作为最后防线"],
        ["极端行情波动率暴增", "固有风险", "ATR自适应仓位 + 保本兜底"],
    ]
    gen.add_table(risk_scenes, col_widths=[40*mm, 25*mm, 85*mm])

    gen.story.append(PageBreak())
