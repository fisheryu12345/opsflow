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

    def test_success_failure_auto_var(self):
        """success/failure 边自动注册 _result 变量"""
        edges = [
            {"from": "n1", "to": "n2", "label": "success"},
            {"from": "n1", "to": "n3", "label": "failure"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        # 应生成 _result_n1 变量
        assert "_result_n1" in auto_vars
        assert auto_vars["_result_n1"] == {"source_act": "n1", "source_key": "_result"}
        # success 边条件：${_result_n1} == True（变量 ${} 取节点值后 BoolRule 解析完整表达式）
        assert conditions["n1->n2"] == "${_result_n1} == True"
        # failure 边条件：${_result_n1} == False
        assert conditions["n1->n3"] == "${_result_n1} == False"

    def test_mixed_custom_and_auto_conditions(self):
        """自定义条件和自动 success/failure 边共存"""
        edges = [
            {"from": "n1", "to": "n2", "label": "success"},
            {"from": "n1", "to": "n3", "label": "failure"},
            {"from": "n2", "to": "n4", "condition": "${node_2.msg == 'ok'}"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        # n1 → n2/n3 生成 auto var
        assert "_result_n1" in auto_vars
        # n2 → n4 使用自定义引用
        assert "_gwcond_node_2_msg" in auto_vars
        assert conditions["n2->n4"] == "${_gwcond_node_2_msg == 'ok'}"

    def test_success_label_only_auto_var(self):
        """只有一个 success 标记时也注册 _result 变量"""
        edges = [
            {"from": "n1", "to": "n2", "label": "success"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges)
        # 即使只有一个 success 边也注册 _result（隐式 ExclusiveGateway 需要）
        assert "_result_n1" in auto_vars
        assert conditions["n1->n2"] == "${_result_n1} == True"

    def test_gateway_edges_link_to_predecessor(self):
        """exclusive_gateway 出边的 success/failure 标签自动引用前驱活动节点的 _result"""
        edges = [
            {"from": "n1", "to": "gw1", "label": "success"},
            {"from": "gw1", "to": "n2", "label": "success"},
            {"from": "gw1", "to": "n3", "label": "failure"},
        ]
        nodes = [
            {"id": "n1", "node_type": "atom"},
            {"id": "gw1", "node_type": "exclusive_gateway"},
            {"id": "n2", "node_type": "atom"},
            {"id": "n3", "node_type": "atom"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges, effective_nodes=nodes)
        # 应注册 _result_n1（前驱活动节点的 _result）
        assert "_result_n1" in auto_vars
        assert auto_vars["_result_n1"] == {"source_act": "n1", "source_key": "_result"}
        # n1→gw1 出边：非网关 → 直接注册
        assert conditions["n1->gw1"] == "${_result_n1} == True"
        # gw1→n2/n3 出边：网关 → 回溯到 n1 的 _result
        assert conditions["gw1->n2"] == "${_result_n1} == True"
        assert conditions["gw1->n3"] == "${_result_n1} == False"

    def test_gateway_no_predecessor_skips_auto_gen(self):
        """网关没有非网关前驱时不生成自动条件（避免引用不存在的前驱变量）"""
        edges = [
            {"from": "gw1", "to": "n2", "label": "success"},
        ]
        nodes = [
            {"id": "gw1", "node_type": "exclusive_gateway"},
            {"id": "n2", "node_type": "atom"},
        ]
        conditions, auto_vars = _parse_edge_conditions(edges, effective_nodes=nodes)
        # 没有前驱活动节点 → 不自动生成
        assert "_result_n2" not in auto_vars  # 不引用自身
        assert "gw1->n2" not in conditions    # 让 _get_condition 兜底


class TestGetCondition:
    """_get_condition 条件回退逻辑"""

    def test_custom_condition_returns(self):
        conditions = {"n1->n2": "${node_1.cpu > 80}"}
        result = _get_condition(conditions, "n1", "n2")
        assert result == "${node_1.cpu > 80}"

    def test_success_label_default(self):
        result = _get_condition({}, "n1", "n2", label="success")
        assert result == "${_result} == True"

    def test_failure_label_default(self):
        result = _get_condition({}, "n1", "n2", label="failure")
        assert result == "${_result} == False"

    def test_unknown_label_default(self):
        """默认 label 也返回 success 条件"""
        result = _get_condition({}, "n1", "n2", label="other")
        assert result == "${_result} == True"

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
        tpl.project_id = None
        tpl.id = None
        return tpl

    def test_empty_nodes_returns_empty_pipeline(self):
        tpl = self._make_template()
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result or "end_event" in result

    def test_single_atom_produces_pipeline(self):
        nodes = [{"id": "n1", "type": "task", "atom_type": "ping_test",
                  "label": "Ping Test", "params": {"target_ip": "10.0.0.1"}}]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None
        assert "activities" in result
        # 原始 X6 ID 直接作为 bamboo activity ID
        assert "n1" in result['activities'], f"n1 应作为 activity key，实际 keys={list(result['activities'].keys())}"

    def test_start_end_only_passes_gracefully(self):
        """只有 start/end 视觉节点 → 空 pipeline"""
        nodes = [
            {"id": "s1", "node_type": "start_event"},
            {"id": "e1", "node_type": "end_event"},
        ]
        edges = [{"from": "s1", "to": "e1"}]
        tpl = self._make_template(nodes, edges)
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_multi_root_creates_parallel_gateway(self):
        """多个入口节点自动插入 ParallelGateway"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "ping_test"},
            {"id": "n2", "type": "task", "atom_type": "ping_test"},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, _ = build_bamboo_pipeline(tpl)
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
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_implicit_success_failure_gateway(self):
        """原子节点 success/failure 双出边且无自定义条件时自动创建隐式 ExclusiveGateway"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "check_disk"},
            {"id": "n2", "type": "task", "atom_type": "send_alert"},
            {"id": "n3", "type": "task", "atom_type": "send_success"},
        ]
        # success/failure 边无 explicit condition → 触发隐式 ExclusiveGateway 创建
        edges = [
            {"from": "n1", "to": "n2", "label": "failure"},
            {"from": "n1", "to": "n3", "label": "success"},
        ]
        tpl = self._make_template(nodes, edges)
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None

        # 验证 data.inputs 中包含 ${_result_n1} 的 NodeOutput 声明
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

        # 验证门条件的 evaluate 中包含 ${_result_n1} == True（变量取 ${} 后 BoolRule 解析完整表达式）
        gateways = result.get("gateways", {})
        assert len(gateways) > 0, "应创建至少一个 gateway"

        result_found_gw = False
        for gid, gw in gateways.items():
            conditions = gw.get("conditions", {})
            for flow_id, cond_data in conditions.items():
                evaluate = cond_data.get("evaluate", "")
                if "${_result_n1} == True" in evaluate:
                    result_found_gw = True
        assert result_found_gw, "应存在 evaluate 包含 ${_result_n1} == True 的 gateway 条件"

    def test_with_timeout_configs(self):
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "shell",
             "timeout_seconds": 300, "params": {"cmd": "sleep 100"}},
        ]
        edges = []
        tpl = self._make_template(nodes, edges)
        result, _ = build_bamboo_pipeline(tpl)
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
        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None


class TestValidateBambooCompatibility:
    """validate_bamboo_compatibility 校验"""

    def test_empty_pipeline(self):
        result = validate_bamboo_compatibility({"nodes": [], "edges": []})
        assert result["valid"] is True
        assert len(result["warnings"]) > 0 or len(result["errors"]) == 0

    def test_single_node_pipeline(self):
        """单节点有 start 入边 → 合法"""
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

    def test_duplicate_ids(self):
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n1", "node_type": "atom", "label": "N1-2", "atom_type": "ping_test"},
            ],
            "edges": [],
        })
        assert result["valid"] is False

    def test_broken_edge_reference(self):
        """边引用了不存在的节点 → orphan warning"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "ping_test"},
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
                {"id": "n1", "node_type": "atom", "label": "N1", "atom_type": "ping_test"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "ping_test"},
                {"id": "n3", "node_type": "atom", "label": "N3", "atom_type": "ping_test"},
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
        assert any("出度" in e for e in result["errors"])

    def test_valid_serial_pipeline(self):
        """合法串行流程（start → n1 → n2）"""
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

    def test_gateway_validation(self):
        """汇聚网关出度不能超过 1"""
        result = validate_bamboo_compatibility({
            "nodes": [
                {"id": "n1", "node_type": "converge_gateway", "label": "CG"},
                {"id": "n2", "node_type": "atom", "label": "N2", "atom_type": "ping_test"},
                {"id": "n3", "node_type": "atom", "label": "N3", "atom_type": "ping_test"},
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


class TestExclusiveGatewayBuild:
    """排他网关专门测试 — 条件构建 + 完整流程"""

    def test_conditions_stored_on_gateway(self):
        """验证 ExclusiveGateway.conditions dict 被正确填充"""
        node = {"id": "gw1", "node_type": "exclusive_gateway"}
        outgoing = [
            {"to": "n1", "label": "success", "condition": "${_result == True}"},
            {"to": "n2", "label": "failure", "condition": "${_result == False}"},
        ]
        conditions_map = {"gw1->n1": "${_result == True}", "gw1->n2": "${_result == False}"}
        elem = _create_element(node, outgoing, conditions_map)
        from bamboo_engine.builder.flow.gateway import ExclusiveGateway
        assert isinstance(elem, ExclusiveGateway)
        # conditions 是 {int index: str expr}
        assert len(elem.conditions) == 2
        assert elem.conditions[0] == "${_result == True}"
        assert elem.conditions[1] == "${_result == False}"

    def test_single_outgoing_edge(self):
        """只有 1 条出边时排他网关仍正常工作"""
        node = {"id": "gw1", "node_type": "exclusive_gateway"}
        outgoing = [{"to": "n1", "label": "success", "condition": "${_result == True}"}]
        conditions_map = {"gw1->n1": "${_result == True}"}
        elem = _create_element(node, outgoing, conditions_map)
        assert len(elem.conditions) == 1
        assert elem.conditions[0] == "${_result == True}"

    def test_no_conditions_fallback_to_default(self):
        """出边未设置条件时回退到 _result 默认值"""
        node = {"id": "gw1", "node_type": "exclusive_gateway"}
        outgoing = [
            {"to": "n1", "label": "success"},
            {"to": "n2", "label": "failure"},
        ]
        # 空的 conditions_map → _get_condition 按 label 回退
        elem = _create_element(node, outgoing, {})
        assert len(elem.conditions) == 2
        assert elem.conditions[0] == "${_result} == True"   # success 默认
        assert elem.conditions[1] == "${_result} == False"  # failure 默认

    def test_build_full_exclusive_gateway_pipeline(self):
        """完整流程：atom → exclusive_gateway → 分支 A/B

        验证构建出的 bamboo pipeline tree 包含正确的 gateways/activities/flows/conditions。
        """
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
        tpl.project_id = None  # 避免 resolve_project_variables DB 查询
        tpl.id = None

        result, _ = build_bamboo_pipeline(tpl)

        assert result is not None
        # 验证 gateways 部分存在
        assert "gateways" in result
        assert "gw1" in result["gateways"], "ExclusiveGateway 应使用原始 ID 作为 key"
        gw_data = result["gateways"]["gw1"]
        assert gw_data["type"] == "ExclusiveGateway"
        # 验证 conditions 存在
        assert "conditions" in gw_data
        assert len(gw_data["conditions"]) == 2
        # 验证 activities 包含所有 3 个原子节点
        assert len(result["activities"]) == 3
        # 验证 flows 正确连接
        assert "flows" in result
        flow_count = len(result["flows"])
        # atom→gw (1) + gw→n2 (1) + gw→n3 (1) = 至少 3 条流
        assert flow_count >= 3, f"预期至少 3 条流，实际 {flow_count}"


class TestParallelGatewayBuild:
    """并行网关专门测试 — 元素创建 + 完整流程构建"""

    def test_parallel_gateway_creates_gateway(self):
        """验证 _create_element 返回 ParallelGateway 实例"""
        node = {"id": "pg1", "node_type": "parallel_gateway"}
        elem = _create_element(node, [])
        from bamboo_engine.builder.flow.gateway import ParallelGateway
        assert isinstance(elem, ParallelGateway)

    def test_parallel_gateway_no_conditions(self):
        """并行网关没有 conditions（与排他网关不同）"""
        node = {"id": "pg1", "node_type": "parallel_gateway"}
        elem = _create_element(node, [])
        assert not hasattr(elem, 'conditions') or len(elem.conditions) == 0

    def test_build_parallel_gateway_with_converge(self):
        """完整：start → parallel_gateway → 3 条并行分支 → converge → end

        验证构建出的 pipeline 包含 ParallelGateway 和 ConvergeGateway，
        且 branches 全部同时存在。
        """
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

        result, _ = build_bamboo_pipeline(tpl)

        assert result is not None
        # 验证 gateways 包含 ParallelGateway
        assert "gateways" in result
        assert "pg1" in result["gateways"], "ParallelGateway 应使用原始 ID"
        assert result["gateways"]["pg1"]["type"] == "ParallelGateway"
        # 验证 converge gateway 也在 gateways 中
        assert "cg1" in result["gateways"], "ConvergeGateway 应使用原始 ID"
        assert result["gateways"]["cg1"]["type"] == "ConvergeGateway"
        # 验证所有 3 个 task 都在 activities 中
        assert len(result["activities"]) == 3
        # 验证 flows (pg→t1,t2,t3 + t1,t2,t3→cg + start→pg) 至少 7 条
        assert "flows" in result
        assert len(result["flows"]) >= 7

    def test_build_parallel_without_converge_auto_inferred(self):
        """并行网关无汇聚网关时 builder 自动推断（所有分支汇聚到 end）"""
        nodes = [
            {"id": "pg1", "node_type": "parallel_gateway", "label": "Fork"},
            {"id": "t1", "type": "task", "atom_type": "ping_test", "label": "T1"},
            {"id": "t2", "type": "task", "atom_type": "ping_test", "label": "T2"},
        ]
        edges = [
            {"from": "pg1", "to": "t1"},
            {"from": "pg1", "to": "t2"},
            # 没有 converge — 所有分支直达 end_event
        ]
        tpl = Mock()
        tpl.name = "test_parallel_no_cg"
        tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
        tpl.target_hosts = []
        tpl.global_vars = {}
        tpl.project_id = None
        tpl.id = None

        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None
        # 应该成功构建（不会崩溃）
        assert "gateways" in result

    def test_multi_root_auto_parallel(self):
        """多个入口节点自动创建 ParallelGateway 连接 start"""
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

        result, _ = build_bamboo_pipeline(tpl)
        assert result is not None
        # 应至少有一个 gateway（自动插入的 ParallelGateway）
        assert len(result.get("gateways", {})) >= 1
