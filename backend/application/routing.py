# -*- coding: utf-8 -*-
from django.urls import path, re_path
from application.websocketConfig import MegCenter
from opsflow.consumers import FlowMonitorConsumer

websocket_urlpatterns = [
    path('ws/<str:service_uid>/', MegCenter.as_asgi()),
    re_path(r'^ws/opsflow/execution/(?P<execution_id>\d+)/$', FlowMonitorConsumer.as_asgi()),
]
