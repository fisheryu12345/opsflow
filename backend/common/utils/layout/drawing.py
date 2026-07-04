"""Main orchestrator — wires all 5 phases of the Sugiyama layout algorithm."""

from . import normalize, acyclic
from .rank import tight_tree
from .order import order
from .dummy import compute_nodes_fill_num, replace_long_path_with_dummy, remove_dummy
from . import position
from .constants import POSITION, CANVAS_WIDTH


def draw_pipeline(
    pipeline,
    activity_size=POSITION["activity_size"],
    event_size=POSITION["event_size"],
    gateway_size=POSITION["gateway_size"],
    start=POSITION["start"],
    canvas_width=CANVAS_WIDTH,
):
    """Execute the full Sugiyama layout pipeline on a pipeline tree.

    Phases:
        1. normalize — build flat all_nodes dict
        2. acyclic — remove self-loops, reverse back-edges
        3. rank — assign rank (layer) to each node (tight-tree)
        4. dummy — split long edges with dummy nodes
        5. order — minimize crossings (weighted-median)
        6. position — compute x,y coordinates + arrow endpoints

    :param pipeline: pipeline tree dict (must contain activities, gateways,
                     flows, start_event, end_event)
    :param activity_size: (width, height) for task nodes
    :param event_size: (width, height) for event nodes
    :param gateway_size: (width, height) for gateway nodes
    :param start: (x, y) starting position
    :param canvas_width: max canvas width
    :returns: None — pipeline is updated in-place with "location" and "line" keys
    """
    # 1. Normalize: build all_nodes lookup
    normalize.normalize_run(pipeline)

    # 2. Acyclic: remove self-loops, reverse back-edges
    self_edges = acyclic.remove_self_edges(pipeline)
    reversed_flows = acyclic.acyclic_run(pipeline)

    # 3. Rank: assign layers via tight-tree (longest-path + feasible-tree)
    ranks = tight_tree.tight_tree_ranker(pipeline)

    # 4. Dummy: split long edges with dummy node chains
    real_flows_chain = replace_long_path_with_dummy(pipeline, ranks)

    # 5. Order: minimize crossings via weighted-median heuristic
    orders = order.ordering(pipeline, ranks)

    # 6. Compute fill numbers for gateway branch spacing
    nodes_fill_nums = compute_nodes_fill_num(pipeline, orders)

    # Restore self-loops (they don't affect layout geometry)
    acyclic.insert_self_edges(pipeline, self_edges)

    # Merge real_flows_chain and reversed_flows for line computation
    more_flows = {}
    more_flows.update(real_flows_chain)
    more_flows.update(reversed_flows)

    # 7. Position: compute x,y and arrow endpoints
    locations, lines = position.position(
        pipeline=pipeline,
        orders=orders,
        activity_size=activity_size,
        event_size=event_size,
        gateway_size=gateway_size,
        start=start,
        canvas_width=canvas_width,
        more_flows=more_flows,
        nodes_fill_nums=nodes_fill_nums,
    )

    # Cleanup: remove dummy nodes, restore long edges and reversed edges
    remove_dummy(pipeline, real_flows_chain, dummy_nodes_included=[locations], dummy_flows_included=[lines])
    acyclic.acyclic_undo(pipeline, reversed_flows)
    normalize.normalize_undo(pipeline)

    # Attach results to pipeline
    pipeline.update({"location": list(locations.values()), "line": list(lines.values())})
