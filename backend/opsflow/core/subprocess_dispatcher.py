"""Independent Subprocess Dispatcher — runs subprocess as separate FlowExecution

This module implements Phase 5 of the subprocess management enhancement.
When a subprocess node has `independent: true` in its params, the
PluginService delegates execution here instead of using bamboo-engine's
built-in SubProcess element.
"""

import logging
from typing import Optional

from opsflow.models import FlowExecution, FlowTemplate, NodeExecutionTrace

logger = logging.getLogger(__name__)


class SubprocessDispatcher:
    """Dispatches a subprocess node as an independent FlowExecution.

    Usage:
        dispatcher = SubprocessDispatcher(parent_execution)
        child_id = dispatcher.start_subprocess(
            node_id="node_sub_1",
            target_template_id=5,
            variable_mapping=[{"parent_key": "host", "child_key": "target_host"}],
            output_mapping=[{"child_key": "result.key", "parent_key": "output_var"}],
        )
    """

    def __init__(self, parent_execution: FlowExecution):
        self.parent = parent_execution

    def start_subprocess(
        self,
        node_id: str,
        target_template_id: int,
        variable_mapping: Optional[list] = None,
        output_mapping: Optional[list] = None,
    ) -> Optional[int]:
        """Create and start a child execution for the subprocess node.

        Resolves variable_mapping values from parent context, creates a new
        FlowExecution for the target template, and starts it asynchronously.

        Returns:
            child_execution_id or None on failure
        """
        try:
            target = FlowTemplate.objects.get(id=target_template_id)
        except FlowTemplate.DoesNotExist:
            logger.error("Subprocess target template %s not found", target_template_id)
            return None

        # Resolve variable mappings from parent context
        from opsflow.core.variable_resolver import build_execution_context, resolve_variables

        parent_ctx = build_execution_context(self.parent)
        vm = variable_mapping or []
        child_global_vars = {}
        for mapping in vm:
            if isinstance(mapping, dict):
                parent_key = mapping.get("parent_key", "")
                child_key = mapping.get("child_key", "")
                if parent_key and child_key:
                    resolved = resolve_variables(parent_key, parent_ctx)
                    child_global_vars[child_key] = resolved
            elif isinstance(mapping, (list, tuple)) and len(mapping) == 2:
                parent_key, child_key = mapping
                resolved = resolve_variables(parent_key, parent_ctx)
                child_global_vars[child_key] = resolved

        # Create child execution
        child = FlowExecution.objects.create(
            template=target,
            status="pending",
            parent_execution=self.parent,
            is_subprocess=True,
            created_by=self.parent.created_by,
        )

        # Freeze template snapshot with mapped vars + parent context
        snapshot = target.snapshot or {}
        child.template_snapshot = {
            "pipeline_tree": snapshot.get("pipeline_tree", target.pipeline_tree),
            "global_vars": child_global_vars,
            "template_version": target.version,
            "parent_execution_id": self.parent.id,
            "parent_node_id": node_id,
        }
        child.node_status = {node_id: "running"}
        child.save(update_fields=["template_snapshot", "node_status"])

        # Record parent trace linking to child execution
        NodeExecutionTrace.objects.create(
            execution=self.parent,
            node_id=node_id,
            node_label=target.name,
            atom_type="subprocess",
            node_type="subprocess",
            status="running",
            outputs={"child_execution_id": child.id},
            inputs={"target_template_id": target_template_id},
        )

        # Start child execution (async via Celery)
        from opsflow.core.flow_engine import FlowEngine

        engine = FlowEngine(child)
        engine.start()

        logger.info(
            "[SubprocessDispatcher] Child execution %s started for node %s (template %s)",
            child.id, node_id, target.name,
        )
        return child.id

    def handle_completion(self, child_execution: FlowExecution):
        """Called when a child execution completes or fails.

        Maps child outputs back to the parent node according to output_mapping.
        """
        child_snapshot = child_execution.template_snapshot or {}
        parent_node_id = child_snapshot.get("parent_node_id")

        if not parent_node_id:
            logger.warning("[SubprocessDispatcher] No parent_node_id in child snapshot %s", child_execution.id)
            return

        # Get the output mapping from parent's pipeline_tree
        tree = self.parent.template_snapshot or {}
        pipeline_tree = tree.get("pipeline_tree", {})
        output_mapping = []
        for node in pipeline_tree.get("nodes", []):
            if node.get("id") == parent_node_id:
                output_mapping = node.get("params", {}).get("output_mapping", [])
                break

        # Collect child outputs
        child_traces = NodeExecutionTrace.objects.filter(
            execution=child_execution,
            status="completed",
        ).exclude(outputs={}).values("node_id", "outputs")

        child_outputs = {}
        for t in child_traces:
            child_outputs[t["node_id"]] = t["outputs"]

        # Map back to parent context
        parent_outputs = {}
        for om in output_mapping:
            if isinstance(om, dict):
                child_key = om.get("child_key", "")
                parent_key = om.get("parent_key", "")
            elif isinstance(om, (list, tuple)) and len(om) == 2:
                child_key, parent_key = om
            else:
                continue

            if child_key and parent_key:
                # Support dot-notation: node_id.output_key
                parts = child_key.split(".", 1)
                if len(parts) == 2:
                    c_node, c_key = parts
                    if c_node in child_outputs and isinstance(child_outputs[c_node], dict):
                        if c_key in child_outputs[c_node]:
                            parent_outputs[parent_key] = child_outputs[c_node][c_key]

        # Update parent trace
        traces = NodeExecutionTrace.objects.filter(
            execution=self.parent,
            node_id=parent_node_id,
        )
        for trace in traces:
            trace.outputs = {**(trace.outputs or {}), **parent_outputs, "_result": child_execution.status == "completed"}
            trace.status = "completed" if child_execution.status == "completed" else "failed"
            trace.save()

        logger.info(
            "[SubprocessDispatcher] Parent node %s updated from child %s (status: %s)",
            parent_node_id, child_execution.id, child_execution.status,
        )
