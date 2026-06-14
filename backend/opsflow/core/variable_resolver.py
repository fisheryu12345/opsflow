"""变量解析引擎 — ${key} 模板变量替换 + 跨节点数据引用

提供 bk-sops 风格的变量解析能力：
  1. ${global_var} → 从全局变量字典取值
  2. ${node_id.output_key} → 从上游节点输出取值
  3. ${_result} → 前驱节点执行结果（bamboo-engine 内置）

支持变量类型：
  - plain:   静态值，不做替换
  - splice:  模板字符串，${key} 替换（默认）
  - split:   替换后用逗号分隔为列表
  - lazy:    延迟计算，由 lazy_resolver 回调处理
"""

import logging
import re
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

VARIABLE_PATTERN = re.compile(r'\$\{([^}]+)\}')


# ── Global variables normalization ─────────────────────────────────


def normalize_global_vars(global_vars: dict) -> dict:
    """规范化 global_vars 为包含元数据的结构化格式

    旧格式: {"key": "value"}
    新格式: {"key": {"value": ..., "type": "input", "source_type": "manual",
                      "source_info": None, "show_type": True, "description": ""}}

    始终返回结构化格式。
    """
    if not global_vars:
        return {}
    normalized = {}
    for key, val in global_vars.items():
        if isinstance(val, dict) and "value" in val:
            # 已经是结构化格式 — 确保默认字段
            entry = {
                "value": val["value"],
                "type": val.get("type", "input"),
                "show_type": val.get("show_type", True),
                "description": val.get("description", ""),
                "source_type": val.get("source_type", "manual"),
                "source_info": val.get("source_info"),
                "validation": val.get("validation", []),
            }
        else:
            # 扁平格式 — 包装为结构化
            entry = {
                "value": val,
                "type": "input",
                "show_type": True,
                "description": "",
                "source_type": "manual",
                "source_info": None,
                "validation": [],
            }
        normalized[key] = entry
    return normalized


def get_global_vars_values(global_vars: dict) -> dict:
    """从规范化（或扁平）global_vars 中提取纯值 dict

    供 bamboo_builder.py 注入 Var(type=PLAIN) 使用。
    """
    normalized = normalize_global_vars(global_vars)
    return {k: v["value"] for k, v in normalized.items()}


def count_variable_references(pipeline_tree: dict, var_key: str) -> int:
    """扫描 pipeline_tree 中 `${var_key}` 的出现次数"""
    if not pipeline_tree or not var_key:
        return 0
    pattern = re.compile(r'\$\{' + re.escape(var_key) + r'\}')
    count = 0
    nodes = pipeline_tree.get('nodes', []) or []
    for node in nodes:
        params = node.get('params', {}) or {}
        count += _count_in_value(params, pattern)
    return count


def cleanup_unused_vars(pipeline_tree: dict, global_vars: dict) -> dict:
    """删除 pipeline_tree 中不再被任何节点引用的全局变量

    Args:
        pipeline_tree: {nodes, edges} 格式的流程定义
        global_vars: 规范化或扁平格式的全局变量

    Returns:
        清理后的全局变量 dict（结构化格式）
    """
    normalized = normalize_global_vars(global_vars)
    cleaned = {}
    for key, entry in normalized.items():
        ref_count = count_variable_references(pipeline_tree, key)
        if ref_count > 0:
            cleaned[key] = entry
        # 引用计数为 0 时自动删除
    return cleaned


def get_variable_reference_details(pipeline_tree: dict, var_key: str) -> list[dict]:
    """返回变量引用明细 — 每个引用出现的节点 ID 和字段路径

    Returns:
        [{"node_id": "node_1", "node_label": "SSH", "field_path": "params.command",
          "param_key": "command", "message": "..."}, ...]
    """
    if not pipeline_tree or not var_key:
        return []
    pattern = re.compile(r'\$\{' + re.escape(var_key) + r'\}')
    refs = []
    nodes = pipeline_tree.get('nodes', []) or []
    for node in nodes:
        node_id = node.get('id', '')
        node_label = node.get('label', '')
        params = node.get('params', {}) or {}
        node_refs = _find_references_in(params, pattern, node_id, node_label, 'params')
        refs.extend(node_refs)

        # 也检查 node_config 中的引用（如果有）
        node_config = node.get('node_config', {}) or {}
        if isinstance(node_config, dict):
            node_refs2 = _find_references_in(node_config, pattern, node_id, node_label, 'node_config')
            refs.extend(node_refs2)

    return refs


def _find_references_in(data, pattern: re.Pattern, node_id: str, node_label: str, base_path: str = 'params') -> list[dict]:
    """递归搜索 dict 中的匹配引用，返回引用明细列表"""
    refs = []
    if isinstance(data, dict):
        for key, val in data.items():
            field_path = f"{base_path}.{key}"
            if isinstance(val, str):
                if pattern.search(val):
                    # 提取引用上下文（截断长文本）
                    ctx = val[:80] + '...' if len(val) > 80 else val
                    refs.append({
                        'node_id': node_id,
                        'node_label': node_label or node_id,
                        'field_path': field_path,
                        'param_key': key,
                        'message': ctx,
                    })
            elif isinstance(val, (dict, list)):
                refs.extend(_find_references_in(val, pattern, node_id, node_label, base_path=field_path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            refs.extend(_find_references_in(item, pattern, node_id, node_label, base_path=f"{base_path}[{i}]"))
    return refs


def _count_in_value(value, pattern: re.Pattern) -> int:
    """递归统计匹配次数"""
    if isinstance(value, str):
        return len(pattern.findall(value))
    if isinstance(value, dict):
        return sum(_count_in_value(v, pattern) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_in_value(v, pattern) for v in value)
    return 0


def resolve_variables(template_str: str, context: dict) -> str:
    """解析 ${key} 引用，返回替换后的字符串

    Args:
        template_str: 含 ${key} 的模板字符串
        context: 变量上下文，含 global_vars + 各节点 outputs

    Returns:
        替换后的字符串（找不到的变量保留原样）
    """
    if not template_str or '${' not in template_str:
        return template_str

    def _replacer(match):
        key = match.group(1).strip()

        # 1. 直接查找
        if key in context:
            return str(context[key])

        # 2. 点号分隔的引用: node_id.output_key
        parts = key.split('.', 1)
        if len(parts) == 2:
            node_id, output_key = parts
            node_outputs = context.get(node_id, {})
            if isinstance(node_outputs, dict) and output_key in node_outputs:
                return str(node_outputs[output_key])

        # 3. 递归查找: 在嵌套 dict 中搜索点号路径
        val = _deep_get(context, key)
        if val is not None:
            return str(val)

        # 找不到则保留原样（bk-sops 行为一致）
        return match.group(0)

    return VARIABLE_PATTERN.sub(_replacer, template_str)


def split_value(raw: str, delimiter: str = ",") -> list:
    """将字符串按分隔符拆分为列表，去除空白和空项"""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    return [item.strip() for item in raw.split(delimiter) if item.strip()]


def resolve_with_type(value: Any, var_type: str, context: dict,
                      lazy_resolver: Optional[Callable] = None) -> Any:
    """按变量类型解析值

    Args:
        value: 原始值
        var_type: plain | splice | split | lazy
        context: 变量上下文
        lazy_resolver: lazy 类型时调用的回调 (value, context) → any

    Returns:
        解析后的值
    """
    if var_type == "plain":
        return value
    if var_type == "split":
        raw = resolve_variables(str(value), context) if isinstance(value, str) else value
        return split_value(str(raw))
    if var_type == "lazy" and lazy_resolver:
        raw = resolve_variables(str(value), context) if isinstance(value, str) else value
        return lazy_resolver(raw, context)
    # 默认 splice
    if isinstance(value, str) and '${' in value:
        return resolve_variables(value, context)
    return value


def _deep_get(d: dict, dotted_key: str):
    """在嵌套 dict 中按点号路径查找值，如 'node_1.outputs.job_inst_id'"""
    parts = dotted_key.split('.')
    current = d
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def build_execution_context(execution) -> dict:
    """从 FlowExecution 构建变量解析上下文

    包含:
      - global_vars: 模板全局变量
      - hook_variables: 用户提升的全局变量配置
      - target_hosts: 目标主机列表
      - 各节点的 outputs: 已完成节点的输出
      - _system.*: 系统内置变量
      - _project.*: 项目/模板配置变量
    """
    ctx = {}

    # 全局变量（使用规范化提取值）
    frozen = execution.template_snapshot or {}
    global_vars = frozen.get('global_vars', {}) or {}
    if isinstance(global_vars, dict):
        normalized = normalize_global_vars(global_vars)
        for key, entry in normalized.items():
            ctx[key] = entry["value"]

    # 可提升变量（hook_variables）
    template = execution.template
    if template:
        hook_vars = getattr(template, 'hook_variables', {}) or {}
        for key, cfg in hook_vars.items():
            if isinstance(cfg, dict) and 'value' in cfg:
                ctx[key] = cfg['value']
            elif isinstance(cfg, dict) and 'default' in cfg:
                ctx[key] = cfg['default']

    # ── 项目环境变量 ──
    template_obj = getattr(execution, 'template', None)
    if template_obj and template_obj.project_id:
        project_env = resolve_project_variables(template_obj.project_id)
        # project env 作为 base，已存在的 ctx 值（模板 vars）覆盖其上
        ctx = {**project_env, **ctx}

    ctx['target_hosts'] = frozen.get('target_hosts', [])

    # 各节点 outputs
    from opsflow.models import NodeExecutionTrace
    traces = NodeExecutionTrace.objects.filter(
        execution=execution,
        status='completed',
    ).exclude(outputs={}).values('node_id', 'outputs')

    for t in traces:
        nid = t['node_id']
        outputs = t.get('outputs', {})
        if outputs:
            ctx[nid] = outputs

    # ── 解析被提升的节点输出变量 ──
    # 全局变量中 source_type="node_output" 的条目其值为空字符串，
    # 需要从对应节点的实际输出中动态取值。
    promoted_globals = normalize_global_vars(frozen.get('global_vars', {}))
    for key, entry in promoted_globals.items():
        if entry.get("source_type") == "node_output":
            src_info = entry.get("source_info") or {}
            src_node = src_info.get("node_id", "")
            src_field = src_info.get("tag_code", "")
            if src_node and src_field and src_node in ctx:
                if isinstance(ctx[src_node], dict) and src_field in ctx[src_node]:
                    ctx[key] = ctx[src_node][src_field]

    # ── 系统变量 (_system.*) ──
    ctx['_system'] = {
        'execution_id': execution.id,
        'started_at': getattr(execution, 'started_at', None) or '',
        'executed_by': execution.created_by.username if getattr(execution, 'created_by', None) else '',
        'status': getattr(execution, 'status', ''),
        'current_node': getattr(execution, 'current_node', '') or '',
    }

    # ── 项目/模板变量 (_project.*) ──
    tpl = getattr(execution, 'template', None)
    if tpl:
        ctx['_project'] = {
            'template_id': getattr(tpl, 'id', ''),
            'template_name': getattr(tpl, 'name', ''),
            'template_version': getattr(tpl, 'version', None) or 1,
            'category': getattr(tpl, 'category', '') or '',
        }

    return ctx


def resolve_project_variables(project_id: int) -> dict:
    """获取项目环境变量（扁平 dict，供运行时注入）

    从 ProjectEnvironmentVariable 表中读取指定项目的所有环境变量，
    返回 {key: value} 格式，供 bamboo_builder 注入到 pipeline inputs。
    """
    from opsflow.models import ProjectEnvironmentVariable
    qs = ProjectEnvironmentVariable.objects.filter(project_id=project_id)
    return {v.key: v.value for v in qs}
