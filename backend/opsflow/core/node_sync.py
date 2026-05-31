"""节点同步工具 — 在 pipeline_tree JSON 与 TemplateNode/ExecutionNode 模型间同步

每次模板保存（pipeline_tree 变更）后，调用 sync_template_nodes() 将 JSON 节点刷新为独立行。
每次执行启动时，调用 sync_execution_nodes() 从模板快照创建 ExecutionNode 记录。
"""

import logging

from opsflow.models import FlowTemplate, FlowExecution, TemplateNode, ExecutionNode

logger = logging.getLogger(__name__)


def extract_nodes_from_tree(pipeline_tree: dict) -> list[dict]:
    """从 pipeline_tree JSON 提取节点列表（标准格式，非可视化节点）"""
    nodes = []
    for node in (pipeline_tree.get('nodes') or []):
        node_type = node.get('node_type', '')
        # 跳过纯视觉节点（start_event / end_event 保留用于定位，但按需过滤）
        entry = {
            'node_id': node.get('id', ''),
            'node_type': node_type,
            'atom_type': node.get('atom_type', ''),
            'label': node.get('label', ''),
            'node_config': {k: v for k, v in node.items() if k not in ('id', 'x', 'y')},
            'position_x': node.get('x'),
            'position_y': node.get('y'),
            'max_retries': node.get('max_retries', 0),
            'timeout_seconds': node.get('timeout_seconds'),
            'risk_level': node.get('risk_level', 'low'),
            'is_subprocess': node_type == 'subprocess',
        }
        nodes.append(entry)
    return nodes


def sync_template_nodes(template: FlowTemplate):
    """将模板的 pipeline_tree 同步为 TemplateNode 行（全量删除重建）

    调用时机：模板保存且 pipeline_tree 变更时。
    性能：通常 < 100 节点，全量删除重建的开销可忽略。
    """
    tree = template.pipeline_tree or {}
    nodes_data = extract_nodes_from_tree(tree)

    if not nodes_data:
        # 空树的模板不创建节点记录
        TemplateNode.objects.filter(template=template).delete()
        return

    with_transaction = getattr(template, '_sync_in_transaction', False)

    if with_transaction:
        _do_sync(template, nodes_data)
    else:
        from django.db import transaction
        with transaction.atomic():
            _do_sync(template, nodes_data)

    logger.info(
        "[node_sync] Template %s (id=%s): synced %s nodes",
        template.name, template.id, len(nodes_data),
    )


def _do_sync(template: FlowTemplate, nodes_data: list[dict]):
    """执行同步（在事务中调用）"""
    TemplateNode.objects.filter(template=template).delete()
    TemplateNode.objects.bulk_create([
        TemplateNode(template=template, **n) for n in nodes_data
    ])


def sync_execution_nodes(execution: FlowExecution):
    """从模板快照创建 ExecutionNode 记录

    调用时机：执行启动时。
    """
    snapshot = execution.template_snapshot or {}
    tree = snapshot.get('pipeline_tree') or {}
    raw_nodes = tree.get('nodes', [])

    if not raw_nodes:
        logger.warning(
            "[node_sync] Execution %s: no nodes in template snapshot",
            execution.id,
        )
        return

    nodes_data = extract_nodes_from_tree(tree)

    # 尝试关联 TemplateNode（如果模板节点记录已存在）
    try:
        template_nodes = {
            tn.node_id: tn
            for tn in TemplateNode.objects.filter(template=execution.template)
        }
    except Exception:
        template_nodes = {}

    exec_nodes = []
    for n in nodes_data:
        tn = template_nodes.get(n['node_id'])
        exec_nodes.append(ExecutionNode(
            execution=execution,
            template_node=tn,
            node_id=n['node_id'],
            node_type=n['node_type'],
            atom_type=n['atom_type'],
            label=n['label'],
            status='pending',
            max_retries=n['max_retries'],
            timeout_seconds=n['timeout_seconds'],
            position_x=n['position_x'],
            position_y=n['position_y'],
        ))

    ExecutionNode.objects.bulk_create(exec_nodes)

    logger.info(
        "[node_sync] Execution %s: synced %s nodes",
        execution.id, len(exec_nodes),
    )
