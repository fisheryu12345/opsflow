"""Long-edge splitting with dummy nodes + gateway fill-number computation."""

import uuid

from .constants import PK, DUMMY_NODE_TYPE, DUMMY_FLOW_TYPE, MIN_LEN, NodeType
from .rank.utils import slack
from .utils import delete_flow_id_from_node_io, add_flow_id_to_node_io, format_to_list


def _line_uniqid():
    return "l" + uuid.uuid4().hex


def _node_uniqid():
    return "n" + uuid.uuid4().hex


def replace_long_path_with_dummy(pipeline, ranks):
    """Replace edges spanning >1 rank with chains of DummyNode -> DummyFlow."""
    real_flows_chain = {}
    for flow_id, flow in list(pipeline[PK.flows].items()):
        flow_slack = slack(ranks, flow)
        if flow_slack > 0:
            real_flows_chain[flow_id] = flow
            dummy_nodes_ranks = range(
                ranks[flow[PK.source]] + MIN_LEN, ranks[flow[PK.target]], MIN_LEN
            )

            incoming_flow_id = _line_uniqid()
            dummy_node_id = _node_uniqid()
            dummy_flow = {
                PK.id: incoming_flow_id,
                PK.type: DUMMY_FLOW_TYPE,
                PK.source: flow[PK.source],
                PK.target: dummy_node_id,
            }
            # change outgoing of flow.source node
            delete_flow_id_from_node_io(
                pipeline["all_nodes"][flow[PK.source]], flow_id, PK.outgoing
            )
            add_flow_id_to_node_io(
                pipeline["all_nodes"][flow[PK.source]], incoming_flow_id, PK.outgoing
            )
            # delete long path flow from pipeline
            pipeline[PK.flows].pop(flow_id)
            for node_rank in dummy_nodes_ranks:
                # generate current dummy node's outgoing flow
                outgoing_flow_id = _line_uniqid()
                dummy_node = {
                    PK.id: dummy_node_id,
                    PK.type: DUMMY_NODE_TYPE,
                    PK.name: DUMMY_NODE_TYPE,
                    PK.incoming: incoming_flow_id,
                    PK.outgoing: outgoing_flow_id,
                }

                # add dummy to pipeline
                pipeline["all_nodes"].update({dummy_node_id: dummy_node})
                pipeline[PK.flows].update({incoming_flow_id: dummy_flow})

                # add dummy to ranks
                ranks.update({dummy_node_id: node_rank})

                # next loop init data
                incoming_flow_id = outgoing_flow_id
                dummy_node_id = _node_uniqid()
                dummy_flow = {
                    PK.id: incoming_flow_id,
                    PK.type: DUMMY_FLOW_TYPE,
                    PK.source: dummy_node[PK.id],
                    PK.target: dummy_node_id,
                }

            # add last dummy flow to pipeline
            dummy_flow[PK.target] = flow[PK.target]
            pipeline[PK.flows].update({incoming_flow_id: dummy_flow})
            # change incoming of flow.target node
            delete_flow_id_from_node_io(
                pipeline["all_nodes"][flow[PK.target]], flow_id, PK.incoming
            )
            add_flow_id_to_node_io(
                pipeline["all_nodes"][flow[PK.target]], incoming_flow_id, PK.incoming
            )
    return real_flows_chain


def _compute_sorted_list_by_order(orders, dummy_nums_dict):
    """Return node ids sorted by their position in orders."""
    result = []
    for index, nodes in orders.items():
        for node_id in dummy_nums_dict:
            if node_id in nodes:
                result.append(node_id)
    return result


def _compute_node_right_to_left(pipeline, incoming, value, nodes_dummy_nums):
    """Walk right-to-left from a gateway, propagating fill num to upstream nodes."""
    node_id = pipeline[PK.flows][incoming][PK.source]
    if node_id not in pipeline[PK.activities]:
        return
    nodes_dummy_nums[node_id] = value
    for item in format_to_list(pipeline[PK.activities][node_id].get(PK.incoming, "")):
        _compute_node_right_to_left(pipeline, item, value, nodes_dummy_nums)


def _compute_node_left_to_right(pipeline, outgoing, value, nodes_dummy_nums):
    """Walk left-to-right, propagating fill num through dummy nodes."""
    flow = pipeline[PK.flows].get(outgoing)
    if flow is None:
        return
    node_id = flow[PK.target]
    node = pipeline["all_nodes"].get(node_id)
    if node is None:
        return
    if node.get(PK.type) == DUMMY_NODE_TYPE:
        nodes_dummy_nums[node_id] = value
        _compute_node_left_to_right(
            pipeline, node.get(PK.outgoing, ""), value, nodes_dummy_nums
        )


def compute_nodes_fill_num(pipeline, orders):
    """Calculate extra vertical slots needed at each position for gateway branches."""
    gateways = pipeline[PK.gateways]
    final_dummy_nums = {}

    # Initialize: gateway fill = outgoing/incoming count - 1
    for gateway_id, gateway in gateways.items():
        gtype = gateway[PK.type]
        if gtype in [
            NodeType.ExclusiveGateway,
            NodeType.ParallelGateway,
            NodeType.ConditionalParallelGateway,
        ]:
            final_dummy_nums[gateway_id] = len(format_to_list(gateway[PK.outgoing])) - 1
        if gtype == NodeType.ConvergeGateway:
            final_dummy_nums[gateway_id] = len(format_to_list(gateway[PK.incoming])) - 1

    # Propagate fill nums upstream through activity chains
    nodes_dummy_nums = {}
    for gateway_id, gateway in gateways.items():
        gtype = gateway[PK.type]
        if gtype in [
            NodeType.ExclusiveGateway,
            NodeType.ParallelGateway,
            NodeType.ConditionalParallelGateway,
        ]:
            for incoming in format_to_list(gateway[PK.incoming]):
                value = len(format_to_list(gateway[PK.outgoing])) - 1
                source_id = pipeline[PK.flows][incoming][PK.source]
                nodes_dummy_nums[source_id] = value
                _compute_node_right_to_left(
                    pipeline, incoming, value, nodes_dummy_nums
                )

    nodes_orders_list = _compute_sorted_list_by_order(orders, nodes_dummy_nums)

    # Accumulate: if a node is upstream of a gateway, add its fill to the gateway
    for node_id in reversed(nodes_orders_list):
        if node_id in pipeline[PK.activities]:
            for incoming in format_to_list(
                pipeline[PK.activities][node_id].get(PK.incoming, "")
            ):
                source_id = pipeline[PK.flows][incoming][PK.source]
                if source_id in final_dummy_nums:
                    value = final_dummy_nums[source_id] + nodes_dummy_nums[node_id]
                    final_dummy_nums[source_id] = value
                    gateway = gateways[source_id]
                    if gateway[PK.type] in [
                        NodeType.ExclusiveGateway,
                        NodeType.ParallelGateway,
                        NodeType.ConditionalParallelGateway,
                    ]:
                        for gi in format_to_list(gateway[PK.incoming]):
                            _compute_node_right_to_left(
                                pipeline, gi, value, nodes_dummy_nums
                            )

    # Sync converge gateways with their branch gateways
    converge_gateway_node_nums = {}
    for gateway_id, value in final_dummy_nums.items():
        gateway = gateways[gateway_id]
        if gateway[PK.type] in [
            NodeType.ExclusiveGateway,
            NodeType.ParallelGateway,
            NodeType.ConditionalParallelGateway,
        ]:
            converge_id = gateway.get("converge_gateway_id")
            if converge_id:
                converge_gateway_node_nums[converge_id] = value

    final_dummy_nums.update(converge_gateway_node_nums)
    final_dummy_nums.update(nodes_dummy_nums)

    # Propagate through dummy nodes
    dummy_node_nums = {}
    for node_id, node in pipeline["all_nodes"].items():
        if node.get(PK.type) == DUMMY_NODE_TYPE:
            incoming_flow = pipeline[PK.flows].get(node.get(PK.incoming, ""))
            if incoming_flow:
                source_id = incoming_flow[PK.source]
                if source_id in final_dummy_nums:
                    dummy_node_nums[node_id] = final_dummy_nums[source_id]
                    _compute_node_left_to_right(
                        pipeline,
                        node.get(PK.outgoing, ""),
                        final_dummy_nums[source_id],
                        dummy_node_nums,
                    )

    final_dummy_nums.update(dummy_node_nums)
    return final_dummy_nums


def remove_dummy(
    pipeline,
    real_flows_chain,
    dummy_nodes_included=None,
    dummy_flows_included=None,
):
    """Remove dummy nodes/flows and restore long edges."""
    if dummy_nodes_included is None:
        dummy_nodes_included = []
    for node_id, node in list(pipeline["all_nodes"].items()):
        if node.get(PK.type) == DUMMY_NODE_TYPE:
            pipeline["all_nodes"].pop(node_id)
            for dummy_included in dummy_nodes_included:
                if isinstance(dummy_included, dict) and node_id in dummy_included:
                    dummy_included.pop(node_id)

    if dummy_flows_included is None:
        dummy_flows_included = []
    for flow_id, flow in list(pipeline[PK.flows].items()):
        if flow.get(PK.type) == DUMMY_FLOW_TYPE:
            pipeline[PK.flows].pop(flow_id)
            for dummy_included in dummy_flows_included:
                if isinstance(dummy_included, dict) and flow_id in dummy_included:
                    dummy_included.pop(flow_id)

            if flow[PK.source] in pipeline["all_nodes"]:
                delete_flow_id_from_node_io(
                    pipeline["all_nodes"][flow[PK.source]], flow_id, PK.outgoing
                )
            if flow[PK.target] in pipeline["all_nodes"]:
                delete_flow_id_from_node_io(
                    pipeline["all_nodes"][flow[PK.target]], flow_id, PK.incoming
                )

    # Restore original long edges
    pipeline[PK.flows].update(real_flows_chain)
    for flow_id, flow in real_flows_chain.items():
        add_flow_id_to_node_io(
            pipeline["all_nodes"][flow[PK.source]], flow_id, PK.outgoing
        )
        add_flow_id_to_node_io(
            pipeline["all_nodes"][flow[PK.target]], flow_id, PK.incoming
        )
