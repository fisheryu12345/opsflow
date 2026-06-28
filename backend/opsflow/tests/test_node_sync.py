"""节点持久化同步测试 — 测试 extract_nodes_from_tree 数据转换逻辑

DB 依赖的同步函数（sync_template_nodes / sync_execution_nodes）通过
实际迁移和手工验证确认正确性。
"""

from django.test import TestCase
from opsflow.core.node_sync import extract_nodes_from_tree


class TestExtractNodes(TestCase):
    """extract_nodes_from_tree — 将 pipeline_tree JSON 转换为标准节点列表"""

    def test_extract_basic_nodes(self):
        tree = {
            "nodes": [
                {"id": "node_1", "node_type": "atom", "atom_type": "shell", "label": "SSH", "x": 50, "y": 40, "max_retries": 2, "timeout_seconds": 30, "risk_level": "medium"},
                {"id": "node_2", "node_type": "exclusive_gateway", "label": "Condition?", "x": 300, "y": 40},
                {"id": "node_3", "node_type": "end_event", "label": "End", "x": 800, "y": 40},
            ],
            "edges": [],
        }
        nodes = extract_nodes_from_tree(tree)
        assert len(nodes) == 3

        # 原子节点
        n1 = nodes[0]
        assert n1["node_id"] == "node_1"
        assert n1["node_type"] == "atom"
        assert n1["atom_type"] == "shell"
        assert n1["position_x"] == 50
        assert n1["max_retries"] == 2
        assert n1["timeout_seconds"] == 30
        assert n1["risk_level"] == "medium"
        assert n1["is_subprocess"] is False

        # 网关节点
        n2 = nodes[1]
        assert n2["node_type"] == "exclusive_gateway"
        assert n2["atom_type"] == ""
        assert n2["max_retries"] == 0  # 默认值

        # 子流程节点
        subprocess_node = {"id": "sp_1", "node_type": "subprocess", "label": "SubTask"}
        tree["nodes"].append(subprocess_node)
        nodes = extract_nodes_from_tree(tree)
        sp = [n for n in nodes if n["node_type"] == "subprocess"][0]
        assert sp["is_subprocess"] is True

    def test_empty_tree(self):
        nodes = extract_nodes_from_tree({})
        assert nodes == []

    def test_none_nodes(self):
        nodes = extract_nodes_from_tree({"nodes": None})
        assert nodes == []

    def test_extract_node_config_strips_position(self):
        """验证 node_config 不包含 id/x/y（这些字段独立存储）"""
        tree = {
            "nodes": [
                {"id": "n1", "node_type": "atom", "atom_type": "shell",
                 "label": "Test", "x": 100, "y": 200, "params": {"cmd": "ls"}, "max_retries": 1},
            ],
            "edges": [],
        }
        nodes = extract_nodes_from_tree(tree)
        n = nodes[0]
        assert "id" not in n["node_config"]
        assert "x" not in n["node_config"]
        assert "y" not in n["node_config"]
        assert n["node_config"]["params"] == {"cmd": "ls"}
