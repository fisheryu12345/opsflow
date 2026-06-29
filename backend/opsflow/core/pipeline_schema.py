"""Pipeline Tree JSON Schema 验证

定义 OPSFLOW_PIPELINE_SCHEMA 对前端 nodes/edges 格式进行结构验证，
在 bamboo_validator 的业务逻辑验证之前执行。

参考 bk_sops pipeline_web/parser/schemas.py + validate.py
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# 常量键名正则 — 必须匹配 ${identifier}
KEY_PATTERN = r"^(\$\{[a-zA-Z_][a-zA-Z0-9_]*\})$"
KEY_PATTERN_RE = re.compile(KEY_PATTERN)

# ── OPSFLOW Pipeline Tree JSON Schema ───────────────────────────────

OPSFLOW_PIPELINE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["nodes", "edges"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "node_type"],
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
                        "maxLength": 100,
                    },
                    "label": {
                        "type": "string",
                        "maxLength": 200,
                    },
                    "node_type": {
                        "type": "string",
                        "enum": [
                            "", "atom",
                            "exclusive_gateway", "parallel_gateway",
                            "conditional_parallel_gateway", "converge_gateway",
                            "subprocess",
                            "start_event", "end_event",
                        ],
                    },
                    "atom_type": {"type": "string", "maxLength": 128},
                    "params": {"type": "object"},
                    "max_retries": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10,
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 86400,
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "retry_delay": {"type": "integer", "minimum": 0, "maximum": 3600},
                    "position_x": {"type": "number"},
                    "position_y": {"type": "number"},
                    "_plugin_version": {"type": "string"},
                    "plugin_version": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["from", "to"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                    "label": {"type": "string", "maxLength": 200},
                    "condition": {"type": "string"},
                },
                "additionalProperties": True,
            },
        },
        "global_vars": {
            "type": "object",
            "additionalProperties": True,
        },
    },
    "additionalProperties": True,
}


def validate_pipeline_schema(pipeline_tree: dict) -> list:
    """JSON Schema 结构验证

    Args:
        pipeline_tree: 前端传来的 pipeline_tree dict

    Returns:
        list[str]: 错误列表，为空表示验证通过
    """
    if not isinstance(pipeline_tree, dict):
        return ["pipeline_tree 必须为 dict"]

    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed, skipping schema validation")
        return []

    try:
        jsonschema.validate(pipeline_tree, OPSFLOW_PIPELINE_SCHEMA)
        return []
    except jsonschema.exceptions.ValidationError as e:
        # 格式化错误路径和消息
        path = " → ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        msg = e.message
        return [f"[Schema] {path}: {msg}"]


def validate_global_var_keys(global_vars: dict) -> list:
    """校验全局变量键名格式

    禁止使用 _env_ 和 _system 保留前缀。
    键名应使用常规标识符（字母/数字/下划线）。

    Reference: bk_sops KEY_PATTERN（适配 OpsFlow 格式）
    """
    errors = []
    if not isinstance(global_vars, dict):
        return []

    for key in global_vars:
        if not isinstance(key, str) or not key:
            errors.append(f"变量键名无效: '{key}'")
            continue
        if key.startswith('_env_') or key.startswith('_system'):
            errors.append(f"变量键名 '{key}' 使用了保留前缀 _env_ 或 _system")
        if not all(c.isalnum() or c == '_' for c in key):
            errors.append(f"变量键名 '{key}' 包含非法字符（仅允许字母/数字/下划线）")

    return errors


def validate_pipeline_full(pipeline_tree: dict) -> dict:
    """全量验证：JSON Schema → 键名 → 返回 unified 结果

    返回格式与 bamboo_validator 兼容:
        {'valid': bool, 'errors': [str], 'warnings': [str]}
    """
    errors = validate_pipeline_schema(pipeline_tree)
    global_vars = pipeline_tree.get('global_vars', {})
    errors.extend(validate_global_var_keys(global_vars))

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': [],
    }
