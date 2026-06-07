"""OPSflow {nodes, edges} <-> pipeline tree format bridge."""

import uuid
import logging

from .constants import PK, OPSFLOW_NODE_TYPE_MAP, OPSFLOW_NODE_TYPE_MAP_REVERSE
from .constants import NodeType, POSITION, CANVAS_WIDTH
from .drawing import draw_pipeline

logger = logging.getLogger(__name__)


def _node_id():
    return "n" + uuid.uuid4().hex


def _flow_id():
    return "l" + uuid.uuid4().hex


def opsflow_to_pipeline(nodes, edges):
    """Convert OPSflow {nodes, edges} to a pipeline tree dict.

    Each OPSflow node:
        {id, node_type, name, ...}

    Each OPSflow edge:
        {id, source, target, ...}

    Returns a pipeline dict compatible with draw_pipeline().
    """
    # Separate nodes by type
    start_event = None
    end_event = None
    activities = {}
    gateways = {}
    for node in nodes:
        nid = node["id"]
        node_type = OPSFLOW_NODE_TYPE_MAP.get(
            node.get("node_type", ""), NodeType.ServiceActivity
        )
        entry = {
            PK.id: nid,
            PK.type: node_type,
            PK.name: node.get("name", ""),
            PK.incoming: "",
            PK.outgoing: "",
        }

        if node_type == NodeType.EmptyStartEvent:
            start_event = entry
        elif node_type == NodeType.EmptyEndEvent:
            end_event = entry
        elif node_type in (
            NodeType.ExclusiveGateway,
            NodeType.ParallelGateway,
            NodeType.ConditionalParallelGateway,
            NodeType.ConvergeGateway,
        ):
            gateways[nid] = entry
        else:
            activities[nid] = entry

    # Auto-synthesize start/end if missing
    if start_event is None and activities:
        sid = _node_id()
        start_event = {
            PK.id: sid,
            PK.type: NodeType.EmptyStartEvent,
            PK.name: "start",
            PK.incoming: "",
            PK.outgoing: "",
        }

    if end_event is None and activities:
        eid = _node_id()
        end_event = {
            PK.id: eid,
            PK.type: NodeType.EmptyEndEvent,
            PK.name: "end",
            PK.incoming: "",
            PK.outgoing: "",
        }

    # Build a unified lookup of all nodes (including start/end) for edge processing
    all_node_dict = {}
    if start_event:
        all_node_dict[start_event[PK.id]] = start_event
    if end_event:
        all_node_dict[end_event[PK.id]] = end_event
    all_node_dict.update(activities)
    all_node_dict.update(gateways)

    # Build flows — support both source/target and from/to formats
    flows = {}
    for edge in edges:
        fid = edge.get("id", _flow_id())
        source = edge.get("source") or edge.get("from", "")
        target = edge.get("target") or edge.get("to", "")
        if not source or not target:
            continue
        flows[fid] = {
            PK.id: fid,
            PK.type: "",
            PK.source: source,
            PK.target: target,
        }
        # Update incoming/outgoing for ALL matching nodes
        if source in all_node_dict:
            _append_to_io(all_node_dict[source], PK.outgoing, fid)
        if target in all_node_dict:
            _append_to_io(all_node_dict[target], PK.incoming, fid)

    # Auto-wire: connect start_event to root nodes and leaf nodes to end_event
    if start_event and activities:
        eid = start_event[PK.id]
        existing_out = set()
        for f in flows.values():
            if f[PK.source] == eid:
                existing_out.add(f[PK.target])
        first_nodes = [
            nid for nid, n in activities.items()
            if not n[PK.incoming] and nid != eid
        ]
        for fnid in first_nodes:
            if fnid not in existing_out:
                fid = _flow_id()
                flows[fid] = {
                    PK.id: fid, PK.type: "",
                    PK.source: eid, PK.target: fnid,
                }
                _append_to_io(start_event, PK.outgoing, fid)
                _append_to_io(all_node_dict[fnid], PK.incoming, fid)

    if end_event and activities:
        eid = end_event[PK.id]
        existing_in = set()
        for f in flows.values():
            if f[PK.target] == eid:
                existing_in.add(f[PK.source])
        last_nodes = [
            nid for nid, n in activities.items()
            if not n[PK.outgoing] and nid != eid
        ]
        for lnid in last_nodes:
            if lnid not in existing_in:
                fid = _flow_id()
                flows[fid] = {
                    PK.id: fid, PK.type: "",
                    PK.source: lnid, PK.target: eid,
                }
                _append_to_io(all_node_dict[lnid], PK.outgoing, fid)
                _append_to_io(end_event, PK.incoming, fid)

    pipeline = {
        PK.start_event: start_event,
        PK.end_event: end_event,
        PK.activities: activities,
        PK.gateways: gateways,
        PK.flows: flows,
    }
    return pipeline


def _append_to_io(node, io_type, flow_id):
    """Append flow_id to node's incoming or outgoing (supports string|list)."""
    current = node.get(io_type, "")
    if not current:
        node[io_type] = flow_id
    elif isinstance(current, list):
        current.append(flow_id)
    else:
        node[io_type] = [current, flow_id]


def pipeline_to_positions(pipeline):
    """Extract [{id, x, y}] from pipeline after draw_pipeline()."""
    locations = pipeline.get("location", [])
    positions = []
    for loc in locations:
        positions.append({
            "id": loc["id"],
            "x": loc["x"],
            "y": loc["y"],
        })
    return positions


def compute_layout(nodes, edges, **kwargs):
    """Full layout computation: OPSflow format in -> positions out.

    :param nodes: list of {id, node_type, name, ...}
    :param edges: list of {id, source, target, ...}
    :param kwargs: optional overrides for activity_size, event_size,
                   gateway_size, start, canvas_width
    :returns: list of {id, x, y}
    :raises ValueError: on invalid input
    """
    if not nodes:
        return []

    if len(nodes) <= 1:
        # Single node: place at start position
        start = kwargs.get("start", POSITION["start"])
        return [{"id": nodes[0]["id"], "x": start[0], "y": start[1]}]

    pipeline = opsflow_to_pipeline(nodes, edges)

    activity_size = kwargs.get("activity_size", POSITION["activity_size"])
    event_size = kwargs.get("event_size", POSITION["event_size"])
    gateway_size = kwargs.get("gateway_size", POSITION["gateway_size"])
    start = kwargs.get("start", POSITION["start"])
    canvas_width = kwargs.get("canvas_width", CANVAS_WIDTH)

    draw_pipeline(
        pipeline,
        activity_size=activity_size,
        event_size=event_size,
        gateway_size=gateway_size,
        start=start,
        canvas_width=canvas_width,
    )

    return pipeline_to_positions(pipeline)
