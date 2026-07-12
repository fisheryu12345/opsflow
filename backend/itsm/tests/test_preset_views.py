"""Preset ViewSet 测试 — project_id fallback on create

Note: Uses SimpleTestCase to avoid bamboo-pipeline SQLite migration issue
(component_framework_componentmodel table not available in test DB).
"""
from django.test import SimpleTestCase, override_settings
from unittest.mock import MagicMock, patch

from itsm.views.preset_views import PresetViewSet


class TestPresetCreateFallbackProjectId(SimpleTestCase):
    """perform_create() project_id fallback logic — unit tests via patching"""

    def setUp(self):
        self.viewset = PresetViewSet()

    def test_fallback_when_no_project_id_but_has_visible_projects(self):
        """Without project_id but user has visible projects → use first one"""
        serializer = MagicMock()
        request = MagicMock()
        request.data = {}
        request.query_params = {}
        request.user = MagicMock()

        self.viewset.request = request
        pids = [101, 102, 103]
        self.viewset.get_user_project_ids = MagicMock(return_value=pids)

        self.viewset.perform_create(serializer)

        # Should fallback to first project (101) and save
        serializer.save.assert_called_once_with(project_id=101, creator=request.user.id)

    def test_validation_error_when_no_project_at_all(self):
        """Without project_id AND no visible projects → ValidationError"""
        from rest_framework.exceptions import ValidationError
        serializer = MagicMock()
        request = MagicMock()
        request.data = {}
        request.query_params = {}
        request.user = MagicMock()

        self.viewset.request = request
        self.viewset.get_user_project_ids = MagicMock(return_value=[])

        with self.assertRaises(ValidationError):
            self.viewset.perform_create(serializer)

    def test_explicit_project_id_passes(self):
        """Explicit project_id in request body should be used directly"""
        serializer = MagicMock()
        request = MagicMock()
        request.data = {'project_id': 42}
        request.query_params = {}
        request.user = MagicMock()

        self.viewset.request = request
        pids = [42, 99]
        self.viewset.get_user_project_ids = MagicMock(return_value=pids)

        self.viewset.perform_create(serializer)

        serializer.save.assert_called_once_with(project_id=42, creator=request.user.id)

    def test_project_id_from_query_params(self):
        """project_id from query_params should also work"""
        serializer = MagicMock()
        request = MagicMock()
        request.data = {}
        request.query_params = {'project_id': '88'}
        request.user = MagicMock()

        self.viewset.request = request
        pids = [88, 99]
        self.viewset.get_user_project_ids = MagicMock(return_value=pids)

        self.viewset.perform_create(serializer)

        serializer.save.assert_called_once_with(project_id=88, creator=request.user.id)

    def test_permission_denied_when_project_not_visible(self):
        """Explicit project_id must be in user's visible projects"""
        from rest_framework.exceptions import PermissionDenied
        serializer = MagicMock()
        request = MagicMock()
        request.data = {'project_id': 999}
        request.query_params = {}
        request.user = MagicMock()

        self.viewset.request = request
        self.viewset.get_user_project_ids = MagicMock(return_value=[1, 2, 3])

        with self.assertRaises(PermissionDenied):
            self.viewset.perform_create(serializer)
