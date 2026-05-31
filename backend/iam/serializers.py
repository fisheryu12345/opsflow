from rest_framework import serializers

from dvadmin.utils.serializers import CustomModelSerializer
from iam.models import PermissionRequest, UserDirectPermission


class PermissionRequestSerializer(CustomModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default=None)
    target_role_name = serializers.CharField(source='target_role.name', read_only=True, default=None)
    target_menu_name = serializers.CharField(source='target_menu.name', read_only=True, default=None)
    target_menu_button_name = serializers.CharField(source='target_menu_button.name', read_only=True, default=None)
    request_type_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    def get_request_type_label(self, obj):
        return obj.get_request_type_display()

    def get_status_label(self, obj):
        return obj.get_status_display()

    class Meta:
        model = PermissionRequest
        fields = '__all__'
        read_only_fields = ['id', 'user', 'status', 'reviewer', 'review_comment', 'reviewed_at']


class PermissionRequestCreateSerializer(CustomModelSerializer):
    class Meta:
        model = PermissionRequest
        fields = ['request_type', 'target_role', 'target_menu', 'target_menu_button', 'reason']


class PermissionRequestReviewSerializer(serializers.Serializer):
    review_comment = serializers.CharField(required=False, allow_blank=True, default='')


class UserDirectPermissionSerializer(CustomModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    menu_name = serializers.CharField(source='menu.name', read_only=True, default=None)
    menu_button_name = serializers.CharField(source='menu_button.name', read_only=True, default=None)
    granted_by_name = serializers.CharField(source='granted_by.name', read_only=True, default=None)

    class Meta:
        model = UserDirectPermission
        fields = '__all__'
        read_only_fields = ['id', 'granted_by', 'granted_at']
