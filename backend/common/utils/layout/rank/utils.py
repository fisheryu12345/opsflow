"""Rank utility functions."""

from ..constants import PK, MIN_LEN


def max_rank(ranks):
    return max(ranks.values())


def min_rank(ranks):
    return min(ranks.values())


def normalize_ranks(ranks):
    """Shift all ranks so that min rank is 0."""
    min_rk = min_rank(ranks)
    for node_id in ranks:
        ranks[node_id] -= min_rk


def slack(ranks, flow):
    """Return slack (tightness) of a flow: rank(target) - rank(source) - 1."""
    return ranks[flow[PK.target]] - ranks[flow[PK.source]] - MIN_LEN
