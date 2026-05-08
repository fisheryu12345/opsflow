"""
Stock app URL configuration
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from stock.views.performance import (
    DailyEquitySnapshotViewSet,
    RollingPerformanceMetricsViewSet,
    AccountPerformanceSummaryViewSet,
    SymbolWinRateView,
    AccountCumulativeStatsView,
    DailyReturnsCalendarView,  # 日历热力图数据接口
    DrawdownCurveView  # 新增：回撤曲线数据接口
)
from stock.views.contract import FullContractListViewSet
from stock.views.dailysignal import  DailyStrategySignalViewSet
from stock.views.strategyconfig import StrategyConfigViewSet
from stock.views.position import PositionStateViewSet
from stock.views.trade_log import TradeLogViewSet, ErrorLogViewSet
from stock.views.closed_position import ClosedPositionRecordViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'contracts', FullContractListViewSet, basename='contract')
router.register(r'strategy', StrategyConfigViewSet, basename='strategy')
router.register(r'trade_log', TradeLogViewSet, basename='trade_log')
router.register(r'error_log', ErrorLogViewSet, basename='error_log')
router.register(r'daily_signals', DailyStrategySignalViewSet, basename='daily_signals')
router.register(r'position', PositionStateViewSet, basename='position')
router.register(r'closed-positions', ClosedPositionRecordViewSet, basename='closed-position')

# ==================== 绩效数据路由 ====================
router.register(r'equity-snapshots', DailyEquitySnapshotViewSet, basename='equity-snapshot')
router.register(r'rolling-metrics', RollingPerformanceMetricsViewSet, basename='rolling-metrics')
router.register(r'account-summaries', AccountPerformanceSummaryViewSet, basename='account-summary')

# 注册品种胜率统计接口（非 ModelViewSet，需手动添加）
symbol_win_rate_view = SymbolWinRateView.as_view({'get': 'list'})
cumulative_stats_view = AccountCumulativeStatsView.as_view({'get': 'list'})
daily_returns_calendar_view = DailyReturnsCalendarView.as_view({'get': 'list'})
drawdown_curve_view = DrawdownCurveView.as_view({'get': 'list'})  # 新增：回撤曲线

urlpatterns = router.urls + [
    path('symbol-win-rate/', symbol_win_rate_view, name='symbol-win-rate'),
    path('cumulative-stats/', cumulative_stats_view, name='cumulative-stats'),
    path('daily-returns-calendar/', daily_returns_calendar_view, name='daily-returns-calendar'),
    path('drawdown-curve/', drawdown_curve_view, name='drawdown-curve'),  # 新增路由
]
