"""Acyclic graph transformation — remove self-loops and reverse backward edges."""

from copy import deepcopy

from .constants import PK
from .utils import add_flow_id_to_node_io, delete_flow_id_from_node_io


def _detect_cycle(pipeline):
    """DFS-based cycle detection. Returns (has_cycle, [cycle_node_ids])."""
    adj = {}
    for flow_id, flow in pipeline[PK.flows].items():
        adj.setdefault(flow[PK.source], []).append(flow[PK.target])

    all_nodes = list(pipeline["all_nodes"].keys())
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in all_nodes}

    def dfs(nid, path):
        color[nid] = GRAY
        for neighbor in adj.get(nid, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                path.append(neighbor)
                return True, path
            elif color[neighbor] == WHITE:
                path.append(neighbor)
                has, p = dfs(neighbor, path)
                if has:
                    return True, p
                path.pop()
        color[nid] = BLACK
        return False, []

    for nid in all_nodes:
        if color[nid] == WHITE:
            has, path = dfs(nid, [nid])
            if has:
                return True, path
    return False, []


def remove_self_edges(pipeline):
    """Remove self-looping edges and store them for restoration."""
    self_edges = {}
    for flow_id, flow in list(pipeline[PK.flows].items()):
        if flow[PK.source] == flow[PK.target]:
            self_edges[flow_id] = flow
            pipeline[PK.flows].pop(flow_id)
            node_id = flow[PK.source]
            node = pipeline["all_nodes"].get(node_id)
            if node:
                delete_flow_id_from_node_io(node, flow_id, PK.incoming)
                delete_flow_id_from_node_io(node, flow_id, PK.outgoing)
    return self_edges


def insert_self_edges(pipeline, self_edges):
    """Restore previously removed self-loop edges."""
    pipeline[PK.flows].update(self_edges)
    for flow_id, flow in self_edges.items():
        node_id = flow[PK.source]
        node = pipeline["all_nodes"].get(node_id)
        if node:
            add_flow_id_to_node_io(node, flow_id, PK.incoming)
            add_flow_id_to_node_io(node, flow_id, PK.outgoing)


def acyclic_run(pipeline):
    """Reverse backward edges until graph is acyclic. Returns reversed flows."""
    # Build lookup: "{source}.{target}" → flow_id
    deformed = {
        f"{flow[PK.source]}.{flow[PK.target]}": flow_id
        for flow_id, flow in pipeline[PK.flows].items()
    }
    reversed_flows = {}

    while True:
        has_cycle, cycle_path = _detect_cycle(pipeline)
        if not has_cycle:
            break

        # The last two nodes in the cycle_path form one edge of the cycle
        source = cycle_path[-2]
        target = cycle_path[-1]
        key = f"{source}.{target}"
        flow_id = deformed.get(key)
        if flow_id is None:
            break

        reversed_flows[flow_id] = deepcopy(pipeline[PK.flows][flow_id])
        pipeline[PK.flows][flow_id].update({PK.source: target, PK.target: source})

        source_node = pipeline["all_nodes"].get(source)
        if source_node:
            delete_flow_id_from_node_io(source_node, flow_id, PK.outgoing)
            add_flow_id_to_node_io(source_node, flow_id, PK.incoming)

        target_node = pipeline["all_nodes"].get(target)
        if target_node:
            delete_flow_id_from_node_io(target_node, flow_id, PK.incoming)
            add_flow_id_to_node_io(target_node, flow_id, PK.outgoing)

    return reversed_flows


def acyclic_undo(pipeline, reversed_flows):
    """Restore previously reversed edges to their original direction."""
    pipeline[PK.flows].update(reversed_flows)
    for flow_id, flow in reversed_flows.items():
        source = flow[PK.source]
        source_node = pipeline["all_nodes"].get(source)
        if source_node:
            delete_flow_id_from_node_io(source_node, flow_id, PK.incoming)
            add_flow_id_to_node_io(source_node, flow_id, PK.outgoing)

        target = flow[PK.target]
        target_node = pipeline["all_nodes"].get(target)
        if target_node:
            delete_flow_id_from_node_io(target_node, flow_id, PK.outgoing)
            add_flow_id_to_node_io(target_node, flow_id, PK.incoming)
