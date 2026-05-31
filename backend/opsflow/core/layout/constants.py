"""Layout engine constants — replaces pipeline_web.constants.PWE."""


class NodeType:
    ServiceActivity = "ServiceActivity"
    EmptyStartEvent = "EmptyStartEvent"
    EmptyEndEvent = "EmptyEndEvent"
    ExclusiveGateway = "ExclusiveGateway"
    ParallelGateway = "ParallelGateway"
    ConditionalParallelGateway = "ConditionalParallelGateway"
    ConvergeGateway = "ConvergeGateway"
    DummyNode = "DummyNode"


class PipelineKey:
    id = "id"
    type = "type"
    name = "name"
    start_event = "start_event"
    end_event = "end_event"
    activities = "activities"
    gateways = "gateways"
    flows = "flows"
    incoming = "incoming"
    outgoing = "outgoing"
    source = "source"
    target = "target"
    location = "location"
    line = "line"

    # for location output
    status = "status"


PK = PipelineKey()

DUMMY_NODE_TYPE = NodeType.DummyNode
DUMMY_FLOW_TYPE = "DummyFlow"

MIN_LEN = 1
CANVAS_WIDTH = 1300

POSITION = {
    "activity_size": (180, 48),
    "event_size": (56, 56),
    "gateway_size": (70, 70),
    "start": (60, 100),
}

PIPELINE_ELEMENT_TO_WEB = {
    DUMMY_NODE_TYPE: DUMMY_NODE_TYPE,
    NodeType.ServiceActivity: "tasknode",
    NodeType.EmptyStartEvent: "startpoint",
    NodeType.EmptyEndEvent: "endpoint",
    NodeType.ExclusiveGateway: "branchgateway",
    NodeType.ParallelGateway: "parallelgateway",
    NodeType.ConvergeGateway: "convergegateway",
    NodeType.ConditionalParallelGateway: "conditionalparallelgateway",
}
PIPELINE_WEB_TO_ELEMENT = {value: key for key, value in PIPELINE_ELEMENT_TO_WEB.items()}

# OPSflow node_type → internal NodeType mapping
OPSFLOW_NODE_TYPE_MAP = {
    "": NodeType.ServiceActivity,
    "start_event": NodeType.EmptyStartEvent,
    "end_event": NodeType.EmptyEndEvent,
    "exclusive_gateway": NodeType.ExclusiveGateway,
    "parallel_gateway": NodeType.ParallelGateway,
    "conditional_parallel_gateway": NodeType.ConditionalParallelGateway,
    "converge_gateway": NodeType.ConvergeGateway,
}

OPSFLOW_NODE_TYPE_MAP_REVERSE = {v: k for k, v in OPSFLOW_NODE_TYPE_MAP.items()}
