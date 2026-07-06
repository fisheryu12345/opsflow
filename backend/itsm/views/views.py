# -*- coding: utf-8 -*-
"""ITSM views - ServiceCategory, SlaPolicy

CRUD — project-scoped with multi-tenant isolation
"""

from ..models import ServiceCategory, SlaPolicy
from ..serializers import (
    ServiceCategorySerializer, ServiceCategoryCreateUpdateSerializer,
    SlaPolicySerializer,
)
from .workflow_views import ItsmProjectViewSet


class ServiceCategoryViewSet(ItsmProjectViewSet):
    """服务分类 CRUD — project-scoped"""
    model = ServiceCategory
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    filter_fields = ['is_active', 'parent']
    search_fields = ['name', 'code']
    ordering = ['sort_order', 'name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ServiceCategoryCreateUpdateSerializer
        return ServiceCategorySerializer


class SlaPolicyViewSet(ItsmProjectViewSet):
    """SLA 策略 CRUD — project-scoped"""
    model = SlaPolicy
    queryset = SlaPolicy.objects.all()
    serializer_class = SlaPolicySerializer
    filter_fields = ['priority', 'is_active']
    ordering = ['priority']
