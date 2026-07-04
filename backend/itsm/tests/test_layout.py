"""Layout engine 测试 — Sugiyama 布局计算"""
from django.test import TestCase


class ComputeLayoutTests(TestCase):
    """布局引擎基本功能"""

    def test_empty_nodes_returns_empty(self):
        """空节点列表返回空列表（不抛异常）"""
        from common.utils.layout import compute_layout
        positions = compute_layout([], [], canvas_width=2800)
        self.assertEqual(len(positions), 0)

    def test_single_node(self):
        """单个节点正确返回坐标"""
        from common.utils.layout import compute_layout
        nodes = [{'id': '1', 'node_type': 'start_event', 'name': '开始'}]
        positions = compute_layout(nodes, [],
                                   activity_size=(280, 72),
                                   event_size=(56, 56),
                                   gateway_size=(70, 70),
                                   start=(80, 80),
                                   canvas_width=2800)
        self.assertGreaterEqual(len(positions), 1)
        pos1 = next(p for p in positions if p['id'] == '1')
        self.assertIn('x', pos1)
        self.assertIn('y', pos1)

    def test_two_nodes_with_edge(self):
        """两个节点连线返回不同坐标"""
        from common.utils.layout import compute_layout
        nodes = [
            {'id': '1', 'node_type': 'start_event', 'name': '开始'},
            {'id': '2', 'node_type': '', 'name': '填单'},
        ]
        edges = [{'id': 'e1', 'source': '1', 'target': '2'}]
        positions = compute_layout(nodes, edges,
                                   activity_size=(280, 72),
                                   event_size=(56, 56),
                                   gateway_size=(70, 70),
                                   start=(80, 80),
                                   canvas_width=2800)
        # 布局引擎可能创建 dummy 节点，至少包含原始 2 个节点
        node_ids = {p['id'] for p in positions}
        self.assertIn('1', node_ids)
        self.assertIn('2', node_ids)
        # 两个节点坐标不同
        pos1 = next(p for p in positions if p['id'] == '1')
        pos2 = next(p for p in positions if p['id'] == '2')
        self.assertNotEqual((pos1['x'], pos1['y']), (pos2['x'], pos2['y']))
