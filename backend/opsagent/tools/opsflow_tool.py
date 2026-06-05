# -*- coding: utf-8 -*-
"""OpsFlow trigger tool — Agent can trigger OpsFlow template execution

OpsFlow 流程触发工具 — Agent 可触发运维流程执行，查看执行状态和结果
"""

import json

from opsagent.tools.base import tool
from opsagent.core.types import RiskLevel, ToolResult


@tool(
    name="opsflow_trigger",
    description="Trigger or query OpsFlow workflow templates. Supports listing templates, "
                "triggering execution, and checking execution status.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_templates", "trigger_execution", "get_execution_status",
                         "list_executions"],
                "description": "Operation type: "
                               "list_templates=list available FlowTemplates; "
                               "trigger_execution=start a new execution; "
                               "get_execution_status=check execution detail; "
                               "list_executions=list recent executions",
            },
            "template_id": {
                "type": "integer",
                "description": "FlowTemplate ID. Required for trigger_execution.",
            },
            "execution_id": {
                "type": "integer",
                "description": "FlowExecution ID. Required for get_execution_status.",
            },
            "variable_overrides": {
                "type": "object",
                "description": "Variables to override when triggering execution, "
                               'e.g. {"host": "10.0.0.1", "port": 8080}',
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (1-50, default 10)",
                "default": 10,
            },
        },
        "required": ["action"],
    },
    risk_level=RiskLevel.MEDIUM_WRITE,
    requires_approval=True,
)
async def opsflow_trigger(action: str, template_id: int = 0, execution_id: int = 0,
                          variable_overrides: dict = None, limit: int = 10, **kwargs):
    """Trigger or query OpsFlow workflow execution

    Supports listing available templates, triggering new executions,
    and checking execution status/results.
    """
    variable_overrides = variable_overrides or {}
    limit = max(1, min(50, limit or 10))

    try:
        if action == 'list_templates':
            return await _list_templates(limit)
        elif action == 'trigger_execution':
            return await _trigger_execution(template_id, variable_overrides)
        elif action == 'get_execution_status':
            return await _get_execution_status(execution_id)
        elif action == 'list_executions':
            return await _list_executions(limit)
        else:
            return ToolResult(
                success=False, output='',
                error=f'Unknown action: {action}',
            )
    except Exception as e:
        return ToolResult(success=False, output='', error=f'OpsFlow operation failed: {e}')


async def _list_templates(limit: int) -> ToolResult:
    """List available OpsFlow templates — 列出可用流程模板"""
    from opsflow.models import FlowTemplate

    templates = FlowTemplate.objects.filter(is_draft=False).order_by('-updated_at')[:limit]
    tpl_list = []

    lines = [f'Available OpsFlow Templates ({len(templates)}):']
    for t in templates:
        tpl_list.append({
            'id': t.id,
            'name': t.name,
            'category': t.category,
            'is_draft': t.is_draft,
            'version': t.version,
            'created_at': str(t.created_at),
        })
        lines.append(f'  ID={t.id}: {t.name}')
        lines.append(f'      Category: {t.category or "N/A"} | Version: {t.version or 1}')
        if t.description:
            lines.append(f'      Description: {t.description[:200]}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'total': len(tpl_list), 'templates': tpl_list},
    )


async def _trigger_execution(template_id: int, variable_overrides: dict) -> ToolResult:
    """Trigger a new execution — 触发新的流程执行"""
    if not template_id:
        return ToolResult(success=False, output='', error='template_id is required for trigger_execution')

    from opsflow.models import FlowTemplate, FlowExecution

    try:
        template = FlowTemplate.objects.get(id=template_id)
    except FlowTemplate.DoesNotExist:
        return ToolResult(success=False, output='', error=f'Template not found: id={template_id}')

    if template.is_draft:
        return ToolResult(
            success=False, output='',
            error=f'Template "{template.name}" is a draft and cannot be executed. Publish it first.',
        )

    # Create execution record — 创建执行记录
    execution = FlowExecution.objects.create(
        template=template,
        project=template.project,
        status='pending',
        node_status={},
        state_tree={},
        context={},
        template_snapshot={
            'pipeline_tree': template.pipeline_tree,
            'target_hosts': template.target_hosts,
            'global_vars': template.global_vars,
            'template_version': template.version,
        },
    )

    # Apply variable overrides — 应用变量覆盖
    if variable_overrides and execution.template_snapshot:
        frozen_vars = dict(execution.template_snapshot.get('global_vars', {}))
        for key, value in variable_overrides.items():
            if key in frozen_vars:
                if isinstance(frozen_vars[key], dict) and 'value' in frozen_vars[key]:
                    frozen_vars[key] = dict(frozen_vars[key])
                    frozen_vars[key]['value'] = value
                else:
                    frozen_vars[key] = value
        execution.template_snapshot['global_vars'] = frozen_vars
        execution.save(update_fields=['template_snapshot'])

    # Sync execution nodes — 同步执行节点
    try:
        from opsflow.core.node_sync import sync_execution_nodes
        sync_execution_nodes(execution)
    except Exception as e:
        # Non-critical: nodes will be synced on flow engine start — 非关键：引擎启动时会同步
        pass

    # Start execution via FlowEngine — 启动执行
    try:
        from opsflow.core.flow_engine import FlowEngine
        engine = FlowEngine(execution)
        engine.start()
    except Exception as e:
        # If engine.start fails, keep execution as pending — 引擎启动失败，保持等待状态
        pass

    return ToolResult(
        success=True,
        output=f'Execution triggered for template "{template.name}" (ID={template.id}).\n'
               f'Execution ID: {execution.id}\n'
               f'Status: {execution.status}\n'
               f'Use opsflow_trigger action=get_execution_status with execution_id={execution.id} '
               f'to check progress.',
        metadata={
            'execution_id': execution.id,
            'template_id': template.id,
            'template_name': template.name,
            'status': execution.status,
        },
    )


async def _get_execution_status(execution_id: int) -> ToolResult:
    """Get execution status and results — 获取执行状态和结果"""
    if not execution_id:
        return ToolResult(success=False, output='', error='execution_id is required')

    from opsflow.models import FlowExecution, ExecutionNode, NodeExecutionTrace

    try:
        execution = FlowExecution.objects.get(id=execution_id)
    except FlowExecution.DoesNotExist:
        return ToolResult(success=False, output='', error=f'Execution not found: id={execution_id}')

    template_name = execution.template.name if execution.template else 'N/A'

    # Get node details — 获取节点详情
    nodes = ExecutionNode.objects.filter(execution=execution)
    node_list = []
    for n in nodes:
        node_list.append({
            'node_id': n.node_id,
            'label': n.label,
            'node_type': n.node_type,
            'atom_type': n.atom_type,
            'status': n.status,
        })

    # Get traces — 获取执行轨迹
    traces = NodeExecutionTrace.objects.filter(execution=execution)[:20]
    trace_list = []
    for t in traces:
        trace_list.append({
            'node_id': t.node_id,
            'label': t.node_label,
            'status': t.status,
            'entered_at': str(t.entered_at) if t.entered_at else None,
            'exited_at': str(t.exited_at) if t.exited_at else None,
            'duration_ms': t.duration_ms,
            'error': t.error[:200] if t.error else None,
        })

    lines = [f'Execution Status (ID={execution_id}):']
    lines.append(f'  Template: {template_name}')
    lines.append(f'  Status: {execution.get_status_display()}')
    lines.append(f'  Created: {execution.created_at}')
    if execution.started_at:
        lines.append(f'  Started: {execution.started_at}')
    if execution.ended_at:
        lines.append(f'  Ended: {execution.ended_at}')
    lines.append(f'  Current Node: {execution.current_node or "N/A"}')
    lines.append(f'  Total Nodes: {len(node_list)}')

    if trace_list:
        lines.append('\n  Recent Traces:')
        for t in trace_list[:10]:
            dur = f'{t["duration_ms"]}ms' if t['duration_ms'] else 'N/A'
            err = f' | Error: {t["error"]}' if t.get('error') else ''
            lines.append(f'    [{t["status"]}] {t["label"] or t["node_id"]} ({dur}){err}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={
            'execution_id': execution.id,
            'template_name': template_name,
            'status': execution.status,
            'node_count': len(node_list),
            'trace_count': len(trace_list),
            'nodes': node_list[:50],
            'traces': trace_list,
        },
    )


async def _list_executions(limit: int) -> ToolResult:
    """List recent executions — 列出最近的执行记录"""
    from opsflow.models import FlowExecution

    executions = FlowExecution.objects.order_by('-created_at')[:limit]
    exec_list = []

    lines = [f'Recent Executions ({len(executions)}):']
    for e in executions:
        tpl_name = e.template.name if e.template else 'N/A'
        exec_list.append({
            'id': e.id,
            'template_name': tpl_name,
            'status': e.status,
            'created_at': str(e.created_at),
            'started_at': str(e.started_at) if e.started_at else None,
            'ended_at': str(e.ended_at) if e.ended_at else None,
        })
        lines.append(f'  ID={e.id}: [{e.status}] {tpl_name}')
        lines.append(f'      Created: {e.created_at}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'total': len(exec_list), 'executions': exec_list},
    )
