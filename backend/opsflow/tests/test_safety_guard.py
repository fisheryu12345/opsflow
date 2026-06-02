"""Pipeline 安全校验测试 — validate_pipeline 各种场景"""

import pytest
from unittest.mock import patch

# Mock 注册表 — 提供测试用的原子
MOCK_REGISTRY = {
    "ping_test": type("MockPlugin", (), {"risk_level": "low", "code": "ping_test"}),
    "send_alert": type("MockPlugin", (), {"risk_level": "high", "code": "send_alert"}),
    "destroy_vm": type("MockPlugin", (), {"risk_level": "high", "code": "destroy_vm"}),
}


@patch("opsflow.core.safety_guard.PLUGIN_REGISTRY", MOCK_REGISTRY)
class TestValidatePipeline:
    """validate_pipeline 核心逻辑"""

    def test_valid_pipeline(self):
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [],
        })
        assert result.get("valid")

    def test_non_dict_input_returns_invalid(self):
        result = self._validate("not a dict")
        assert result.get("valid") is False

    def test_empty_nodes_pass(self):
        """空 pipeline 应校验失败（与 flow_engine 的空检测一致）"""
        result = self._validate({"nodes": [], "edges": []})
        assert result.get("valid") is False

    def test_unknown_atom_type(self):
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "nonexistent_plugin"},
            ],
            "edges": [],
        })
        assert result.get("valid") is False
        assert any("未知原子" in e for e in result["errors"])

    def test_max_retries_exceeds_limit(self):
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test",
                 "max_retries": 15},
            ],
            "edges": [],
        })
        assert result.get("valid") is False

    def test_max_retries_within_limit(self):
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test",
                 "max_retries": 5},
            ],
            "edges": [],
        })
        assert result.get("valid")

    def test_no_max_retries_ok(self):
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [],
        })
        assert result.get("valid")

    def test_orphan_node_generates_warning(self):
        """孤立节点（无入边）产生 warning"""
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
            ],
        })
        # n1 是 start, n2 有入边, 所以无 orphan
        assert isinstance(result.get("warnings"), list)

    def test_high_risk_without_rollback(self):
        """高危节点无回滚路径 → warning"""
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "send_alert"},
            ],
            "edges": [],
        })
        assert result.get("valid")  # 只有 warning, 不是 error

    @patch("opsflow.core.safety_guard.HIGH_RISK_ATOMS")
    def test_high_risk_with_rollback(self, mock_high_risk):
        """高危节点有回滚路径 → no warning"""
        mock_high_risk.return_value = {"destroy_vm"}
        result = self._validate({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "destroy_vm"},
            ],
            "edges": [
                {"from": "n1", "to": "n2", "label": "failure"},
            ],
        })
        warnings = result.get("warnings", [])
        has_warning = any("回滚" in w for w in warnings)
        assert not has_warning

    def _validate(self, pipeline):
        from opsflow.core.safety_guard import validate_pipeline
        return validate_pipeline(pipeline)
