"""Conflict Checker 冲突检测 — 排他网关规则专项测试

主要测试 Rule 6: ExclusiveGateway 出边必须设置条件表达式。
验证冲突检测引擎对排他网关的各种边界条件判断是否准确。
"""

from django.test import SimpleTestCase

from opsflow.core.conflict_checker import check_config_conflicts


class TestExclusiveGatewayConflictRules(SimpleTestCase):
    """排他网关冲突检测 — Rule 6: 出边条件表达式"""

    def test_missing_condition_on_edge(self):
        """出边 condition 为空 → warning"""
        tree = {
            "nodes": [
                {"id": "gw1", "node_type": "exclusive_gateway", "label": "Choose"},
                {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "Branch A"},
                {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "Branch B"},
            ],
            "edges": [
                {"from": "gw1", "to": "n1", "condition": ""},
                {"from": "gw1", "to": "n2", "condition": "${_result == False}"},
            ],
        }
        result = check_config_conflicts(tree)
        warnings = result.get("warnings", [])
        assert any("no condition expression" in w for w in warnings)
        assert any("Branch A" in w for w in warnings)

    def test_all_edges_have_conditions(self):
        """所有出边都有条件 → 无 warning"""
        tree = {
            "nodes": [
                {"id": "gw1", "node_type": "exclusive_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "gw1", "to": "n1", "condition": "${_result == True}"},
                {"from": "gw1", "to": "n2", "condition": "${_result == False}"},
            ],
        }
        result = check_config_conflicts(tree)
        assert not any("no condition expression" in w for w in result.get("warnings", []))

    def test_mixed_conditions(self):
        """部分有条件部分没有 → 只对无条件的边报 warning"""
        tree = {
            "nodes": [
                {"id": "gw1", "node_type": "exclusive_gateway", "label": "Choose"},
                {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "A"},
                {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "B"},
                {"id": "n3", "type": "task", "atom_type": "ping_test", "label": "C"},
            ],
            "edges": [
                {"from": "gw1", "to": "n1", "condition": "${cond1}"},
                {"from": "gw1", "to": "n2"},              # 无 condition 字段
                {"from": "gw1", "to": "n3", "condition": ""},  # 空 condition
            ],
        }
        result = check_config_conflicts(tree)
        warnings = result.get("warnings", [])
        gw_warnings = [w for w in warnings if "no condition expression" in w]
        # 应该只有 2 条 warning（n2 和 n3），n1 有条件所以没有
        assert len(gw_warnings) == 2

    def test_single_edge_gateway(self):
        """排他网关只有 1 条出边 → 有条件则不 warning"""
        tree = {
            "nodes": [
                {"id": "gw1", "node_type": "exclusive_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "gw1", "to": "n1", "condition": "${always}"},
            ],
        }
        result = check_config_conflicts(tree)
        assert not any("no condition expression" in w for w in result.get("warnings", []))

    def test_non_gateway_nodes_unaffected(self):
        """非排他网关的边不应触发 Rule 6 warning"""
        tree = {
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "n1", "to": "n2"},  # 普通边，没有 condition
            ],
        }
        result = check_config_conflicts(tree)
        assert not any("no condition expression" in w for w in result.get("warnings", []))

    def test_with_parallel_gateway_no_converge(self):
        """并行网关无汇聚（Rule 4）不应干扰排他分支检测（Rule 6）"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "eg", "node_type": "exclusive_gateway", "label": "Choose"},
                {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "A"},
                {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "B"},
            ],
            "edges": [
                {"from": "pg", "to": "eg"},
                {"from": "eg", "to": "n1", "condition": "${_result == True}"},
                {"from": "eg", "to": "n2", "condition": ""},
            ],
        }
        result = check_config_conflicts(tree)
        warnings = result.get("warnings", [])
        # Rule 4: parallel_gateway 可能缺汇聚
        assert any("Parallel gateway" in w for w in warnings)
        # Rule 6: exclusive_gateway 出边条件缺失
        assert any("no condition expression" in w for w in warnings)

    def test_exclusive_gateway_with_condition_field_absent(self):
        """出边有 label 但无 condition 字段 → 按无处理"""
        tree = {
            "nodes": [
                {"id": "gw1", "node_type": "exclusive_gateway", "label": "Choose"},
                {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "Branch A"},
                {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "Branch B"},
            ],
            "edges": [
                {"from": "gw1", "to": "n1", "label": "success"},     # 无 condition
                {"from": "gw1", "to": "n2", "label": "failure"},     # 无 condition
            ],
        }
        result = check_config_conflicts(tree)
        warnings = result.get("warnings", [])
        assert any("no condition expression" in w for w in warnings)


class TestParallelGatewayConflictRules(SimpleTestCase):
    """并行网关冲突检测 — Rule 4: 缺少汇聚网关"""

    def test_parallel_gateway_with_converge(self):
        """并行网关下游有汇聚网关 → 无 warning"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "cg", "node_type": "converge_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "pg", "to": "n1"},
                {"from": "pg", "to": "n2"},
                {"from": "n1", "to": "cg"},
                {"from": "n2", "to": "cg"},
            ],
        }
        result = check_config_conflicts(tree)
        assert not any("Parallel gateway" in w for w in result.get("warnings", []))

    def test_parallel_gateway_without_converge(self):
        """并行网关下游无汇聚网关 → warning"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
            ],
            "edges": [
                {"from": "pg", "to": "n1"},
                {"from": "pg", "to": "n2"},
            ],
        }
        result = check_config_conflicts(tree)
        warnings = result.get("warnings", [])
        assert any("Parallel gateway" in w for w in warnings)

    def test_parallel_gateway_converge_after_chain(self):
        """并行网关 → 链式节点 → 汇聚，应有汇聚路径"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "n2", "type": "task", "atom_type": "ping_test"},
                {"id": "n3", "type": "task", "atom_type": "ping_test"},
                {"id": "cg", "node_type": "converge_gateway"},
            ],
            "edges": [
                {"from": "pg", "to": "n1"},
                {"from": "pg", "to": "n2"},
                {"from": "n1", "to": "n3"},
                {"from": "n2", "to": "cg"},
                {"from": "n3", "to": "cg"},
            ],
        }
        result = check_config_conflicts(tree)
        # 从 pg 出发有路径可以到达 cg，应该无 warning
        assert not any("Parallel gateway" in w for w in result.get("warnings", []))

    def test_parallel_gateway_single_branch(self):
        """并行网关 1 条出边 + 汇聚 → 无 warning"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "n1", "type": "task", "atom_type": "ping_test"},
                {"id": "cg", "node_type": "converge_gateway"},
            ],
            "edges": [
                {"from": "pg", "to": "n1"},
                {"from": "n1", "to": "cg"},
            ],
        }
        result = check_config_conflicts(tree)
        # 有汇聚路径 → 无 warning
        assert not any("Parallel gateway" in w for w in result.get("warnings", []))

    def test_parallel_gateway_chain_to_converge_deep(self):
        """多级链式路径最终到达汇聚"""
        tree = {
            "nodes": [
                {"id": "pg", "node_type": "parallel_gateway"},
                {"id": "a1", "type": "task", "atom_type": "ping_test"},
                {"id": "a2", "type": "task", "atom_type": "ping_test"},
                {"id": "b1", "type": "task", "atom_type": "ping_test"},
                {"id": "cg", "node_type": "converge_gateway"},
            ],
            "edges": [
                {"from": "pg", "to": "a1"},
                {"from": "pg", "to": "b1"},
                {"from": "a1", "to": "a2"},
                {"from": "a2", "to": "cg"},
                {"from": "b1", "to": "cg"},
            ],
        }
        result = check_config_conflicts(tree)
        assert not any("Parallel gateway" in w for w in result.get("warnings", []))
