# -*- coding: utf-8 -*-
"""CMDB query tool — Agent can query CMDB via natural language

CMDB 查询工具 — Agent 可通过自然语言查询 CMDB 配置管理数据库
支持模型查询、实例搜索、拓扑查询
"""

from opsagent.tools.base import tool
from opsagent.core.types import RiskLevel, ToolResult


@tool(
    name="cmdb_query",
    description="Query CMDB (Configuration Management Database). Supports listing models, "
                "searching instances, getting instance details, and topology queries.",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_models", "search_instances", "get_instance", "get_topology",
                         "global_search"],
                "description": "Query action type: "
                               "list_models=show all model types; "
                               "search_instances=search instances by filters; "
                               "get_instance=get instance detail by ID; "
                               "get_topology=show topology for an instance; "
                               "global_search=search across all models",
            },
            "model_code": {
                "type": "string",
                "description": "Model code like 'Host', 'Biz', 'Router'. Required for "
                               "search_instances and get_instance.",
            },
            "instance_id": {
                "type": "string",
                "description": "Instance UUID. Required for get_instance and get_topology.",
            },
            "filters": {
                "type": "object",
                "description": "Field filters for search_instances, e.g. "
                               '{"status": "normal", "ip": "10.0.0.1"}',
            },
            "search": {
                "type": "string",
                "description": "Free-text search keyword for search_instances or global_search",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (1-100, default 20)",
                "default": 20,
            },
        },
        "required": ["action"],
    },
    risk_level=RiskLevel.READ,
    requires_approval=False,
)
async def cmdb_query(action: str, model_code: str = '', instance_id: str = '',
                     filters: dict = None, search: str = '', limit: int = 20, **kwargs):
    """Query CMDB configuration management database

    Supports five query modes: list model definitions, search instances,
    get instance detail, get topology tree, and global search.
    Uses existing NodeService and TopologyService for data access.
    """
    filters = filters or {}
    limit = max(1, min(100, limit or 20))

    try:
        if action == 'list_models':
            return await _list_models()
        elif action == 'search_instances':
            return await _search_instances(model_code, filters, search, limit)
        elif action == 'get_instance':
            return await _get_instance(model_code, instance_id)
        elif action == 'get_topology':
            return await _get_topology(instance_id, limit)
        elif action == 'global_search':
            return await _global_search(search, limit)
        else:
            return ToolResult(
                success=False, output='',
                error=f'Unknown action: {action}. Valid actions: '
                      f'list_models, search_instances, get_instance, get_topology, global_search',
            )
    except Exception as e:
        return ToolResult(success=False, output='', error=f'CMDB query failed: {e}')


async def _list_models() -> ToolResult:
    """List all model definitions in CMDB — 列出所有 CMDB 模型定义"""
    from cmdb.models.model_definition import ModelDefinition

    models = ModelDefinition.objects.all().values(
        'id', 'code', 'name', 'classification__name', 'is_builtin', 'description',
    )
    model_list = list(models)

    if not model_list:
        return ToolResult(success=True, output='No models found in CMDB.')

    lines = ['Available CMDB Models:']
    for m in model_list:
        cls_name = m.get('classification__name') or 'Uncategorized'
        builtin = '[Built-in]' if m.get('is_builtin') else '[Custom]'
        lines.append(f"  - {m['code']} ({m['name']}) | {builtin} | Category: {cls_name}")
        if m.get('description'):
            lines.append(f"    Description: {m['description']}")

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'total': len(model_list), 'models': model_list},
    )


async def _search_instances(model_code: str, filters: dict,
                            search: str, limit: int) -> ToolResult:
    """Search instances by model code and filters — 按模型编码和过滤条件搜索实例"""
    if not model_code:
        return ToolResult(success=False, output='', error='model_code is required for search_instances')

    from cmdb.services.node_service import NodeService

    try:
        svc = NodeService(model_code)
    except Exception as e:
        return ToolResult(
            success=False, output='',
            error=f"Model '{model_code}' not found or service unavailable: {e}",
        )

    if search:
        items = svc.search(search, limit=limit)
    else:
        result = svc.list(filters, page=1, page_size=limit)
        items = result.get('items', [])

    if not items:
        return ToolResult(
            success=True,
            output=f'No instances found for model "{model_code}".',
            metadata={'model_code': model_code, 'total': 0},
        )

    lines = [f'Found {len(items)} instance(s) of model "{model_code}":']
    for item in items:
        name = (item.get('name') or item.get('hostname') or item.get('ip')
                or item.get('instance_id', 'N/A'))
        lines.append(f'  - {name}')
        # Show key fields — 显示关键字段
        for key in ('instance_id', 'ip', 'status', 'hostname', 'os_type', 'region'):
            if key in item:
                lines.append(f'      {key}={item[key]}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'model_code': model_code, 'total': len(items), 'items': items[:limit]},
    )


async def _get_instance(model_code: str, instance_id: str) -> ToolResult:
    """Get instance detail — 获取单个实例详情"""
    if not model_code or not instance_id:
        return ToolResult(
            success=False, output='',
            error='Both model_code and instance_id are required for get_instance',
        )

    from cmdb.services.node_service import NodeService

    try:
        svc = NodeService(model_code)
        instance = svc.retrieve(instance_id)
    except Exception as e:
        return ToolResult(success=False, output='', error=str(e))

    if not instance:
        return ToolResult(
            success=True,
            output=f'Instance "{instance_id}" not found in model "{model_code}".',
            metadata={'model_code': model_code, 'instance_id': instance_id, 'found': False},
        )

    lines = [f'Instance Detail ({model_code}):']
    for key, value in instance.items():
        lines.append(f'  {key}: {value}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'model_code': model_code, 'instance_id': instance_id, 'found': True, 'data': instance},
    )


async def _get_topology(instance_id: str, limit: int) -> ToolResult:
    """Get topology tree for an instance — 获取实例拓扑树"""
    if not instance_id:
        return ToolResult(success=False, output='', error='instance_id is required for get_topology')

    from cmdb.services.topology_service import TopologyService

    svc = TopologyService()
    result = svc.get_tree(instance_id, max_depth=min(limit, 10))

    nodes = result.get('nodes', [])
    if not nodes:
        return ToolResult(
            success=True,
            output=f'No topology found for instance "{instance_id}".',
            metadata={'instance_id': instance_id, 'total': 0},
        )

    lines = [f'Topology Tree (root: {instance_id}, {len(nodes)} nodes):']
    for node in nodes:
        depth = node.get('depth', 0)
        indent = '  ' * depth
        label = (node.get('name') or node.get('instance_id', '?'))
        model = node.get('__model_code', '')
        rels = node.get('rel_chain', [])
        rel_str = f' <[{">".join(rels)}]>' if rels else ''
        lines.append(f'{indent}{"└─" if depth > 0 else ""} {label} ({model}){rel_str}')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'instance_id': instance_id, 'total': len(nodes), 'nodes': nodes},
    )


async def _global_search(search: str, limit: int) -> ToolResult:
    """Global search across all CMDB models — 全局跨模型搜索"""
    if not search:
        return ToolResult(success=False, output='', error='search keyword is required for global_search')

    from cmdb.services.topology_service import TopologyService

    svc = TopologyService()
    results = svc.global_search(search, limit=limit)

    if not results:
        return ToolResult(
            success=True,
            output=f'No results found for "{search}".',
            metadata={'search': search, 'total': 0},
        )

    lines = [f'Global search results for "{search}" ({len(results)}):']
    for r in results:
        label = r.get('label', r.get('instance_id', '?'))
        model = r.get('model_code', '')
        lines.append(f'  - {label} [{model}] (ID: {r.get("instance_id")})')

    return ToolResult(
        success=True,
        output='\n'.join(lines),
        metadata={'search': search, 'total': len(results), 'results': results},
    )
