"""Tight-tree rank orchestrator — longest-path then feasible-tree refinement."""

from .longest_path import longest_path_ranker
from .feasible_tree import feasible_tree_ranker
from .utils import normalize_ranks


def tight_tree_ranker(pipeline):
    """Assign ranks using longest-path, then refine with feasible tree."""
    ranks = longest_path_ranker(pipeline)
    ranks = feasible_tree_ranker(pipeline, ranks)
    normalize_ranks(ranks)
    return ranks
