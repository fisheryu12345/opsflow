"""Integration tests for the ai_layout API endpoint.

Uses RequestFactory + mock to avoid requiring a test database.
Run with: DJANGO_SETTINGS_MODULE=application.test_settings pytest opsflow/tests/test_layout.py -v
"""

import json
from unittest.mock import Mock, patch

from rest_framework.test import APIRequestFactory, force_authenticate

from opsflow.views.template_views import FlowTemplateViewSet


def factory():


from rest_framework.test import APIRequestFactory
def _make_request(data):
    factory = APIRequestFactory()
    request = factory.post('/fake/', data, format='json')
    return request
    """Build a JSON request with force-authenticated user."""
    from dvadmin.system.models import Users

    user = Mock(spec=Users)
    user.pk = 1
    user.id = 1
    user.username = "testuser"
    user.is_authenticated = True
    user.is_superuser = True

    if method == "post":
        request = factory.post(url, data or {}, format="json")
    else:
        request = factory.get(url)
    force_authenticate(request, user=user)


class TestAiLayoutEndpoint(SimpleTestCase):
    """Tests for FlowTemplateViewSet.ai_layout method."""

    def test_requires_nodes(self):
        request = _make_request(factory, data={"nodes": [], "edges": []})
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code == 400
        assert response.data["code"] == 4000

    def test_simple_serial(self):
        data = {
            "nodes": [
                {"id": "n1", "node_type": "start_event"},
                {"id": "n2", "node_type": "", "name": "task"},
                {"id": "n3", "node_type": "end_event"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
            ],
        }
        request = _make_request(factory, data=data)
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code == 200
        assert response.data["code"] == 2000
        positions = response.data["data"]["positions"]
        assert len(positions) == 3
        ids = {p["id"] for p in positions}
        assert ids == {"n1", "n2", "n3"}
        for p in positions:
            assert "x" in p and "y" in p
            assert p["x"] >= 0
            assert p["y"] >= 0

    def test_branching_graph(self):
        data = {
            "nodes": [
                {"id": "s", "node_type": "start_event"},
                {"id": "g1", "node_type": "exclusive_gateway"},
                {"id": "a1", "node_type": "", "name": "A"},
                {"id": "a2", "node_type": "", "name": "B"},
                {"id": "g2", "node_type": "converge_gateway"},
                {"id": "e", "node_type": "end_event"},
            ],
            "edges": [
                {"from": "s", "to": "g1"},
                {"from": "g1", "to": "a1"},
                {"from": "g1", "to": "a2"},
                {"from": "a1", "to": "g2"},
                {"from": "a2", "to": "g2"},
                {"from": "g2", "to": "e"},
            ],
        }
        request = _make_request(factory, data=data)
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code == 200
        positions = response.data["data"]["positions"]
        assert len(positions) == 6
        input_ids = {n["id"] for n in data["nodes"]}
        assert input_ids == returned_ids
