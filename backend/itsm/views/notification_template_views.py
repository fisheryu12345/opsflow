# -*- coding: utf-8 -*-
"""NotificationTemplate CRUD — project-scoped with multi-tenant isolation"""

from ..models import NotificationTemplate
from ..serializers.notification_template import NotificationTemplateSerializer
from .workflow_views import ItsmProjectViewSet


class NotificationTemplateViewSet(ItsmProjectViewSet):
    """通知模板 CRUD — project-scoped"""
    model = NotificationTemplate
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    filter_fields = ['is_active']
    search_fields = ['name']
    ordering = ['-create_datetime']
