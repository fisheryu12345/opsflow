"""Volume 3: Implementation & Operations (Chapters 9-13 + Appendices)."""
from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from generate_strategy_pdf.styles import *

CHART_DIR = "charts"


def build_volume3(gen):
    """Build Volume 3: Features, Performance, K-line, Backtest, Appendices."""
    _add_chapter9(gen)
    _add_chapter10(gen)
    _add_chapter11(gen)
    _add_chapter12(gen)
    _add_chapter13(gen)
    _add_appendix_a(gen)
    _add_appendix_b(gen)
    _add_appendix_c(gen)


def _add_chapter9(gen):
    """Chapter 9: Trading Management Features."""
    gen.add_heading1("第三卷  功能实现与运维")
    gen.add_heading1("第9章  交易管理功能")

    gen.add_heading2("9.1 持仓管理")
    gen.add_body("PositionState 模型管理所有活跃持仓，关键字段如下:")
    pos_fields = [
        ["字段", "类型", "说明"],
        ["units", "0~3", "当前持仓 Unit 数"],
        ["direction", "1/-1/0", "持仓方向(多/空/无)"],
        ["stop_loss_price", "Decimal", "当前止损价(动态)"],
        ["protect_cost_enalbed", "Boolean", "保本开关(单向，永不关闭)"],
        ["highest_close", "Decimal", "持仓期间最高收盘价(双向跟踪)"],
        ["lowest_close", "Decimal", "持仓期间最低收盘价(双向跟踪)"],
        ["cost_price", "Decimal", "持仓成本价(每日从TqSDK同步)"],
        ["entry_trend_factor", "Decimal", "入场趋势因子"],
        ["entry_trend_label", "String", "入场趋势标签"],
        ["entry_atr", "Decimal", "入场 ATR"],
    ]
    gen.add_table(pos_fields, col_widths=[35*mm, 25*mm, 90*mm])

    gen.add_heading2("9.2 信号监控")
    gen.add_body("DailyStrategySignal 管理所有交易信号的完整生命周期:")
    sig_fields = [
        ["字段", "说明"],
        ["trade_type", "ENTRY / STOP_LOSS / ROLLOVER / ADD_ON"],
        ["executed_status", "PENDING -> EXECUTING -> SUCCESS / FAILED / CANCELLED"],
        ["symbol", "交易所格式(如 SHFE.rb2510)"],
        ["trade_date", "信号生成日期(unique_together: account+symbol+trade_date)"],
        ["remark", "执行备注(跳空保护/震荡行情不入场等)"],
    ]
    gen.add_table(sig_fields, col_widths=[30*mm, 120*mm])

    gen.add_body(
        "防重复机制: 同一品种、同一 trade_type、同一交易日只生成一个 PENDING 信号。"
        "若前一日信号未执行，次日不会重复生成。"
    )

    gen.add_heading2("9.3 平仓记录")
    gen.add_body("ClosedPositionRecord 保存历史平仓明细:")
    closed_fields = [
        ["字段", "说明"],
        ["pnl", "盈亏金额(正=盈利，负=亏损)"],
        ["holding_days", "持仓天数"],
        ["exit_price", "平仓价格"],
        ["entry_trend_factor/label/atr", "入场趋势快照(从 PositionState 复制)"],
        ["exit_trend_factor/label", "出场趋势状态(从信号读取)"],
        ["exit_atr", "出场 ATR(实时计算)"],
        ["max_favorable_excursion", "MFE 最大有利价格偏移"],
        ["max_adverse_excursion", "MAE 最大不利价格偏移"],
    ]
    gen.add_table(closed_fields, col_widths=[40*mm, 110*mm])

    gen.add_heading2("9.4 策略配置")
    gen.add_body("StrategyConfig 提供全局策略参数配置:")
    config_fields = [
        ["参数", "说明"],
        ["account", "关联的交易账户"],
        ["skip_choppy_entry", "V3专用: 震荡行情是否跳过开仓"],
        ["is_active", "账户是否启用策略"],
        ["product_codes", "通过 AccountContractConfig 管理激活品种"],
    ]
    gen.add_table(config_fields, col_widths=[35*mm, 115*mm])

    gen.add_heading2("9.5 合约管理")
    gen.add_body("FullContractList 维护全局合约元数据，每日自动同步:")
    contract_fields = [
        ["字段", "说明"],
        ["symbol", "交易所格式代码"],
        ["product_code", "品种代码(如 rb, MA)"],
        ["volume_multiple", "合约乘数(手 -> 吨)"],
        ["price_tick", "最小变动价位"],
        ["min_position", "交易所最小开仓手数"],
        ["is_main", "是否主力合约"],
        ["is_rollover_needed", "是否需要移仓换月"],
    ]
    gen.add_table(contract_fields, col_widths=[35*mm, 115*mm])

    gen.add_heading2("9.6 多账户系统")
    gen.add_body(
        "系统支持多账户独立运行，每个账户有独立的:\n"
        "- 信号队列(逐账户 signals，互不干扰)\n"
        "- 资金核算(三层绩效逐账户计算)\n"
        "- 策略配置(独立 skip_choppy_entry)\n"
        "- Redis 分布式锁(lock:open:{account.id}，逐账户隔离)"
    )

    gen.add_heading2("9.7 滑点统计")
    gen.add_body(
        "系统记录每次开仓和平仓的滑点(开仓价 vs 信号价/止损价差距)，"
        "并在 Dashboard 中以指标卡片和品种滑点图表展示，"
        "用于持续监控各品种的流动性状况和执行质量。"
    )

    gen.story.append(PageBreak())


def _add_chapter10(gen):
    """Chapter 10: Performance Dashboard."""
    gen.add_heading1("第10章  绩效看板")

    gen.add_heading2("10.1 三层绩效体系")
    gen.add_body("绩效数据每日收盘后自动更新，从日频快照逐层聚合到账户级总览:")

    gen.add_image("performance_hierarchy.png", width=160*mm)

    gen.add_heading2("10.2 核心指标定义")
    metrics = [
        ["指标", "层级", "计算方式", "意义"],
        ["日收益率", "L1", "(当日权益 - 前日权益) / 前日权益", "每日资金变动"],
        ["夏普比率", "L2", "(平均日收益率 - 无风险利率) / 收益率标准差 x sqrt(250)", "风险调整后收益"],
        ["索提诺比率", "L2", "同夏普但分母使用下行标准差", "只惩罚下跌波动"],
        ["波动率", "L2", "收益率标准差 x sqrt(250)", "年度化波动"],
        ["胜率", "L2", "盈利交易数 / 总交易数", "交易胜率"],
        ["盈亏比", "L2", "平均盈利 / 平均亏损", "盈亏质量"],
        ["卡玛比率", "L3", "年化收益 / 最大回撤", "回撤调整后收益"],
        ["最大回撤", "L3", "max(peak - trough) / peak", "最大损失幅度"],
        ["连续亏损", "L3", "连续亏损交易笔数", "回撤恢复能力"],
    ]
    gen.add_table(metrics, col_widths=[25*mm, 12*mm, 70*mm, 45*mm])

    gen.add_heading2("10.3 资金回撤曲线")
    gen.add_body(
        "回撤曲线使用峰值回溯算法: 每日计算累计权益的 rolling maximum (peak)，"
        "回撤 = (equity - peak) / peak。系统在 Dashboard 中展示完整的回撤曲线，"
        "标注最大回撤点和恢复时间。"
    )
    gen.add_image("equity_curve.png", width=170*mm)

    gen.add_heading2("10.4 日历热力图")
    gen.add_body(
        "日收益率以日历热力图形式展示，红色=亏损，绿色=盈利，颜色深度代表收益率绝对值。"
        "便于直观识别亏损聚集期、盈利爆发期和季节性模式。"
    )
    gen.add_image("heatmap.png", width=170*mm)

    gen.story.append(PageBreak())


def _add_chapter11(gen):
    """Chapter 11: K-line Analysis."""
    gen.add_heading1("第11章  K线分析")

    gen.add_heading2("11.1 K线买点")
    gen.add_body(
        "K线图表使用 ECharts 实现，支持以下核心功能:\n"
        "- 日线蜡烛图(开盘/收盘/最高/最低)\n"
        "- 唐奇安通道(20日最高/最低轨道)\n"
        "- MA10/20/40 均线\n"
        "- 交易标记(开仓/加仓/移仓/平仓)\n"
        "- dataZoom 拖拽缩放 + 滚轮缩放"
    )

    gen.add_heading2("11.2 K线数据扩充")
    gen.add_body("KlineData 模型经历三阶段扩充:")
    kline_fields = [
        ["阶段", "新增字段", "用途"],
        ["Phase 1", "atr_14 / atr_20", "波动率计算"],
        ["Phase 2", "ma_10 / ma_20 / ma_40", "趋势因子计算"],
        ["Phase 3", "donchian_high_20 / donchian_low_20", "通道突破判断"],
    ]
    gen.add_table(kline_fields, col_widths=[25*mm, 55*mm, 70*mm])
    gen.add_body(
        "批量指标计算通过管理命令触发，每日收盘后自动运行回填。"
    )

    gen.story.append(PageBreak())


def _add_chapter12(gen):
    """Chapter 12: Logging & Monitoring."""
    gen.add_heading1("第12章  日志监控")

    gen.add_heading2("12.1 交易日志 (TradeLog)")
    gen.add_body("TradeLog 记录所有交易操作的关键事件:")
    trade_log_fields = [
        ["字段", "说明"],
        ["function_name", "触发函数名"],
        ["symbol", "合约代码"],
        ["msg", "日志消息"],
        ["log_level", "INFO / WARNING / ERROR"],
        ["account", "关联账户"],
    ]
    gen.add_table(trade_log_fields, col_widths=[35*mm, 115*mm])

    gen.add_heading2("12.2 错误监控 (ErrorLog)")
    gen.add_body("ErrorLog 自动捕获所有系统异常并持久化存储:")
    err_fields = [
        ["字段", "说明"],
        ["function_name", "异常发生函数"],
        ["msg", "错误详情 + Traceback"],
        ["account", "关联账户(如有)"],
    ]
    gen.add_table(err_fields, col_widths=[35*mm, 115*mm])
    gen.add_body(
        "使用约定: 代码中不使用 logger.info/warning/error，统一使用 log_trade() 和 log_error() "
        "函数写入数据库，确保所有日志持久化可查。"
    )

    gen.story.append(PageBreak())


def _add_chapter13(gen):
    """Chapter 13: Backtest System."""
    gen.add_heading1("第13章  回测系统")

    gen.add_heading2("13.1 回测架构")
    gen.add_body(
        "回测系统独立于实盘，采用数据驱动引擎:\n"
        "- 基于历史 K 线数据回放\n"
        "- 独立于 TqSDK 实时连接\n"
        "- 支持参数扫描和批量回测\n"
        "- 输出完整交易记录和绩效指标"
    )

    gen.add_heading2("13.2 回测与实盘差异分析")
    gen.add_body("以下为回测与实盘的关键差异及其对绩效的影响方向:")

    bt_diff = [
        ["#", "差异", "实盘情况", "对绩效影响"],
        ["1", "MA过滤缺失", "实盘V2跳过MA过滤\n回测有过滤", "回测偏高(+3~5%胜率)"],
        ["2", "滑点处理", "回测假设0滑点\n实盘有滑点", "回测偏高"],
        ["3", "K线数据质量", "回测使用收盘价\n实盘使用实时价", "回测偏乐观"],
        ["4", "手续费", "回测可能低估\n实盘按交易所收", "回测偏高"],
        ["5", "流动性限制", "回测假设全成交\n实盘可能部分成交", "回测偏高"],
        ["6", "跳空影响", "回测忽略隔夜跳空\n实盘跳空常见", "回测偏高"],
        ["7", "主力合约切换", "回测固定合约\n实盘需移仓", "回测偏高"],
        ["8", "策略状态管理", "回测简化状态\n实盘需完整状态机", "回测偏乐观"],
    ]
    gen.add_table(bt_diff, col_widths=[8*mm, 25*mm, 40*mm, 25*mm])

    gen.add_body(
        "关键结论: 回测结果总体偏乐观，所有8项差异均导致回测绩效 >= 实盘绩效。"
        "回测主要用于策略逻辑验证和参数筛选，实盘绩效应以实际情况为准。"
        "预期实盘较回测低 3~8%(年化收益)，差异主要通过实时绩效监控动态评估。"
    )

    gen.add_heading2("13.3 回测使用指南")
    gen.add_body(
        "运行步骤: 1) 配置回测参数(品种/时间范围/初始资金) -> "
        "2) 选择策略(V2/V3/海龟原版/MA10斜率/双均线) -> "
        "3) 执行回测 -> 4) 查看输出(逐笔交易/曲线/绩效指标)。\n"
        "支持参数扫描模式: 指定参数范围后批量运行，对比不同参数组合的绩效表现。"
    )

    gen.story.append(PageBreak())


def _add_appendix_a(gen):
    """Appendix A: Parameter Quick Reference."""
    gen.add_heading1("附录A  关键参数速查表")

    params = [
        ["参数", "值", "所属模块", "作用"],
        ["POSITION_RISK_BASE_AMOUNT", "4,000", "config_loader", "每 Unit 风险基数(元)"],
        ["POSITION_RISK_MULTIPLIER", "2", "config_loader", "止损距离 = 2 x ATR"],
        ["POSITION_MAX_UNITS", "3", "config_loader", "单品种最大持仓 Unit"],
        ["PROTECT_COST_ENABLED_RATIO", "2.5", "config_loader", "保本触发倍数"],
        ["GAP_PROTECTION_RATIO", "1.5", "config_loader", "跳空保护倍数"],
        ["TIMEOUT_SECONDS", "60", "config_loader", "订单超时(秒)"],
        ["TREND_GAP_LIMIT", "0.03", "indicators", "趋势因子封顶间距"],
        ["TREND_FACTOR_MAX", "0.5", "indicators", "趋势因子最大值"],
        ["TREND_LABEL_STRONG_RATIO", "0.80", "indicators", "强趋势阈值"],
        ["TREND_LABEL_WEAK_RATIO", "0.30", "indicators", "弱趋势阈值"],
        ["skip_choppy_entry", "False/True", "StrategyConfig", "V3震荡过滤开关"],
    ]
    gen.add_table(params, col_widths=[40*mm, 25*mm, 30*mm, 55*mm])

    gen.story.append(PageBreak())


def _add_appendix_b(gen):
    """Appendix B: Operation Manual."""
    gen.add_heading1("附录B  实盘操作手册")

    gen.add_heading2("B.1 每日操作流程")
    gen.add_body(
        "09:00 — 检查服务器运行状态(进程/网络/TqSDK连接)\n"
        "09:02 — 开盘任务自动执行，检查邮件报告(信号执行结果)\n"
        "14:55 — 临收盘止损自动执行\n"
        "15:02 — 收盘计算自动执行，检查邮件报告(当日信号/绩效)\n"
        "15:30 — 检查 ErrorLog 确认无异常\n"
        "21:00 — 夜盘开盘前检查(同09:02)"
    )

    gen.add_heading2("B.2 监控清单")
    gen.add_body(
        "每日必查:\n"
        "1. 开盘任务邮件 — 确认信号执行情况\n"
        "2. 收盘任务邮件 — 确认新信号、止损更新、绩效指标\n"
        "3. ErrorLog — 确认无异常报错\n\n"
        "每周检查:\n"
        "1. 持仓盈亏与Dashboard一致性\n"
        "2. 滑点统计指标\n"
        "3. 策略配置是否与预期一致\n\n"
        "每月检查:\n"
        "1. 绩效趋势: 夏普/胜率/盈亏比变化\n"
        "2. 回撤: 最大回撤是否超过预期范围\n"
        "3. 参数: 是否需要调整风险参数"
    )

    gen.add_heading2("B.3 异常处理")
    gen.add_body(
        "常见异常与处理:\n"
        "1. 开盘任务未执行: 检查网络 -> 检查Redis锁 -> 手动触发\n"
        "2. 信号未按预期执行: 检查信号状态 -> 检查跳空保护 -> 检查交易时间\n"
        "3. 持仓与实际不符: 检查 TqSDK 连接 -> 检查 TargetPosTask -> 手动调整\n"
        "4. 服务器宕机: 重启 -> 检查任务状态 -> 手动补执行\n"
        "5. 主力合约未及时切换: 手动触发 sync_contract_list"
    )

    gen.story.append(PageBreak())


def _add_appendix_c(gen):
    """Appendix C: Glossary."""
    gen.add_heading1("附录C  术语表")

    terms = [
        ["术语", "英文", "说明"],
        ["ATR", "Average True Range", "平均真实波幅，20日周期，衡量波动率"],
        ["Unit", "—", "风险单位，基于ATR计算的标准化仓位"],
        ["唐奇安通道", "Donchian Channel", "N日最高价/最低价轨道，突破信号"],
        ["MFE", "Max Favorable Excursion", "持仓期间最大有利价格偏移"],
        ["MAE", "Max Adverse Excursion", "持仓期间最大不利价格偏移"],
        ["趋势因子", "Trend Factor", "基于MA排列密度的趋势强度量化值 [0, 0.5]"],
        ["trend_strength", "Trend Strength", "均线间距归一化值 [0%, 100%]"],
        ["保本兜底", "Breakeven Protection", "盈利超过阈值后确保不亏损的机制"],
        ["两步开仓", "Two-Step Opening", "应对最小开仓手数限制的合规策略"],
        ["跳空保护", "Gap Protection", "防止隔夜跳空追高/追低的风险控制"],
        ["金字塔加仓", "Pyramid Adding", "分梯度增加仓位的策略"],
        ["移仓换月", "Rollover", "主力合约切换时平旧开新"],
        ["三层绩效", "3-Tier Performance", "L1日权益/L2滚动指标/L3账户总览"],
        ["TargetPosTask", "—", "TqSDK目标持仓任务(自动报单/追单/撤单)"],
    ]
    gen.add_table(terms, col_widths=[28*mm, 38*mm, 84*mm])

    gen.story.append(PageBreak())
