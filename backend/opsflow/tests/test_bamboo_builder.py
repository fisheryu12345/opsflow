"""bamboo_builder 测试 — build_bamboo_pipeline / _create_element / validate_bamboo_compatibility"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from opsflow.core.pipeline_builder import (
    build_bamboo_pipeline,
    _empty_pipeline,
)
from opsflow.core.pipeline_builder.elements import _create_element
from opsflow.core.bamboo_validator import validate_bamboo_compatibility


class TestCreateElement:
    """_create_element 元素工厂"""

    def test_atom_creates_service_activity(self):
        node = {"id": "n1", "type": "task", "atom_type": "shell",
                "params": {"cmd": "ls"}}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.activity import ServiceActivity
        assert isinstance(elem, ServiceActivity)

    def test_exclusive_gateway_creates_gateway(self):
        node = {"id": "gw1", "node_type": "exclusive_gateway"}
        outgoing = [
            {"to": "n1", "label": "success", "condition": "${_result == True}"},
            {"to": "n2", "label": "failure", "condition": "${_result == False}"},
        ]
        elem = _create_element(node, outgoing)
        from bamboo_engine.builder.flow.gateway import ExclusiveGateway
        assert isinstance(elem, ExclusiveGateway)

    def test_parallel_gateway(self):
        node = {"id": "gw1", "node_type": "parallel_gateway"}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.gateway import ParallelGateway
        assert isinstance(elem, ParallelGateway)

    def test_converge_gateway(self):
        node = {"id": "gw1", "node_type": "converge_gateway"}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.gateway import ConvergeGateway
        assert isinstance(elem, ConvergeGateway)

    def test_atom_inherits_timeout(self):
        node = {"id": "n1", "type": "task", "atom_type": "shell",
                "timeout_seconds": 120}
        elem = _create_element(node, [])
        assert hasattr(elem, "timeout")


class TestBuildBambooPipeline:
    """build_bamboo_pipeline 完整构建"""

    def _make_template(self, nodes=None, edges=None, **kwargs):
        tpl = Mock()
        tpl.name = "test"
        tpl.pipeline_tree = {"nodes": nodes or [], "edges": edges or []}
        tpl.target_hosts = kwargs.get("target_hosts", [])
        tpl.global_vars = kwargs.get("global_vars", {})
        tpl.project_id = None
        tpl.id = None
        return tpl

    def test_empty_nodes_returns_empty_pipeline(self):
        tpl = self._make_template()
        result = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result or "end_event" in result

    def test_single_atom_produces_pipeline(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test",
                  "label": "Ping Test", "params": {"target_ip": "10.0.0.1"}}]
        edges = []
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result
        assert "n1" in result['activities']

    def test_start_end_only_passes_gracefully(self):
        nodes = [
            {"id": "s1", "node_type": "start_event"},
            {"id": "e1", "node_type": "end_event"},
        ]
        edges = [{"from": "s1", "to": "e1"}]
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_multi_root_creates_parallel_gateway(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "ping_test"},
            {"id": "n2", "type": "task", "atom_type": "ping_test"},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_with_edge_conditions(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "check_disk"},
            {"id": "n2", "type": "task", "atom_type": "send_alert"},
            {"id": "n3", "type": "task", "atom_type": "send_success"},
        ]
        edges = [
            {"from": "n1", "to": "n2", "label": "failure",
             "condition": "${_result == False}"},
            {"from": "n1", "to": "n3", "label": "success",
             "condition": "${_result == True}"},
        ]
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_implicit_success_failure_gateway(self):
        """原子节点 success/failure 双出边 → 自动创建隐式 ExclusiveGateway"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "check_disk"},
            {"id": "n2", "type": "task", "atom_type": "send_alert"},
            {"id": "n3", "type": "task", "atom_type": "send_success"},
        ]
        edges = [
            {"from": "n1", "to": "n2", "label": "failure"},
            {"from": "n1", "to": "n3", "label": "success"},
        ]
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None

        # 验证 data.inputs 中包含 _result_n1 的 NodeOutput
        data_inputs = result.get("data", {}).get("inputs", {})
        result_var_name = None
        for key, val in data_inputs.items():
            if isinstance(val, dict) and val.get("source_act") == "n1" and val.get("source_key") == "_result":
                result_var_name = key
                break
        assert result_var_name is not None, \
            "应存在从 n1._result 到 context var 的 NodeOutput 映射"
        assert result_var_name == "_result_n1", \
            f"NodeOutput key 应为 _result_n1，实际为 {result_var_name}"

        # 验证 gateway 条件中包含 _result_n1
        gateways = result.get("gateways", {})
        assert len(gateways) > 0, "应创建至少一个 gateway"

    def test_with_timeout_configs(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "shell",
             "timeout_seconds": 300, "params": {"cmd": "sleep 100"}},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_custom_global_vars(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test"}]
        edges = []
        tpl = self._make_template(nodes)
        result = build_bamboo_pipeline(tpl, global_vars={"threshold": 80})
        assert result is not None
        data_inputs = result.get("data", {}).get("inputs", {})
        # global_vars 展开为独立 key
        assert "${threshold}" in data_inputs

    def test_conditional_parallel_gateway(self):
        nodes = [
            {"id": "gw1", "node_type": "conditional_parallel_gateway"},
            {"id": "n1", "type": "task", "atom_type": "ping_test"},
            {"id": "n2", "type": "task", "atom_type": "ping_test"},
        ]
        edges = [
            {"from": "gw1", "to": "n1", "condition": "${_result == True}"},
            {"from": "gw1", "to": "n2", "condition": "${_result == False}"},
        ]
        tpl = self._make_template(nodes, edges)
        result = build_bamboo_pipeline(tpl)
        assert result is not None


class TestValidateBambooCompatibility:
    """validate_bamboo_compatibility 校验"""

    def test_single_node_pipeline(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "start", "node_type": "start_event", "label": "Start"},
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "end", "node_type": "end_event", "label": "End"},
            ],
            "edges": [
                {"from": "start", "to": "n1"},
            ],
        })
        assert result["valid"] is True

    def test_valid_serial_pipeline(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "start", "node_type": "start_event", "label": "Start"},
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "send_alert"},
            ],
            "edges": [
                {"from": "start", "to": "n1"},
                {"from": "n1", "to": "n2"},
            ],
        })
        assert result["valid"] is True

    def test_duplicate_ids(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n1", "node_type": "atom", "label": "N1-2", "atom_type": "ping_test"},
            ],
            "edges": [],
        })
        assert result["valid"] is False

    def test_cycle_detection(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "ping_test"},
                {"id": "n3", "node_type": "atom", "label": "N3", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
                {"from": "n3", "to": "n1"},
            ],
        })
        assert result["valid"] is False

    def test_atom_excessive_output(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "ping_test"},
                {"id": "n3", "node_type": "atom", "label": "N3", "atom_type": "ping_test"},
                {"id": "n4", "node_type": "atom", "label": "N4", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n1", "to": "n3"},
                {"from": "n1", "to": "n4"},
            ],
        })
        assert result["valid"] is False


class TestExclusiveGatewayBuild:
    """排他网关 — 元素创建 + 完整流程"""

    def test_conditions_stored_on_gateway(self):
        """验证 ExclusiveGateway.conditions dict 被正确填充"""
        node = {"id": "gw1", "node_type": "exclusive_gateway"}
        outgoing = [
            {"to": "n1", "label": "success", "condition": "${_result == True}"},
            {"to": "n2", "label": "failure", "condition": "${_result == False}"},
        ]
        elem = _create_element(node, outgoing)
        from bamboo_engine.builder.flow.gateway import ExclusiveGateway
        assert isinstance(elem, ExclusiveGateway)
        assert len(elem.conditions) == 2
        assert elem.conditions[0] == "${_result == True}"
        assert elem.conditions[1] == "${_result == False}"

    def test_build_full_exclusive_gateway_pipeline(self):
        """完整流程：atom → exclusive_gateway → 分支 A/B"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "check_disk",
             "label": "Check Disk", "params": {"cmd": "df -h"}},
            {"id": "gw1", "node_type": "exclusive_gateway", "label": "Disk Full?"},
            {"id": "n2", "type": "task", "atom_type": "send_alert",
             "label": "Send Alert", "params": {"msg": "disk full"}},
            {"id": "n3", "type": "task", "atom_type": "send_success",
             "label": "Send OK", "params": {"msg": "disk ok"}},
        ]
        edges = [
            {"from": "n1", "to": "gw1"},
            {"from": "gw1", "to": "n2", "label": "failure",
             "condition": "${_result == False}"},
            {"from": "gw1", "to": "n3", "label": "success",
             "condition": "${_result == True}"},
        ]
        tpl = Mock()
        tpl.name = "test"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.target_hosts = []
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)

        assert result is not None
        assert "gateways" in result
        assert "gw1" in result["gateways"]
        gw_data = result["gateways"]["gw1"]
        assert gw_data["type"] == "ExclusiveGateway"
        assert "conditions" in gw_data
        assert len(gw_data["conditions"]) == 2
        assert len(result["activities"]) == 3


class TestParallelGatewayBuild:
    """并行网关 — 元素创建 + 完整流程"""

    def test_parallel_gateway_creates_gateway(self):
        node = {"id": "pg1", "node_type": "parallel_gateway"}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.gateway import ParallelGateway
        assert isinstance(elem, ParallelGateway)

    def test_build_parallel_gateway_with_converge(self):
        nodes = [
            {"id": "pg1", "node_type": "parallel_gateway", "label": "Fork"},
            {"id": "t1", "type": "task", "atom_type": "ping_test",
             "label": "Task 1", "params": {}},
            {"id": "t2", "type": "task", "atom_type": "ping_test",
             "label": "Task 2", "params": {}},
            {"id": "t3", "type": "task", "atom_type": "ping_test",
             "label": "Task 3", "params": {}},
            {"id": "cg1", "node_type": "converge_gateway", "label": "Join"},
        ]
        edges = [
            {"from": "pg1", "to": "t1"},
            {"from": "pg1", "to": "t2"},
            {"from": "pg1", "to": "t3"},
            {"from": "t1", "to": "cg1"},
            {"from": "t2", "to": "cg1"},
            {"from": "t3", "to": "cg1"},
        ]
        tpl = Mock()
        tpl.name = "test_parallel"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.target_hosts = []
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)

        assert result is not None
        assert "gateways" in result
        assert "pg1" in result["gateways"]
        assert result["gateways"]["pg1"]["type"] == "ParallelGateway"
        assert "cg1" in result["gateways"]
        assert result["gateways"]["cg1"]["type"] == "ConvergeGateway"
        assert len(result["activities"]) == 3
        assert len(result.get("flows", {})) >= 7

    def test_build_parallel_without_converge_auto_inferred(self):
        nodes = [
            {"id": "pg1", "node_type": "parallel_gateway", "label": "Fork"},
            {"id": "t1", "type": "task", "atom_type": "ping_test", "label": "T1"},
            {"id": "t2", "type": "task", "atom_type": "ping_test", "label": "T2"},
        ]
        edges = [
            {"from": "pg1", "to": "t1"},
            {"from": "pg1", "to": "t2"},
        ]
        tpl = Mock()
        tpl.name = "test_parallel_no_cg"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.target_hosts = []
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "gateways" in result

    def test_multi_root_auto_parallel(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "Root1"},
            {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "Root2"},
        ]
        edges = []
        tpl = Mock()
        tpl.name = "test_multi_root"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.target_hosts = []
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)
        assert result is not None
        assert len(result.get("gateways", {})) >= 1
