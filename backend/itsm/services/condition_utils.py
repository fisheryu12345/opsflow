# -*- coding: utf-8 -*-
"""ITSM 条件表达式工具 — 从 opsflow 复制，消除跨 app import

从 opsflow.core.pipeline_builder.elements 复制的条件解析工具：
_EXPR_PATTERN, _VAR_REF_PATTERN, _register_node_output, _collect_condition_refs
"""

import re

from bamboo_engine.builder import Var
from bamboo_engine.builder.flow.data import NodeOutput

# 匹配 ${expr} 整体
_EXPR_PATTERN = re.compile(r'\$\{([^}]*)\}')
# 在 ${} 内部匹配 node_id.key 引用
_VAR_REF_PATTERN = re.compile(r'([a-zA-Z_]\w*|\d+)\.([a-zA-Z_]\w*)')


def _register_node_output(data, var_name, source_act, source_key):
    """向 data.inputs 注册 NodeOutput（幂等：已存在则不重复注册）"""
    ctx_key = f"${{{var_name}}}"
    if ctx_key not in data.inputs:
        data.inputs[ctx_key] = NodeOutput(
            type=Var.SPLICE,
            source_act=source_act,
            source_key=source_key,
        )


def _collect_condition_refs(expr: str, data, known_node_ids: set) -> str:
    """解析条件表达式中的 ${node_id.key} 引用，注册到 data.inputs 并返回重写表达式

    如: "${STATE_1.field_amount} > 5" → "${_STATE_1_field_amount} > 5"
    """

    def _rewrite(m):
        inner = m.group(1).strip()
        rewritten_inner = _VAR_REF_PATTERN.sub(
            lambda rm: _register_and_return(rm.group(1), rm.group(2)),
            inner,
        )
        return f"${{{rewritten_inner}}}"

    def _register_and_return(node_id, key):
        if node_id in known_node_ids:
            var_name = f"{node_id}_{key}"
            _register_node_output(data, var_name, node_id, key)
            return var_name
        return f"{node_id}.{key}"

    return _EXPR_PATTERN.sub(_rewrite, expr)
