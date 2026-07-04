"""Pipeline data normalization — build/remove all_nodes dictionary."""

from .constants import PK


def get_all_nodes(pipeline):
    """Build flat all_nodes dict from pipeline sections."""
    all_nodes = {}
    for section in [PK.start_event, PK.end_event]:
        node = pipeline.get(section)
        if isinstance(node, dict) and PK.id in node:
            all_nodes[node[PK.id]] = node
    for section in [PK.activities, PK.gateways]:
        nodes = pipeline.get(section, {})
        if isinstance(nodes, dict):
            all_nodes.update(nodes)
    return all_nodes


def normalize_run(pipeline):
    pipeline["all_nodes"] = get_all_nodes(pipeline)


def normalize_undo(pipeline):
    pipeline.pop("all_nodes", None)
