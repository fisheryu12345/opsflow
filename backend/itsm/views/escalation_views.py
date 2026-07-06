# -*- coding: utf-8 -*-
"""Escalation views — CRUD 升级级别管理"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from itsm.models import EscalationLevel
from itsm.serializers.escalation import EscalationLevelSerializer


class EscalationLevelViewSet(viewsets.ModelViewSet):
    """升级级别 CRUD（全局配置，非项目隔离）"""
    queryset = EscalationLevel.objects.all()
    serializer_class = EscalationLevelSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name']
    ordering = ['level']
