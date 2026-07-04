"""Feasible-tree rank refinement — minimize total edge length."""

from ..constants import PK
from ..utils import format_to_list
from .utils import slack


def feasible_tree_ranker(pipeline, ranks):
    """
    Refine ranks by building a spanning tree of tight edges,
    then shifting to make more edges tight (slack = 0).
    """
    part_tree = {
        "all_nodes": {pipeline[PK.start_event][PK.id]: pipeline[PK.start_event]},
        PK.flows: {},
    }

    node_count = len(pipeline["all_nodes"])
    while _tight_tree(part_tree, pipeline, ranks) < node_count:
        flow = _find_min_slack_flow(part_tree, pipeline, ranks)
        if flow is None:
            break
        delta = slack(ranks, flow)
        if flow[PK.target] in part_tree["all_nodes"]:
            delta = -delta
        _shift_ranks(ranks, list(part_tree["all_nodes"].keys()), delta)

    return ranks


def _tight_tree(part_tree, pipeline, ranks):
    """Grow a spanning tree of tight edges (slack=0) from current partial tree."""

    def dfs(node):
        for direction in [PK.outgoing, PK.incoming]:
            for flow_id in format_to_list(node.get(direction, "")):
                if flow_id not in pipeline[PK.flows]:
                    continue
                flow = pipeline[PK.flows][flow_id]
                direct_key = PK.target if direction == PK.outgoing else PK.source
                direct_node_id = flow[direct_key]
                direct_node = pipeline["all_nodes"].get(direct_node_id)
                if direct_node_id not in part_tree["all_nodes"] and slack(ranks, flow) == 0:
                    part_tree["all_nodes"][direct_node_id] = direct_node
                    part_tree[PK.flows][flow_id] = flow
                    dfs(direct_node)

    for node in list(part_tree["all_nodes"].values()):
        dfs(node)
    return len(part_tree["all_nodes"])


def _find_min_slack_flow(part_tree, pipeline, ranks):
    """Find edge with minimum slack connecting tree to non-tree."""
    if not ranks:
        return None
    min_slack = max(ranks.values()) - min(ranks.values()) if ranks else 1
    min_slack_flow = None
    for flow_id, flow in pipeline[PK.flows].items():
        in_tree_s = flow[PK.source] in part_tree["all_nodes"]
        in_tree_t = flow[PK.target] in part_tree["all_nodes"]
        if in_tree_s != in_tree_t:
            s = slack(ranks, flow)
            if s < min_slack:
                min_slack = s
                min_slack_flow = flow
    return min_slack_flow


def _shift_ranks(ranks, node_ids, delta):
    """Shift ranks of all nodes in the set by delta."""
    for node_id in node_ids:
        ranks[node_id] += delta
