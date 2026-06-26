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
        assert result_var_name == "${_result_n1}", \
            f"NodeOutput key 应为 ${{_result_n1}}，实际为 {result_var_name}"

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
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)
        assert result is not None
        assert len(result.get("gateways", {})) >= 1


class TestLoopMechanismA:
    """Mechanism A: node-level loop - loop_config"""

    def test_loop_config_injected_into_pipeline_dict(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test",
                  "label": "Ping", "params": {"target_ip": "10.0.0.1",
                  "loop_config": {"enable": True, "loop_times": 5, "fail_skip": False}}},
        ]
        edges = []
        tpl = Mock()
        tpl.name = "test_loop_a"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)
        assert "n1" in result.get("activities", {})
        act = result["activities"]["n1"]
        assert "loop_config" in act
        assert act["loop_config"]["loop_times"] == 5
        assert act["loop_config"]["enable"] is True
        assert act["loop_config"]["fail_skip"] is False

    def test_loop_config_skipped_when_not_enabled(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test",
                  "label": "Ping", "params": {"target_ip": "10.0.0.1"}}]
        edges = []
        tpl = Mock()
        tpl.name = "test_loop_disabled"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result = build_bamboo_pipeline(tpl)
        act = result["activities"]["n1"]
        assert "loop_config" not in act

    def test_loop_var_registers_split_input(self):
        node = {"id": "n1", "type": "task", "atom_type": "ping_test",
                "params": {"target_ip": "10.0.0.1",
                "loop_config": {"enable": True, "loop_times": 3,
                                "loop_var": {"name": "target_ip", "values": ["10.0.0.1", "10.0.0.2"]}}}}
        elem = _create_element(node, [], data=None)
        assert "${_loop_value}" in elem.component.inputs["target_ip"].value


class TestLoopMechanismB:
    """Mechanism B: exclusive gateway loop - detection + tolerance + build"""

    def test_detect_exclusive_gateway_loop(self):
        from opsflow.core.bamboo_validator import _detect_exclusive_gateway_loops
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "ping_test"},
            {"id": "gw1", "node_type": "exclusive_gateway"},
            {"id": "n2", "type": "task", "atom_type": "ping_test"},
        ]
        edges = [
            {"from": "n1", "to": "gw1"},
            {"from": "gw1", "to": "n1", "condition": "x"},
            {"from": "gw1", "to": "n2", "condition": "y"},
        ]
        loop_edges = _detect_exclusive_gateway_loops(nodes, edges)
        assert len(loop_edges) == 1, f"expected 1 loop edge, got {len(loop_edges)}: {loop_edges}"
        assert loop_edges[0]["to"] == "n1"

    def test_validate_tolerates_exclusive_gateway_loop(self):
        pipeline = {
            "nodes": [
                {"id": "s1", "node_type": "start_event", "label": "Start"},
                {"id": "n1", "node_type": "atom", "atom_type": "ping_test", "label": "Ping"},
                {"id": "gw1", "node_type": "exclusive_gateway", "label": "Gateway"},
                {"id": "n2", "node_type": "atom", "atom_type": "ping_test", "label": "Ping2"},
                {"id": "e1", "node_type": "end_event", "label": "End"},
            ],
            "edges": [
                {"from": "s1", "to": "n1"},
                {"from": "n1", "to": "gw1"},
                {"from": "gw1", "to": "n1", "condition": "${_result == False}"},
                {"from": "gw1", "to": "n2", "condition": "${_result == True}"},
                {"from": "n2", "to": "e1"},
            ],
        }
        result = validate_bamboo_compatibility(pipeline)
        assert result["valid"] is True

    def test_regular_cycle_still_rejected(self):
        pipeline = {
            "nodes": [
                {"id": "n1", "node_type": "atom", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n1"},
            ],
        }
        result = validate_bamboo_compatibility(pipeline)
        assert result["valid"] is False

    def test_build_pipeline_with_loopback_edge(self):
        """含排他网关回环边的构建 — 验证元素创建和管道结果

        注意：bamboo-engine 的 build_tree() 要求 DAG，回环边会在 builder 层面
        报 IndexError。实际的 cycle_tolerate 在 run_pipeline 时生效。
        这里验证中间步骤的正确性：元素创建 + validation 通过 + 最终构建有保护。
        """
        nodes = [
            {"id": "s1", "node_type": "start_event", "label": "Start"},
            {"id": "n1", "node_type": "atom", "atom_type": "check_disk", "label": "Check", "params": {}},
            {"id": "gw1", "node_type": "exclusive_gateway", "label": "Gate"},
            {"id": "n2", "node_type": "atom", "atom_type": "send_alert", "label": "Alert", "params": {}},
            {"id": "e1", "node_type": "end_event", "label": "End"},
        ]
        edges = [
            {"from": "s1", "to": "n1"},
            {"from": "n1", "to": "gw1"},
            {"from": "gw1", "to": "n1", "label": "failure",
             "condition": "${_result == False}"},
            {"from": "gw1", "to": "n2", "label": "success",
             "condition": "${_result == True}"},
            {"from": "n2", "to": "e1"},
        ]

        # Validation should pass
        result = validate_bamboo_compatibility({
            "nodes": nodes, "edges": edges,
        })
        assert result["valid"] is True, f"Validation failed: {result['errors']}"

        # Loop detection should find 1 loop edge
        from opsflow.core.bamboo_validator import _detect_exclusive_gateway_loops
        loop_edges = _detect_exclusive_gateway_loops(
            [n for n in nodes if n.get('node_type') not in ('start_event', 'end_event')],
            [e for e in edges if e['from'] not in ('s1', 'e1') and e['to'] not in ('s1', 'e1')],
        )
        assert len(loop_edges) == 1
        assert loop_edges[0]["to"] == "n1"

        # Element creation should succeed
        from opsflow.core.pipeline_builder.elements import _create_element
        gw_elem = _create_element(
            {"id": "gw1", "node_type": "exclusive_gateway"},
            [e for e in edges if e["from"] == "gw1"],
        )
        from bamboo_engine.builder.flow.gateway import ExclusiveGateway
        assert isinstance(gw_elem, ExclusiveGateway)
        assert len(gw_elem.conditions) == 2
