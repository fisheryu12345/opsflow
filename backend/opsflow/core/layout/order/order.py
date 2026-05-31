"""Crossing minimization via weighted-median heuristic (Sugiyama)."""

from copy import deepcopy

from ..constants import PK, MIN_LEN
from ..utils import format_to_list
from ..rank.utils import max_rank, min_rank

MAX_ORDERING_LOOP = 24


def ordering(pipeline, ranks):
    """
    Assign node order within each rank to minimize edge crossings.
    Uses the weighted-median heuristic with up to 24 iterations.
    """
    orders = init_order(pipeline, ranks)
    best = deepcopy(orders)
    best_count = crossing_count(pipeline, best)
    for loop in range(MAX_ORDERING_LOOP):
        wmedian(pipeline, orders, loop, ranks)
        count = crossing_count(pipeline, orders)
        if count < best_count:
            best = deepcopy(orders)
            best_count = count
        elif loop % 2 == 0:
            break
    return best


def init_order(pipeline, ranks):
    """Initialize per-rank node ordering via topological traversal from start."""
    orders = {rk: [] for rk in set(ranks.values())}
    rk = min_rank(ranks)
    orders[rk] = [node_id for node_id, node_rk in ranks.items() if node_rk == rk]

    while rk < max_rank(ranks):
        next_rk = rk + MIN_LEN
        for node_id in orders[rk]:
            node = pipeline["all_nodes"].get(node_id)
            if node is None:
                continue
            for flow_id in format_to_list(node.get(PK.outgoing, "")):
                flow = pipeline[PK.flows].get(flow_id)
                if flow is None:
                    continue
                target = flow[PK.target]
                if target not in orders.get(next_rk, []):
                    if next_rk not in orders:
                        orders[next_rk] = []
                    if flow.get(PK.type) == "DummyFlow":
                        orders[next_rk].insert(0, target)
                    else:
                        orders[next_rk].append(target)
        rk = next_rk
    return orders


def wmedian(pipeline, orders, loop, ranks):
    """Apply weighted-median heuristic in alternating direction."""
    min_rk = min_rank(ranks)
    max_rk = max_rank(ranks)

    if loop % 2 == 0:
        # Top-down: compute median from predecessors
        for r in range(min_rk + MIN_LEN, max_rk + MIN_LEN, MIN_LEN):
            medians = []
            for node_id in orders[r]:
                refs = refer_node_ids(pipeline, node_id, PK.incoming)
                medians.append(median_value(refs, orders[r - MIN_LEN]))
            orders[r] = sort_layer(orders[r], medians)
    else:
        # Bottom-up: compute median from successors
        for r in range(max_rk - MIN_LEN, min_rk - MIN_LEN, -MIN_LEN):
            medians = []
            for node_id in orders[r]:
                refs = refer_node_ids(pipeline, node_id, PK.outgoing)
                medians.append(median_value(refs, orders[r + MIN_LEN]))
            orders[r] = sort_layer(orders[r], medians)


def refer_node_ids(pipeline, node_id, io):
    """Get connected node IDs in adjacent layer (incoming → source, outgoing → target)."""
    node = pipeline["all_nodes"].get(node_id)
    if node is None:
        return []
    flow_direction = PK.source if io == PK.incoming else PK.target
    refs = []
    for flow_id in format_to_list(node.get(io, "")):
        flow = pipeline[PK.flows].get(flow_id)
        if flow:
            refs.append(flow[flow_direction])
    return refs


def median_value(refer_nodes, refer_layer_orders):
    """Compute median position of reference nodes in adjacent layer."""
    indices = sorted([refer_layer_orders.index(ref) for ref in refer_nodes if ref in refer_layer_orders])
    if not indices:
        return -1
    n = len(indices)
    if n % 2 == 1:
        return indices[n // 2]
    return (indices[n // 2 - 1] + indices[n // 2]) / 2


def sort_layer(layer_order, weights):
    """
    Sort nodes by weight. Nodes with weight -1 keep their original positions.
    e.g. layer=['a','b','c'], weights=[3, -1, 1] → ['c', 'b', 'a']
    """
    to_sort = []
    persist = []
    for idx, item in enumerate(layer_order):
        if weights[idx] == -1:
            persist.append((item, idx))
        else:
            to_sort.append((item, weights[idx]))
    to_sort.sort(key=lambda x: x[1])
    result = [item[0] for item in to_sort]
    for item, idx in persist:
        result.insert(idx, item)
    return result


def crossing_count(pipeline, orders):
    """Count edge crossings between adjacent ranks."""
    count = 0
    rk_min = min(orders.keys())
    rk_max = max(orders.keys())
    for rk in range(rk_min, rk_max, MIN_LEN):
        current = orders[rk]
        nxt = orders[rk + MIN_LEN]
        flows_between = [
            flow for flow in pipeline[PK.flows].values()
            if flow[PK.source] in current and flow[PK.target] in nxt
        ]
        for i in range(len(flows_between) - 1):
            f1 = flows_between[i]
            s1_idx = current.index(f1[PK.source])
            t1_idx = nxt.index(f1[PK.target])
            for j in range(i + 1, len(flows_between)):
                f2 = flows_between[j]
                s2_idx = current.index(f2[PK.source])
                t2_idx = nxt.index(f2[PK.target])
                if (s1_idx - s2_idx) * (t1_idx - t2_idx) < 0:
                    count += 1
    return count
