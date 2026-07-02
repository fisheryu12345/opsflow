# -*- coding: utf-8 -*-
"""
@Remark: 通用模块 URL 路由
"""
from django.urls import path
from rest_framework import routers

from common.views.operation_log import OperationLogViewSet
from common.views.file_list import FileViewSet
from common.views.login_log import LoginLogViewSet
from common.views.message_center import MessageCenterViewSet
from common.views.system_config import SystemConfigViewSet
from common.views.language import LanguageView

common_router = routers.SimpleRouter()
common_router.register(r'operation_log', OperationLogViewSet)
common_router.register(r'file', FileViewSet)
common_router.register(r'system_config', SystemConfigViewSet)
common_router.register(r'message_center', MessageCenterViewSet)

urlpatterns = [
    path('system_config/save_content/', SystemConfigViewSet.as_view({'put': 'save_content'})),
    path('system_config/get_association_table/', SystemConfigViewSet.as_view({'get': 'get_association_table'})),
    path('system_config/get_table_data/<int:pk>/', SystemConfigViewSet.as_view({'get': 'get_table_data'})),
    path('system_config/get_relation_info/', SystemConfigViewSet.as_view({'get': 'get_relation_info'})),
    path('login_log/stats/', LoginLogViewSet.as_view({'get': 'stats'})),
    path('login_log/', LoginLogViewSet.as_view({'get': 'list'})),
    path('login_log/<int:pk>/', LoginLogViewSet.as_view({'get': 'retrieve'})),
    path('language/', LanguageView.as_view()),
]
urlpatterns += common_router.urls
