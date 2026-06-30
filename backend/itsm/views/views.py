# -*- coding: utf-8 -*-
"""ITSM views - Incident, Change, ServiceRequest, Problem, ServiceCategory, SlaPolicy

CRUD + 状态转换动作 — project-scoped with multi-tenant isolation
"""

from rest_framework.decorators import action
from django.utils import timezone

from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.incident import Incident, Change, ServiceRequest, Problem, ServiceCategory, SlaPolicy
from ..serializers import (
    IncidentSerializer, IncidentCreateUpdateSerializer,
    ChangeSerializer, ChangeCreateUpdateSerializer,
    ServiceRequestSerializer,
    ProblemSerializer, ProblemCreateUpdateSerializer,
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


class IncidentViewSet(ItsmProjectViewSet):
    """事件工单管理 — project-scoped"""
    model = Incident
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    filter_fields = ['status', 'priority', 'source', 'category', 'assignee']
    search_fields = ['title', 'incident_id', 'description']
    ordering = ['-create_datetime']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return IncidentCreateUpdateSerializer
        return IncidentSerializer

    @action(methods=['POST'], detail=True)
    def assign(self, request, pk=None):
        """分派工单"""
        instance = self.get_object()
        user_id = request.data.get('user_id')
        from dvadmin.system.models import Users
        try:
            user = Users.objects.get(id=user_id)
            instance.assignee = user
            instance.status = 'assigned'
            instance.save(update_fields=['assignee', 'status'])
            return DetailResponse(data={'status': instance.status, 'assignee': user.name}, msg='分派成功')
        except Users.DoesNotExist:
            return ErrorResponse(msg='用户不存在')

    @action(methods=['POST'], detail=True)
    def resolve(self, request, pk=None):
        """解决工单"""
        instance = self.get_object()
        instance.status = 'resolved'
        instance.resolution = request.data.get('resolution', '')
        instance.resolved_at = timezone.now()
        instance.save(update_fields=['status', 'resolution', 'resolved_at'])
        return DetailResponse(msg='已解决')

    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        """关闭工单"""
        instance = self.get_object()
        instance.status = 'closed'
        instance.save(update_fields=['status'])
        return DetailResponse(msg='已关闭')


class ChangeViewSet(ItsmProjectViewSet):
    """变更申请管理 — project-scoped"""
    model = Change
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer
    filter_fields = ['status', 'change_type', 'risk_level']
    search_fields = ['title', 'change_id']
    ordering = ['-create_datetime']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ChangeCreateUpdateSerializer
        return ChangeSerializer

    @action(methods=['POST'], detail=True)
    def approve(self, request, pk=None):
        instance = self.get_object()
        instance.status = 'approved'
        instance.approval_note = request.data.get('note', '')
        instance.save(update_fields=['status', 'approval_note'])
        return DetailResponse(msg='已批准')

    @action(methods=['POST'], detail=True)
    def reject(self, request, pk=None):
        instance = self.get_object()
        instance.status = 'rejected'
        instance.approval_note = request.data.get('note', '')
        instance.save(update_fields=['status', 'approval_note'])
        return DetailResponse(msg='已驳回')


class ServiceRequestViewSet(ItsmProjectViewSet):
    """服务请求管理 — project-scoped"""
    model = ServiceRequest
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    filter_fields = ['status', 'category', 'assignee']
    search_fields = ['title', 'request_id']
    ordering = ['-create_datetime']


class ProblemViewSet(ItsmProjectViewSet):
    """问题管理 — project-scoped"""
    model = Problem
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    filter_fields = ['status', 'priority', 'known_error']
    search_fields = ['title', 'problem_id']
    ordering = ['-create_datetime']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProblemCreateUpdateSerializer
        return ProblemSerializer
