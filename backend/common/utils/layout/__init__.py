"""Sugiyama layered graph layout engine for OPSflow.

Provides deterministic, non-LLM-based layout computation for X6 process editor
element positioning, adapted from bk_sops pipeline_web/drawing_new.
"""

from .layout_adapter import compute_layout

__all__ = ["compute_layout"]
