# -*- coding: utf-8 -*-
"""URL configuration for integration app

路由前缀: /api/integration/

遵循规范: SimpleRouter + kebab-case 路径命名
"""

from django.urls import path, include
from rest_framework import routers

from .views.connector import ConnectorDefinitionViewSet, ConnectorInstanceViewSet
from .views.credential import ConnectorCredentialViewSet
from .views.integration_log import IntegrationLogViewSet

router = routers.SimpleRouter()
router.register(r'connector-definitions', ConnectorDefinitionViewSet)
router.register(r'connector-instances', ConnectorInstanceViewSet)
router.register(r'credentials', ConnectorCredentialViewSet)
router.register(r'call-logs', IntegrationLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
