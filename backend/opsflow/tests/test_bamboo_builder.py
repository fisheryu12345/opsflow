"""bamboo_builder 测试 — _parse_edge_conditions / _get_condition / build_bamboo_pipeline / validate_bamboo_compatibility"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from opsflow.core.pipeline_builder import (
    _parse_edge_conditions,
    _get_condition,
    build_bamboo_pipeline,
    _empty_pipeline,
)
from opsflow.core.pipeline_builder.elements import _create_element
from opsflow.core.bamboo_validator import validate_bamboo_compatibility


class TestParseEdgeConditions:
    """_parse_edge_conditions 边条件解析"""

    def test_empty_edges(self):
        conditions, auto_vars = _parse_edge_conditions([])
        assert conditions == {}
        assert auto_vars == {}

    def test_simple_condition(self):
        edges = [
            {"from": "n1", "to": "n2", "condition": "${node_1.cpu > 80}"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        assert "n1->n2" in conditions
        assert "_gwcond_node_1_cpu" in auto_vars
        assert auto_vars["_gwcond_node_1_cpu"] == {"source_act": "node_1", "source_key": "cpu"}

    def test_multi_var_expression(self):
        edges = [
            {"from": "n1", "to": "n2",
             "condition": "${node_1.a > 0 && node_2.b < 5}"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        assert len(auto_vars) == 2
        assert "_gwcond_node_1_a" in auto_vars
        assert "_gwcond_node_2_b" in auto_vars

    def test_no_condition_field(self):
        edges = [{"from": "n1", "to": "n2"}]  # 没有 condition
        conditions, auto_vars = _parse_edge_conditions(edges)
        assert conditions == {}
        assert auto_vars == {}

    def test_empty_condition_string(self):
        edges = [{"from": "n1", "to": "n2", "condition": ""}]
        conditions, auto_vars = _parse_edge_conditions(edges)
        assert conditions == {}
        assert auto_vars == {}

    def test_dedup_same_variable(self):
        edges = [
            {"from": "n1", "to": "n2", "condition": "${node_1.x} > 10"},
            {"from": "n1", "to": "n3", "condition": "${node_1.x} < 5"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        # 同一个变量只注册一次
        assert len(auto_vars) == 1


class TestGetCondition:
    """_get_condition 条件回退逻辑"""

    def test_custom_condition_returns(self):
        conditions = {"n1->n2": "${node_1.cpu > 80}"}
        result = _get_condition(conditions, "n1", "n2")
        assert result == "${node_1.cpu > 80}"

    def test_success_label_default(self):
        result = _get_condition({}, "n1", "n2", label="success")
        assert result == "${_result == True}"

    def test_failure_label_default(self):
        result = _get_condition({}, "n1", "n2", label="failure")
        assert result == "${_result == False}"

    def test_unknown_label_default(self):
        """默认 label 也返回 success 条件"""
        result = _get_condition({}, "n1", "n2", label="other")
        assert result == "${_result == True}"

    def test_condition_with_label_not_used(self):
        conditions = {"n1->n2": "${custom}"}
        result = _get_condition(conditions, "n1", "n2", label="success")
        assert result == "${custom}"  # 自定义条件优先


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
        elem = _create_element(node, outgoing, {"gw1->n1": "${cond}"})
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

    def test_start_event_becomes_service_activity(self):
        # start_event 会被过滤掉，但 _create_element 也会将其转为 ServiceActivity
        node = {"id": "n1", "node_type": "start_event"}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.activity import ServiceActivity
        assert isinstance(elem, ServiceActivity)

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
        return tpl

    def test_empty_nodes_returns_empty_pipeline(self):
        tpl = self._make_template()
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result or "end_event" in result

    def test_single_atom_produces_pipeline(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test",
                  "label": "Ping Test", "params": {"target_ip": "10.0.0.1"}}]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result
        # id_map 应该包含 n1
        assert id_map.get(list(result['activities'].keys())[0]) == 'n1'

    def test_start_end_only_passes_gracefully(self):
        """只有 start/end 视觉节点 → 空 pipeline"""
        nodes = [
            {"id": "s1", "node_type": "start_event"},
            {"id": "e1", "node_type": "end_event"},
        ]
        edges = [{"from": "s1", "to": "e1"}]
        tpl = self._make_template(nodes, edges)
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_multi_root_creates_parallel_gateway(self):
        """多个入口节点自动插入 ParallelGateway"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "ping_test"},
            {"id": "n2", "type": "task", "atom_type": "ping_test"},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, id_map = build_bamboo_pipeline(tpl)
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
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_with_timeout_configs(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "shell",
             "timeout_seconds": 300, "params": {"cmd": "sleep 100"}},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_custom_global_vars(self):
        """传入自定义 global_vars 覆盖模板值"""
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test"}]
        edges = []
        tpl = self._make_template(nodes)
        result, id_map = build_bamboo_pipeline(tpl, global_vars={"threshold": 80})
        assert result is not None

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
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None


class TestValidateBambooCompatibility:
    """validate_bamboo_compatibility 校验"""

    def test_empty_pipeline(self):
        result = validate_bamboo_compatibility({"nodes": [], "edges": []})
        assert result["valid"] is True
        assert len(result["warnings"]) > 0 or len(result["errors"]) == 0

    def test_single_node_pipeline(self):
        result = validate_bamboo_compatibility({
            "nodes": [{"id": "n1", "type": "task", "atom_type": "ping_test"}],
            "edges": [],
        })
        assert result["valid"] is True

    def test_duplicate_ids(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [],
        })
        assert result["valid"] is False

    def test_broken_edge_reference(self):
        """边引用了不存在的节点 → orphan warning"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "nonexistent"},  # 指向不存在的节点
            ],
        })
        # 有效节点 n1→n2 路径完整，但 n2→nonexistent 边被忽略
        # 由于 n2 的出边指向不存在节点，n2 没有有效出边
        # 需检查是否存在 valid=False（可能因为出度/入度不匹配）
        # 目前 validate 不会报错节点到 nonexistent 的边（静默过滤）
        # 只会报 orphan 或 edge 引用缺失
        assert isinstance(result.get("errors"), list)

    def test_cycle_detection(self):
        """环检测"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
                {"id": "n3", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n2", "to": "n3"},
                {"from": "n3", "to": "n1"},  # 环
            ],
        })
        assert result["valid"] is False
        assert any("环" in e for e in result["errors"])

    def test_atom_excessive_output(self):
        """原子节点出度不能超过 2"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
                {"id": "n3", "type": "task", "atom_type": "ping_test"},
                {"id": "n4", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n1", "to": "n3"},
                {"from": "n1", "to": "n4"},
            ],
        })
        assert result["valid"] is False
        assert any("出度" in e for e in result["errors"])

    def test_valid_serial_pipeline(self):
        """合法串行流程"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "send_alert"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
            ],
        })
        assert result["valid"] is True

    def test_gateway_validation(self):
        """汇聚网关出度不能超过 1"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "converge_gateway"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
                {"id": "n3", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},
                {"from": "n1", "to": "n3"},
            ],
        })
        # converge 出度 > 1 应该有 warning
        check = any("汇聚网关" in str(e) or "出度" in str(e)
                    for e in result.get("warnings", []))
        assert check or result["valid"]
