"""Utility functions for flow ID management on nodes."""

from .constants import PK, NodeType


def format_to_list(value):
    """Normalize incoming/outgoing to list."""
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [value]


def add_flow_id_to_node_io(node, flow_id, io_type):
    """Add flow_id to node's incoming or outgoing list."""
    if isinstance(node[io_type], list):
        node[io_type].append(flow_id)
    elif node[io_type]:
        node[io_type] = [node[io_type], flow_id]
    else:
        node[io_type] = flow_id


def delete_flow_id_from_node_io(node, flow_id, io_type):
    """Remove flow_id from node's incoming or outgoing list."""
    if node[io_type] == flow_id:
        node[io_type] = ""
    elif isinstance(node[io_type], list):
        if len(node[io_type]) == 1 and node[io_type][0] == flow_id:
            node[io_type] = (
                ""
                if node.get(PK.type) not in [
                    NodeType.ExclusiveGateway,
                    NodeType.ParallelGateway,
                    NodeType.ConditionalParallelGateway,
                ]
                else []
            )
        else:
            node[io_type].pop(node[io_type].index(flow_id))
            if (
                len(node[io_type]) == 1
                and io_type == PK.outgoing
                and node.get(PK.type) in [
                    NodeType.EmptyStartEvent,
                    NodeType.ServiceActivity,
                    NodeType.ConvergeGateway,
                ]
            ):
                node[io_type] = node[io_type][0]
