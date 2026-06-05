# -*- coding: utf-8 -*-
"""URL configuration for Monitor app

路由前缀: /api/monitor/
"""

from django.urls import path, include
from rest_framework import routers

from .views import (
    MonitorStrategyViewSet, MonitorItemViewSet,
    AlertEventViewSet, AlertViewSet,
    NotifyGroupViewSet, DutyPlanViewSet, DutyArrangeViewSet,
    AlertAssignGroupViewSet, ActionPluginViewSet,
    ShieldPlanViewSet, CollectConfigViewSet,
    DashboardViewSet,
)
from .services.webhook_receivers import prometheus_webhook, grafana_webhook, custom_push

router = routers.SimpleRouter()
router.register(r'strategies', MonitorStrategyViewSet)
router.register(r'items', MonitorItemViewSet)
router.register(r'alert-events', AlertEventViewSet)
router.register(r'alerts', AlertViewSet)
router.register(r'notify-groups', NotifyGroupViewSet)
router.register(r'duty-plans', DutyPlanViewSet)
router.register(r'duty-arranges', DutyArrangeViewSet)
router.register(r'assign-groups', AlertAssignGroupViewSet)
router.register(r'action-plugins', ActionPluginViewSet)
router.register(r'shield-plans', ShieldPlanViewSet)
router.register(r'collect-configs', CollectConfigViewSet)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('', include(router.urls)),
    # Webhook 接收端点 (免 CSRF)
    path('webhook/prometheus/', prometheus_webhook, name='monitor-webhook-prometheus'),
    path('webhook/grafana/', grafana_webhook, name='monitor-webhook-grafana'),
    path('webhook/custom/<str:code>/', custom_push, name='monitor-webhook-custom'),
]
