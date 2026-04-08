"""
Stock app URL configuration
"""
from rest_framework.routers import DefaultRouter
from stock.views.contract import FullContractListViewSet

# 创建路由器
router = DefaultRouter()

# 注册视图集
router.register(r'contracts', FullContractListViewSet, basename='contract')

# URL 模式
urlpatterns = router.urls
