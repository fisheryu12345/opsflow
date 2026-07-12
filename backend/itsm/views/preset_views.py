# -*- coding: utf-8 -*-
"""Preset ViewSet — 预设管理 CRUD"""

from itsm.models.preset import Preset
from itsm.serializers.preset import PresetSerializer
from itsm.views.workflow_views import ItsmProjectViewSet


class PresetViewSet(ItsmProjectViewSet):
    """预设管理 — 支持按类型过滤 ?preset_type=role_list"""
    model = Preset
    queryset = Preset.objects.all()
    serializer_class = PresetSerializer
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        preset_type = self.request.query_params.get('preset_type', '')
        if preset_type:
            qs = qs.filter(preset_type=preset_type)
        return qs

    def perform_create(self, serializer):
        project_id = (
            self.request.data.get('project_id')
            or self.request.query_params.get('project_id')
        )
        if not project_id:
            # Fallback: use the first user-visible project
            user_pids = self.get_user_project_ids()
            project_id = user_pids[0] if user_pids else None
        if not project_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'project_id': 'project_id is required'})
        project_id = int(project_id)
        if project_id not in self.get_user_project_ids():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('No permission to create resources in this project')
        serializer.save(project_id=project_id, creator=self.request.user.id)
