"""
Stock app URL configuration
"""
from rest_framework.routers import DefaultRouter
from stock.views.contract import FullContractListViewSet
from stock.views.strategyconfig import StrategyConfigViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'contracts', FullContractListViewSet, basename='contract')
router.register(r'strategy', StrategyConfigViewSet, basename='strategy')

# URL 模式
urlpatterns = router.urls
