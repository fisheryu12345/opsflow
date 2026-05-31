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


def resolve_params(params: dict, context: dict,
                   var_types: dict = None,
                   lazy_resolver: Optional[Callable] = None) -> dict:
    """递归解析参数字典中所有字段的 ${key} 引用，按 var_types 处理类型

    Args:
        params: 参数字典
        context: 变量上下文
        var_types: {field_name: "plain"|"splice"|"split"|"lazy"}
        lazy_resolver: lazy 类型的回调
    """
    resolved = {}
    for k, v in params.items():
        vt = (var_types or {}).get(k, "splice")
        if vt == "plain":
            resolved[k] = v
        elif vt == "split":
            resolved[k] = resolve_with_type(v, "split", context)
        elif vt == "lazy":
            resolved[k] = resolve_with_type(v, "lazy", context, lazy_resolver)
        elif isinstance(v, str) and '${' in v:
            resolved[k] = resolve_variables(v, context)
        elif isinstance(v, dict):
            resolved[k] = resolve_params(v, context, var_types, lazy_resolver)
        elif isinstance(v, list):
            resolved[k] = [_resolve_item(item, context, var_types, lazy_resolver) for item in v]
        else:
            resolved[k] = v
    return resolved


def _resolve_item(item, context, var_types=None, lazy_resolver=None):
    if isinstance(item, str) and '${' in item:
        return resolve_variables(item, context)
    if isinstance(item, dict):
        return resolve_params(item, context, var_types, lazy_resolver)
    if isinstance(item, list):
        return [_resolve_item(i, context, var_types, lazy_resolver) for i in item]
    return item


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

    return ctx
