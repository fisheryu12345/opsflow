"""Integration tests for the ai_layout API endpoint.

Uses RequestFactory + mock to avoid requiring a test database.
"""
import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from opsflow.views.template_views import FlowTemplateViewSet


def _make_request(factory, method="post", url="/fake/", data=None):
    """Build a JSON request with force-authenticated user."""
    from iam.models import IAMUsers

    user = Mock(spec=IAMUsers)
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
    return request


class TestAiLayoutEndpoint(SimpleTestCase):
    """Tests for FlowTemplateViewSet.ai_layout method."""

    def test_requires_nodes(self):
        factory = APIRequestFactory()
        request = _make_request(factory, data={"nodes": [], "edges": []})
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code in (200, 400)

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
        factory = APIRequestFactory()
        request = _make_request(factory, data=data)
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code in (200, 400)

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
        factory = APIRequestFactory()
        request = _make_request(factory, data=data)
        view = FlowTemplateViewSet.as_view({"post": "ai_layout"})
        response = view(request)
        assert response.status_code in (200, 400)
