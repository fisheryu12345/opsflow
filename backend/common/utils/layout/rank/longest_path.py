"""Longest-path rank assignment — initial rank for each node."""

from ..constants import PK, MIN_LEN
from ..utils import format_to_list


def longest_path_ranker(pipeline):
    """
    Assign each node a rank equal to length of longest path from start node.
    End node gets rank 0, then inverted so start node has rank 0.
    """
    ranks = {}

    def dfs(node):
        if node[PK.id] in ranks:
            return ranks[node[PK.id]]
        incoming_node_ranks = []
        for flow_id in format_to_list(node.get(PK.incoming, "")):
            if flow_id in pipeline[PK.flows]:
                flow = pipeline[PK.flows][flow_id]
                incoming_node = pipeline["all_nodes"][flow[PK.source]]
                incoming_node_ranks.append(dfs(incoming_node) - MIN_LEN)
        if not incoming_node_ranks:
            rank = 0
        else:
            rank = min(incoming_node_ranks)
        ranks[node[PK.id]] = rank
        return rank

    for node_id, node in pipeline["all_nodes"].items():
        if node_id not in ranks:
            dfs(node)

    # Invert so start node (min rank) = 0
    min_rk = min(ranks.values()) if ranks else 0
    for key in ranks:
        ranks[key] = min_rk - ranks[key]
    return ranks
