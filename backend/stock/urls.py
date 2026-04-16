"""
Stock app URL configuration
"""
from rest_framework.routers import DefaultRouter
from stock.views.contract import FullContractListViewSet
from stock.views.strategyconfig import StrategyConfigViewSet
from stock.views.trade_log import TradeLogViewSet, ErrorLogViewSet
from stock.views.dailysignal import DailyStrategySignalViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'contracts', FullContractListViewSet, basename='contract')
router.register(r'strategy', StrategyConfigViewSet, basename='strategy')
router.register(r'trade_log', TradeLogViewSet, basename='trade_log')
router.register(r'error_log', ErrorLogViewSet, basename='error_log')
router.register(r'daily_signals', DailyStrategySignalViewSet, basename='daily_signals')

# URL 模式
urlpatterns = router.urls
