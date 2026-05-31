"""Coordinate assignment with arrow endpoint calculation."""

import copy
import uuid

from .constants import PK, MIN_LEN, DUMMY_NODE_TYPE
from .constants import NodeType


def _line_uniqid():
    return "l" + uuid.uuid4().hex


def _upsert_orders(orders, nodes_fill_nums):
    """Insert placeholder dummy slots into orders for gateway branch spacing."""
    new_orders = copy.deepcopy(orders)
    dummy_nodes = []
    for order in orders:
        if order in nodes_fill_nums:
            dummy_nodes_list = [
                _line_uniqid() for _ in range(0, nodes_fill_nums[order])
            ]
            dummy_nodes.extend(dummy_nodes_list)
            index = new_orders.index(order)
            new_orders = (
                new_orders[: index + 1]
                + dummy_nodes_list
                + new_orders[index + 1 :]
            )
    return new_orders, dummy_nodes


def position(
    pipeline,
    orders,
    activity_size,
    event_size,
    gateway_size,
    start,
    canvas_width,
    more_flows=None,
    nodes_fill_nums=None,
):
    """Assign x,y coordinates to all nodes and compute arrow endpoints for flows.

    :param pipeline: pipeline tree with all_nodes
    :param orders: dict {rank: [node_id, ...]} — per-rank node ordering
    :param activity_size: (width, height) for activity nodes
    :param event_size: (width, height) for event nodes
    :param gateway_size: (width, height) for gateway nodes
    :param start: (x, y) starting position
    :param canvas_width: max canvas width before line wrap
    :param more_flows: extra flows to compute line positions for
    :param nodes_fill_nums: extra vertical slots per node
    :returns: (locations_dict, lines_dict)
    """
    size_x = max(activity_size[0], event_size[0], gateway_size[0])
    shift_y = int(max(activity_size[1], event_size[1], gateway_size[1]) * 3)
    event_shift_y = int((activity_size[1] - event_size[1]) * 0.5)
    gateway_shift_y = int((activity_size[1] - gateway_size[1]) * 0.5)

    pipeline_element_shift_y = {
        DUMMY_NODE_TYPE: 0,
        NodeType.ServiceActivity: 0,
        NodeType.EmptyStartEvent: event_shift_y,
        NodeType.EmptyEndEvent: event_shift_y,
        NodeType.ExclusiveGateway: gateway_shift_y,
        NodeType.ConditionalParallelGateway: gateway_shift_y,
        NodeType.ParallelGateway: gateway_shift_y,
        NodeType.ConvergeGateway: gateway_shift_y,
    }

    pipeline_element_shift_x = {
        DUMMY_NODE_TYPE: 0,
        NodeType.ServiceActivity: activity_size[0] * 1.5,
        NodeType.EmptyStartEvent: event_size[0] * 2.5,
        NodeType.EmptyEndEvent: event_size[0] * 2.5,
        NodeType.ExclusiveGateway: gateway_size[0] * 6.5,
        NodeType.ConditionalParallelGateway: gateway_size[0] * 6.5,
        NodeType.ParallelGateway: gateway_size[0] * 2.5,
        NodeType.ConvergeGateway: gateway_size[0] * 2.5,
    }

    min_rk = min(orders.keys())
    max_rk = max(orders.keys())

    old_locations = {
        location["id"]: location for location in pipeline.get("location", [])
    }
    locations = {}
    rank_x, rank_y = start
    new_line_y = 0

    for rk in range(min_rk, max_rk + MIN_LEN, MIN_LEN):
        shift_x = 0
        layer_nodes = orders[rk]
        layer_nodes, dummy_nodes = _upsert_orders(layer_nodes, nodes_fill_nums)
        order_x, order_y = rank_x, rank_y
        if new_line_y == 0:
            new_line_y = rank_y + shift_y

        for node_id in layer_nodes:
            if node_id in pipeline["all_nodes"]:
                node = pipeline["all_nodes"][node_id]
                node_y = int(order_y + pipeline_element_shift_y[node[PK.type]])
                node_x = int(order_x)

                shift_x = max(
                    pipeline_element_shift_x.get(
                        pipeline["all_nodes"][node_id][PK.type], shift_x
                    ),
                    shift_x,
                )
                if node_id in old_locations:
                    locations[node_id] = copy.deepcopy(old_locations[node_id])
                    locations[node_id].update({"x": node_x, "y": node_y})
                elif node_id not in dummy_nodes:
                    locations[node_id] = {
                        "id": node_id,
                        "type": node[PK.type],
                        "name": node.get(PK.name, ""),
                        PK.status: "",
                        "x": node_x,
                        "y": node_y,
                    }
                if node_y >= new_line_y:
                    new_line_y = node_y + shift_y
            order_y += shift_y

        rank_x = rank_x + shift_x
        # line wrap if exceeded canvas width and only one real node in layer
        if (
            rank_x + size_x > canvas_width
            and (len(layer_nodes) - len(dummy_nodes)) == 1
            and rk < max_rk - MIN_LEN
        ):
            rank_x = start[0]
            rank_y = new_line_y

    flows = {}
    flows.update(pipeline[PK.flows])
    if isinstance(more_flows, dict):
        flows.update(more_flows)
    lines = _position_flows(flows, locations, pipeline_element_shift_y, start[0], shift_y)
    return locations, lines


def _position_flows(flows, locations, pipeline_element_shift_y, start_x, shift_y):
    """Compute arrow endpoints for all flows."""
    lines = {}
    for flow_id, flow in flows.items():
        source_arrow, target_arrow = _arrow_flow(flow, locations, pipeline_element_shift_y)
        lines[flow_id] = {
            "id": flow_id,
            "source": {"arrow": source_arrow, "id": flow[PK.source]},
            "target": {"arrow": target_arrow, "id": flow[PK.target]},
        }
        if flow[PK.source] not in locations or flow[PK.target] not in locations:
            continue
        source_location = locations[flow[PK.source]]
        target_location = locations[flow[PK.target]]
        if target_location["x"] == start_x:
            lines[flow_id]["midpoint"] = (
                1 - shift_y * 0.5 / (target_location["y"] - source_location["y"])
            )
    return lines


def _arrow_flow(flow, locations, pipeline_element_shift_y):
    """Determine arrow endpoints based on relative positions of source and target."""
    source_location = locations[flow[PK.source]]
    target_location = locations[flow[PK.target]]

    source_location_x = source_location["x"]
    source_location_y = source_location["y"]

    target_location_x = target_location["x"]
    target_location_y = target_location["y"]

    if source_location_x < target_location_x:
        if source_location_y < target_location_y:
            source_arrow = "bottom"
            target_arrow = "left"
        elif source_location_y > target_location_y:
            source_arrow = "right"
            target_arrow = "bottom"
        else:
            source_arrow = "right"
            target_arrow = "left"
    elif source_location_x > target_location_x:
        if source_location_y < target_location_y:
            source_arrow = "right"
            target_arrow = "left"
        else:
            source_arrow = "bottom"
            target_arrow = "bottom"
    else:
        if source_location_y < target_location_y:
            source_arrow = "bottom"
            target_arrow = "top"
        elif source_location_y > target_location_y:
            source_arrow = "top"
            target_arrow = "bottom"
        else:
            source_arrow = "right"
            target_arrow = "bottom"
    return source_arrow, target_arrow
