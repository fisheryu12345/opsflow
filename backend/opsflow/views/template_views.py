"""FlowTemplate ViewSet — 流程模板 CRUD

标准 CRUD 操作保留在此文件中。AI 生成、版本管理、变量管理、
子流程追踪等功能已提取到 views/mixins/ 中的 Mixin 类。
"""

import logging
from rest_framework import viewsets, status, exceptions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from iam.resolvers import has_project_role
from iam.permissions import TenantPermission
from opsflow.models import FlowTemplate
from opsflow.serializers import FlowTemplateSerializer
from opsflow.views.mixins.template_ai import TemplateAIMixin
from opsflow.views.mixins.template_version import TemplateVersionMixin
from opsflow.views.mixins.template_variable import TemplateVariableMixin
from opsflow.views.mixins.template_subprocess import TemplateSubprocessMixin
from opsflow.views.mixins.template_export import TemplateExportImportMixin
from opsflow.views.mixins.template_collect import TemplateCollectMixin
from opsflow.views.mixins.template_webhook import TemplateWebhookMixin
from opsflow.views.base import ProjectFilteredViewSet
from opsflow.core.audit_logger import log_operation
from opsflow.core.plugin_deprecation import check_deprecated_plugins_in_template
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

logger = logging.getLogger(__name__)


class FlowTemplateViewSet(
    TemplateAIMixin,
    TemplateVersionMixin,
    TemplateVariableMixin,
    TemplateSubprocessMixin,
    TemplateExportImportMixin,
    TemplateCollectMixin,
    TemplateWebhookMixin,
    ProjectFilteredViewSet,
):
    queryset = FlowTemplate.objects.all()
    serializer_class = FlowTemplateSerializer
    permission_classes = [IsAuthenticated, TenantPermission]
    filterset_fields = ['is_draft', 'created_by', 'category', 'project', 'is_public']
    search_fields = ['name']
    ordering = ['-created_at']
    project_field = 'project'
    include_public = True
    required_permission = None
    action_permissions = {
        'make_public': 'opsflow:template:publish',
    }

    def perform_create(self, serializer):
        is_public = serializer.validated_data.get('is_public', False)
        if is_public:
            if not self.request.user.is_superuser:
                raise exceptions.PermissionDenied('Only superusers can create public templates')
            instance = serializer.save(created_by=self.request.user, project=None)
        else:
            project_kwargs = self.resolve_project_kwargs(self.request)
            if 'project_id' in project_kwargs:
                if not has_project_role(self.request.user, project_kwargs['project_id'], 'editor'):
                    raise exceptions.PermissionDenied(
                        'You need at least editor role to create templates in this project'
                    )
            instance = serializer.save(created_by=self.request.user, **project_kwargs)
        log_operation(self.request.user, 'create', 'template', instance.id, instance.name, request=self.request)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return DetailResponse(data=serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return DetailResponse(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return DetailResponse(data=serializer.data, msg='success')

    def _check_edit_lock(self, instance, user):
        """Check if template is locked by another user"""
        from opsflow.models import TemplateLock
        lock = TemplateLock.objects.filter(template=instance).first()
        if lock and lock.user != user and not lock.is_expired():
            raise exceptions.PermissionDenied(
                f'Template is locked by {lock.user.username}. '
                f'If you believe this is an error, wait 60 seconds for the lock to expire.'
            )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        self._check_edit_lock(instance, request.user)
        # non-superuser cannot edit public templates
        if instance.is_public and not request.user.is_superuser:
            return ErrorResponse(msg='Only superusers can edit public templates', code=4000, status=status.HTTP_403_FORBIDDEN)
        # non-superuser: making template public requires project admin role
        if request.data.get('is_public') and not request.user.is_superuser:
            if not instance.project_id:
                return ErrorResponse(msg='Only superusers can set a template as public', code=4000, status=status.HTTP_403_FORBIDDEN)
            if not has_project_role(request.user, instance.project_id, 'admin'):
                return ErrorResponse(msg='Only superusers or project admin can set a template as public', code=4000, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # ── 无用变量自动清理 ──
        from opsflow.core.variable_resolver import cleanup_unused_vars
        cleaned = cleanup_unused_vars(instance.pipeline_tree or {}, instance.global_vars or {})
        instance.global_vars = cleaned
        instance.save(update_fields=['global_vars'])
        # ── 结束 ──
        # ── 节点持久化同步（pipeline_tree 变更时） ──
        if 'pipeline_tree' in request.data:
            from opsflow.core.node_sync import sync_template_nodes
            sync_template_nodes(instance)
        # ── 结束 ──
        log_operation(self.request.user, 'update', 'template', instance.id, instance.name, request=self.request)
        return DetailResponse(data=serializer.data, msg='success')

    @action(detail=True, methods=['get'])
    def check_deprecated_plugins(self, request, pk=None):
        """检查模板中是否引用已弃用的插件"""
        template = self.get_object()
        result = check_deprecated_plugins_in_template(template)
        return DetailResponse(data=result)

    @action(detail=False, methods=['post'])
    def update_plugin_phase(self, request):
        """手动更新插件生命周期阶段 — 供管理员使用"""
        code = request.data.get('code', '')
        version = request.data.get('version', '')
        phase = request.data.get('phase')
        if not code or phase is None:
            return ErrorResponse(msg='code and phase required', code=4000)
        from opsflow.models import PluginMeta
        filters = {'code': code}
        if version:
            filters['version'] = version
        updated = PluginMeta.objects.filter(**filters).update(phase=phase)
        return DetailResponse(data={'updated': updated})

    @action(detail=False, methods=['get'], url_path='presets')
    def presets(self, request):
        """返回所有启用的模板预设提示词"""
        from opsflow.models.template import TemplatePreset
        qs = TemplatePreset.objects.filter(is_active=True).order_by('sort_order')
        data = [{'id': p.id, 'name': p.name, 'name_en': p.name_en,
                 'icon': p.icon, 'prompt': p.prompt, 'prompt_en': p.prompt_en,
                 'category': p.category} for p in qs]
        return DetailResponse(data=data)

    @action(detail=True, methods=['post'], url_path='make-public')
    def make_public(self, request, pk=None):
        """将项目模板转换为公共模板 — 仅 project admin 或 superuser 可操作"""
        template = self.get_object()
        user = request.user

        # 权限检查
        if not user.is_superuser:
            if not template.project_id:
                raise exceptions.PermissionDenied('Template has no project')
            if not has_project_role(user, template.project_id, 'admin'):
                raise exceptions.PermissionDenied('Only project admin can make template public')

        if template.is_draft:
            return ErrorResponse(msg='Publish the template first before making it public')

        if template.is_public:
            return ErrorResponse(msg='Template is already public')

        scope = request.data.get('project_scope', ['*'])

        template.is_public = True
        template.project = None
        template.project_scope = scope
        template.save(update_fields=['is_public', 'project', 'project_scope'])

        serializer = self.get_serializer(template)
        return DetailResponse(data=serializer.data, msg='Template is now public')

    # ── Optimistic lock actions ──

    @action(detail=True, methods=['post'])
    def acquire_lock(self, request, pk=None):
        """Acquire template editing lock"""
        from opsflow.models import TemplateLock
        from django.utils import timezone

        template = self.get_object()
        lock, created = TemplateLock.objects.get_or_create(
            template=template,
            defaults={'user': request.user},
        )

        if created:
            return DetailResponse(data={
                'template_id': template.id,
                'locked_by': {'id': request.user.id, 'username': str(request.user)},
            }, msg='Lock acquired')

        # Same user: refresh heartbeat
        if lock.user == request.user:
            lock.heartbeat = timezone.now()
            lock.save(update_fields=['heartbeat'])
            return DetailResponse(data={
                'template_id': template.id,
                'locked_by': {'id': request.user.id, 'username': str(request.user)},
            }, msg='Lock refreshed')

        # Expired lock: reassign
        if lock.is_expired():
            lock.user = request.user
            lock.locked_at = timezone.now()
            lock.heartbeat = timezone.now()
            lock.save(update_fields=['user', 'locked_at', 'heartbeat'])
            return DetailResponse(data={
                'template_id': template.id,
                'locked_by': {'id': request.user.id, 'username': str(request.user)},
            }, msg='Expired lock transferred')

        # Conflict
        return ErrorResponse(
            msg=f'Template is being edited by {lock.user.username}',
            code=4000,
            status=status.HTTP_409_CONFLICT,
            data={
                'locked_by': {'id': lock.user.id, 'username': str(lock.user)},
                'locked_at': lock.locked_at.isoformat() if lock.locked_at else None,
            },
        )

    @action(detail=True, methods=['post'])
    def release_lock(self, request, pk=None):
        """Release template editing lock (idempotent)"""
        from opsflow.models import TemplateLock
        TemplateLock.objects.filter(template_id=pk, user=request.user).delete()
        return DetailResponse(msg='Lock released')

    @action(detail=True, methods=['post'])
    def heartbeat_lock(self, request, pk=None):
        """Heartbeat for template editing lock"""
        from opsflow.models import TemplateLock
        from django.utils import timezone
        lock = TemplateLock.objects.filter(template_id=pk, user=request.user).first()
        if not lock:
            return ErrorResponse(msg='No active lock found', code=4000)
        if lock.is_expired():
            lock.delete()
            return ErrorResponse(msg='Lock expired', code=410)
        lock.heartbeat = timezone.now()
        lock.save(update_fields=['heartbeat'])
        return DetailResponse(data={'locked_at': lock.locked_at.isoformat() if lock.locked_at else ''}, msg='Heartbeat updated')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_public:
            if not request.user.is_superuser:
                return ErrorResponse(msg='Only superusers can delete public templates', code=4000)
        elif instance.project_id and not has_project_role(request.user, instance.project_id, 'editor'):
            return ErrorResponse(msg='You need at least editor role to delete this template', code=4000)
        log_operation(request.user, 'delete', 'template', instance.id, instance.name, request=request)
        instance.delete()
        return DetailResponse(data=None)
