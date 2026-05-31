import datetime

from django.db import transaction
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from dvadmin.system.models import Role, Menu
from dvadmin.utils.json_response import SuccessResponse, ErrorResponse
from iam.models import PermissionRequest, UserDirectPermission
from iam.serializers import (
    PermissionRequestSerializer,
    PermissionRequestCreateSerializer,
    PermissionRequestReviewSerializer,
    UserDirectPermissionSerializer,
)


class PermissionRequestViewSet(mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.ListModelMixin,
                               viewsets.GenericViewSet):
    queryset = PermissionRequest.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PermissionRequestCreateSerializer
        return PermissionRequestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(user=user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        request_type_filter = self.request.query_params.get('request_type')
        if request_type_filter:
            qs = qs.filter(request_type=request_type_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        permission_request = self.get_object()
        if request.user.is_superuser:
            if permission_request.status != 'pending':
                return ErrorResponse(msg='当前状态不允许审批')
            ser = PermissionRequestReviewSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            with transaction.atomic():
                permission_request.status = 'approved'
                permission_request.reviewer = request.user
                permission_request.review_comment = ser.validated_data.get('review_comment', '')
                permission_request.reviewed_at = datetime.datetime.now()
                permission_request.save()

                if permission_request.request_type == 'role' and permission_request.target_role:
                    permission_request.user.role.add(permission_request.target_role)
                elif permission_request.request_type == 'menu' and permission_request.target_menu:
                    UserDirectPermission.objects.update_or_create(
                        user=permission_request.user,
                        menu=permission_request.target_menu,
                        defaults={'granted_by': request.user}
                    )
                elif permission_request.request_type == 'menu_button' and permission_request.target_menu_button:
                    UserDirectPermission.objects.update_or_create(
                        user=permission_request.user,
                        menu_button=permission_request.target_menu_button,
                        defaults={'granted_by': request.user}
                    )
            result = PermissionRequestSerializer(permission_request).data
            return SuccessResponse(data=result, msg='已通过')
        return ErrorResponse(msg='无权限操作')

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        permission_request = self.get_object()
        if request.user.is_superuser:
            if permission_request.status != 'pending':
                return ErrorResponse(msg='当前状态不允许审批')
            ser = PermissionRequestReviewSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            permission_request.status = 'rejected'
            permission_request.reviewer = request.user
            permission_request.review_comment = ser.validated_data.get('review_comment', '')
            permission_request.reviewed_at = datetime.datetime.now()
            permission_request.save()
            result = PermissionRequestSerializer(permission_request).data
            return SuccessResponse(data=result, msg='已驳回')
        return ErrorResponse(msg='无权限操作')

    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        qs = Role.objects.filter(status=True).values('id', 'name')
        return SuccessResponse(data=list(qs))

    @action(detail=False, methods=['get'])
    def available_menus(self, request):
        qs = Menu.objects.filter(status=1, visible=1).values('id', 'name', 'parent', 'web_path')
        return SuccessResponse(data=list(qs))


class UserDirectPermissionViewSet(mixins.ListModelMixin,
                                   mixins.DestroyModelMixin,
                                   viewsets.GenericViewSet):
    queryset = UserDirectPermission.objects.all()
    serializer_class = UserDirectPermissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            qs = qs.filter(user=user)
        return qs
