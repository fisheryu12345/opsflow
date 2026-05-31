"""Unit tests for the Sugiyama layout engine.

Run with: python -m pytest opsflow/core/layout/tests.py
Or:       python -m django test opsflow.tests (for API integration tests)
"""

import sys
import os

# Allow running as standalone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from . import compute_layout
from .constants import OPSFLOW_NODE_TYPE_MAP, NodeType


def _pos_by_id(positions):
    return {p["id"]: p for p in positions}


def test_empty_graph():
    assert compute_layout([], []) == []


def test_single_node():
    result = compute_layout([{"id": "x1", "node_type": "", "name": "X"}], [])
    assert len(result) == 1
    assert result[0]["id"] == "x1"


def test_two_nodes():
    nodes = [
        {"id": "a", "node_type": ""},
        {"id": "b", "node_type": ""},
    ]
    edges = [{"from": "a", "to": "b"}]
    positions = compute_layout(nodes, edges)
    assert len(positions) >= 3  # auto-synthesized start + a + ... + end
    pos = _pos_by_id(positions)
    assert pos["a"]["x"] < pos["b"]["x"]


def test_serial_three():
    """3 serial nodes — x strictly increasing, y centered."""
    nodes = [
        {"id": "n1", "node_type": "start_event", "name": "start"},
        {"id": "n2", "node_type": "", "name": "task1"},
        {"id": "n3", "node_type": "end_event", "name": "end"},
    ]
    edges = [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]
    positions = compute_layout(nodes, edges)
    assert len(positions) == 3
    pos = _pos_by_id(positions)
    assert pos["n1"]["x"] < pos["n2"]["x"] < pos["n3"]["x"]


def test_branching():
    """1 start -> exclusive_gateway -> 2 tasks -> converge -> end"""
    nodes = [
        {"id": "s", "node_type": "start_event"},
        {"id": "g1", "node_type": "exclusive_gateway"},
        {"id": "a1", "node_type": "", "name": "A"},
        {"id": "a2", "node_type": "", "name": "B"},
        {"id": "g2", "node_type": "converge_gateway"},
        {"id": "e", "node_type": "end_event"},
    ]
    edges = [
        {"from": "s", "to": "g1"},
        {"from": "g1", "to": "a1"},
        {"from": "g1", "to": "a2"},
        {"from": "a1", "to": "g2"},
        {"from": "a2", "to": "g2"},
        {"from": "g2", "to": "e"},
    ]
    positions = compute_layout(nodes, edges)
    assert len(positions) == 6
    pos = _pos_by_id(positions)
    # Branch tasks should be at different y
    assert pos["a1"]["y"] != pos["a2"]["y"], "branch tasks should have different y"


def test_parallel_gateway():
    """start -> parallel_gateway -> 3 tasks -> converge -> end"""
    nodes = [
        {"id": "s", "node_type": "start_event"},
        {"id": "pg", "node_type": "parallel_gateway"},
        {"id": "t1", "node_type": "", "name": "T1"},
        {"id": "t2", "node_type": "", "name": "T2"},
        {"id": "t3", "node_type": "", "name": "T3"},
        {"id": "cg", "node_type": "converge_gateway"},
        {"id": "e", "node_type": "end_event"},
    ]
    edges = [
        {"from": "s", "to": "pg"},
        {"from": "pg", "to": "t1"},
        {"from": "pg", "to": "t2"},
        {"from": "pg", "to": "t3"},
        {"from": "t1", "to": "cg"},
        {"from": "t2", "to": "cg"},
        {"from": "t3", "to": "cg"},
        {"from": "cg", "to": "e"},
    ]
    positions = compute_layout(nodes, edges)
    assert len(positions) == 7
    pos = _pos_by_id(positions)
    # All three parallel tasks should be at different y
    ys = {pos[t]["y"] for t in ["t1", "t2", "t3"]}
    assert len(ys) == 3, f"expected 3 distinct y values, got {ys}"
    # start x < pg x < task x < converge x < end x
    assert pos["s"]["x"] < pos["pg"]["x"] < pos["t1"]["x"] < pos["cg"]["x"] < pos["e"]["x"]


def test_crossing_minimization():
    """Crossing minimization: lay out a graph known to have crossings."""
    # 2 left nodes -> 2 right nodes with crossing edges
    nodes = [
        {"id": "l1", "node_type": "", "name": "L1"},
        {"id": "l2", "node_type": "", "name": "L2"},
        {"id": "r1", "node_type": "", "name": "R1"},
        {"id": "r2", "node_type": "", "name": "R2"},
    ]
    edges = [
        {"from": "l1", "to": "r2"},
        {"from": "l2", "to": "r1"},
    ]
    positions = compute_layout(nodes, edges)
    assert len(positions) >= 4
    pos = _pos_by_id(positions)
    assert "x" in pos["l1"] and "x" in pos["l2"]
    assert "x" in pos["r1"] and "x" in pos["r2"]


def test_auto_synthesize_start_end():
    """Nodes without start/end should get auto-synthesized terminals."""
    nodes = [
        {"id": "a", "node_type": "", "name": "A"},
        {"id": "b", "node_type": "", "name": "B"},
    ]
    edges = [{"from": "a", "to": "b"}]
    positions = compute_layout(nodes, edges)
    # Should have 4 entries: auto-start + a + b + auto-end
    assert len(positions) == 4
    ids = {p["id"] for p in positions}
    assert "a" in ids and "b" in ids


def test_source_target_edge_format():
    """Support both source/target and from/to edge formats."""
    nodes = [
        {"id": "n1", "node_type": ""},
        {"id": "n2", "node_type": ""},
    ]
    edges = [{"source": "n1", "target": "n2"}]
    positions = compute_layout(nodes, edges)
    assert len(positions) >= 2


def test_type_mapping_completeness():
    """All OPSflow node_type values must map to a valid NodeType."""
    assert OPSFLOW_NODE_TYPE_MAP[""] == NodeType.ServiceActivity
    assert OPSFLOW_NODE_TYPE_MAP["start_event"] == NodeType.EmptyStartEvent
    assert OPSFLOW_NODE_TYPE_MAP["end_event"] == NodeType.EmptyEndEvent
    assert OPSFLOW_NODE_TYPE_MAP["exclusive_gateway"] == NodeType.ExclusiveGateway
    assert OPSFLOW_NODE_TYPE_MAP["parallel_gateway"] == NodeType.ParallelGateway
    assert (
        OPSFLOW_NODE_TYPE_MAP["conditional_parallel_gateway"]
        == NodeType.ConditionalParallelGateway
    )
    assert OPSFLOW_NODE_TYPE_MAP["converge_gateway"] == NodeType.ConvergeGateway


def test_conditional_parallel_gateway():
    """Conditional parallel gateway — branch + converge."""
    nodes = [
        {"id": "s", "node_type": "start_event"},
        {"id": "cpg", "node_type": "conditional_parallel_gateway"},
        {"id": "a", "node_type": "", "name": "A"},
        {"id": "b", "node_type": "", "name": "B"},
        {"id": "cg", "node_type": "converge_gateway"},
        {"id": "e", "node_type": "end_event"},
    ]
    edges = [
        {"from": "s", "to": "cpg"},
        {"from": "cpg", "to": "a"},
        {"from": "cpg", "to": "b"},
        {"from": "a", "to": "cg"},
        {"from": "b", "to": "cg"},
        {"from": "cg", "to": "e"},
    ]
    positions = compute_layout(nodes, edges)
    assert len(positions) == 6
    pos = _pos_by_id(positions)
    assert pos["a"]["y"] != pos["b"]["y"]


def test_no_negative_coordinates():
    """All coordinates should be non-negative."""
    nodes = [
        {"id": "n1", "node_type": "start_event"},
        {"id": "n2", "node_type": ""},
        {"id": "n3", "node_type": "end_event"},
    ]
    edges = [{"from": "n1", "to": "n2"}, {"from": "n2", "to": "n3"}]
    positions = compute_layout(nodes, edges)
    for p in positions:
        assert p["x"] >= 0, f"negative x: {p}"
        assert p["y"] >= 0, f"negative y: {p}"


def test_acyclic_with_cycle():
    """Graph with a cycle should still produce valid layout."""
    nodes = [
        {"id": "s", "node_type": "start_event"},
        {"id": "a", "node_type": "", "name": "A"},
        {"id": "b", "node_type": "", "name": "B"},
        {"id": "e", "node_type": "end_event"},
    ]
    # Intentional cycle: a -> b -> a
    edges = [
        {"from": "s", "to": "a"},
        {"from": "a", "to": "b"},
        {"from": "b", "to": "a"},  # back-edge
        {"from": "b", "to": "e"},
    ]
    positions = compute_layout(nodes, edges)
    assert len(positions) >= 4
    # All original nodes should have positions
    ids = {p["id"] for p in positions}
    for nid in ["s", "a", "b", "e"]:
        assert nid in ids, f"missing {nid} in positions"
