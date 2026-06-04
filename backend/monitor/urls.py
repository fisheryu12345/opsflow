# -*- coding: utf-8 -*-
"""URL configuration for Monitor app

路由前缀: /api/monitor/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import AlertRuleViewSet, AlertEventViewSet, MonitorTargetViewSet
from .services.grafana_webhook import grafana_alert_webhook

router = routers.SimpleRouter()
router.register(r'alert-rules', AlertRuleViewSet)
router.register(r'alert-events', AlertEventViewSet)
router.register(r'targets', MonitorTargetViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('grafana-webhook/', grafana_alert_webhook, name='grafana-webhook'),
]
