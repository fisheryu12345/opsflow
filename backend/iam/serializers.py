from rest_framework import serializers

from dvadmin.utils.serializers import CustomModelSerializer
from iam.models import (
    PermissionRequest, UserDirectPermission,
    BusinessGroup, Business, DeployEnvironment,
    Project, ProjectMember,
    BusinessMember, DeployEnvironmentPermission,
)


class PermissionRequestSerializer(CustomModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True, default=None)
    target_role_name = serializers.CharField(source='target_role.name', read_only=True, default=None)
    target_iam_role_name = serializers.CharField(source='target_iam_role.name', read_only=True, default=None)
    target_menu_name = serializers.CharField(source='target_menu.name', read_only=True, default=None)
    target_menu_button_name = serializers.CharField(source='target_menu_button.name', read_only=True, default=None)
    target_project_name = serializers.CharField(source='target_project.name', read_only=True, default=None)
    target_permission_label = serializers.SerializerMethodField()
    target_permission_label_en = serializers.SerializerMethodField()
    request_type_label = serializers.SerializerMethodField()
    request_type_label_en = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    status_label_en = serializers.SerializerMethodField()

    REQUEST_TYPE_EN = {
        'role': 'Role',
        'menu': 'Menu',
        'menu_button': 'Button',
        'project_role': 'Project Role',
        'permission': 'Permission',
    }
    STATUS_EN = {
        'pending': 'Pending',
        'approved': 'Approved',
        'rejected': 'Rejected',
    }

    def get_request_type_label_en(self, obj):
        return self.REQUEST_TYPE_EN.get(obj.request_type, obj.request_type)

    def get_status_label_en(self, obj):
        return self.STATUS_EN.get(obj.status, obj.status)

    def _resolve_perm_label(self, codename):
        """Look up human-readable name from PageButton > PageTab > IAMPermission."""
        from iam.models.page_config import PageButton, PageTab
        # 1. Check PageButton
        btn = PageButton.objects.filter(required_perm=codename).select_related('tab').first()
        if btn:
            return btn.label_zh, btn.label_en or btn.label_zh
        # 2. Check PageTab
        tab = PageTab.objects.filter(required_perm=codename).first()
        if tab:
            return tab.label_zh, tab.label_en or tab.label_zh
        # 3. Fallback to IAMPermission
        from iam.models import IAMPermission
        perm = IAMPermission.objects.filter(codename=codename).first()
        if perm:
            return perm.label, perm.label
        return codename, codename

    def get_target_permission_label(self, obj):
        if obj.target_permission:
            zh, _ = self._resolve_perm_label(obj.target_permission)
            return zh
        return None

    def get_target_permission_label_en(self, obj):
        if obj.target_permission:
            _, en = self._resolve_perm_label(obj.target_permission)
            return en
        return None

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
        fields = ['request_type', 'target_iam_role', 'target_menu', 'target_menu_button', 'target_permission', 'target_project', 'target_project_role', 'selected_buttons', 'reason']


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


# ─── Tenant serializers ──────────────────────────────────────────────────


class BusinessGroupSerializer(CustomModelSerializer):
    class Meta:
        model = BusinessGroup
        fields = '__all__'


class BusinessSerializer(CustomModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)
    owner_name = serializers.CharField(source='owner.username', read_only=True, default=None)
    project_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    def get_project_count(self, obj):
        return obj.projects.count()

    def get_member_count(self, obj):
        return obj.members.count()

    class Meta:
        model = Business
        fields = '__all__'


class BusinessMemberSerializer(CustomModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True, default=None)
    role_label = serializers.SerializerMethodField()

    def get_role_label(self, obj):
        return obj.get_role_display()

    class Meta:
        model = BusinessMember
        fields = '__all__'
        read_only_fields = ['id', 'joined_at']


class DeployEnvironmentSerializer(CustomModelSerializer):
    class Meta:
        model = DeployEnvironment
        fields = '__all__'


class DeployEnvironmentPermissionSerializer(CustomModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True, default=None)
    environment_name = serializers.CharField(source='environment.name', read_only=True)

    class Meta:
        model = DeployEnvironmentPermission
        fields = '__all__'
        read_only_fields = ['id', 'granted_by', 'granted_at']


class ProjectSerializerBase(CustomModelSerializer):
    """Serializer for iam.Project CRUD"""
    business_name = serializers.CharField(source='business.name', read_only=True, default=None)
    owner_name = serializers.CharField(source='owner.username', read_only=True, default=None)
    template_count = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    def get_template_count(self, obj):
        return obj.templates.count()

    def get_member_count(self, obj):
        return obj.members.count()

    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectMemberSerializer(CustomModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True, default=None)
    role_label = serializers.SerializerMethodField()

    def get_role_label(self, obj):
        return obj.get_role_display()

    class Meta:
        model = ProjectMember
        fields = '__all__'
        read_only_fields = ['id', 'joined_at']
