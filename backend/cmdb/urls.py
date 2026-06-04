# -*- coding: utf-8 -*-
"""URL configuration for CMDB app

路由前缀: /api/cmdb/
"""

from django.urls import path, include
from rest_framework import routers

from .views.classification import ClassificationViewSet
from .views.model_manage import ModelDefinitionViewSet, ModelFieldViewSet
from .views.attribute_group import AttributeGroupViewSet
from .views.association import (
    AssociationTypeViewSet,
    ModelAssociationViewSet,
    InstanceAssociationViewSet,
)
from .views.object_unique import ObjectUniqueViewSet
from .views.mainline_topo import MainlineTopoViewSet
from .views.instance import DynamicInstanceViewSet
from .views.topology import TopologyViewSet

router = routers.SimpleRouter()
router.register(r'classifications', ClassificationViewSet)
router.register(r'model-definitions', ModelDefinitionViewSet)
router.register(r'model-fields', ModelFieldViewSet)
router.register(r'attribute-groups', AttributeGroupViewSet)
router.register(r'association-types', AssociationTypeViewSet)
router.register(r'model-associations', ModelAssociationViewSet)
router.register(r'instance-associations', InstanceAssociationViewSet,
                basename='instance-association')
router.register(r'object-uniques', ObjectUniqueViewSet)
router.register(r'mainline-topos', MainlineTopoViewSet)
router.register(r'topology', TopologyViewSet, basename='topology')

urlpatterns = [
    path('', include(router.urls)),

    # 动态实例路由：/api/cmdb/instances/{model_code}/
    path('instances/<str:model_code>/',
         DynamicInstanceViewSet.as_view({
             'get': 'list',
             'post': 'create',
         })),
    path('instances/<str:model_code>/<str:pk>/',
         DynamicInstanceViewSet.as_view({
             'get': 'retrieve',
             'put': 'update',
             'patch': 'partial_update',
             'delete': 'destroy',
         })),
]
