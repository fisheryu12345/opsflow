# -*- coding: utf-8 -*-
"""URL configuration for CMDB app

路由前缀: /api/cmdb/
"""

from django.urls import path, include
from rest_framework import routers

from .views.model_manage import ModelDefinitionViewSet, ModelFieldViewSet
from .views.biz import BizViewSet, SetViewSet, ModuleViewSet
from .views.host import HostViewSet
from .views.topology import TopologyViewSet

router = routers.SimpleRouter()
router.register(r'model-definitions', ModelDefinitionViewSet)
router.register(r'model-fields', ModelFieldViewSet)
router.register(r'bizs', BizViewSet, basename='biz')
router.register(r'sets', SetViewSet, basename='set')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'hosts', HostViewSet, basename='host')
router.register(r'topology', TopologyViewSet, basename='topology')

urlpatterns = [
    path('', include(router.urls)),
]
