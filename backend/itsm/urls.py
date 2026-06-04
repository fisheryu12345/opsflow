# -*- coding: utf-8 -*-
"""URL configuration for ITSM app

路由前缀: /api/itsm/
"""

from django.urls import path, include
from rest_framework import routers

from .views.views import (
    ServiceCategoryViewSet, SlaPolicyViewSet,
    IncidentViewSet, ChangeViewSet,
    ServiceRequestViewSet, ProblemViewSet,
)

router = routers.SimpleRouter()
router.register(r'service-categories', ServiceCategoryViewSet)
router.register(r'sla-policies', SlaPolicyViewSet)
router.register(r'incidents', IncidentViewSet)
router.register(r'changes', ChangeViewSet)
router.register(r'service-requests', ServiceRequestViewSet)
router.register(r'problems', ProblemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
