"""pipeline 构建 - 条件解析模块"""
from opsflow.core.bamboo_validator import _EXPR_PATTERN, _VAR_REF_PATTERN


def _parse_edge_conditions(edges: list[dict]) -> tuple[dict[str, str], dict[str, dict]]:
    """扫描边定义中的自定义条件，提取 ${node_id.key} 引用

    将条件中的 ${node_id.key} 重写为自动生成的 var 名（如 _gwcond_node_1_cpu），
    并返回 NodeOutput 声明，供 build_bamboo_pipeline 在步骤 6 注入 Data.inputs。

    Returns:
        conditions: {"from->to": "rewritten_condition"}
        auto_vars: {"_gwcond_node_1_cpu": {"source_act": "node_1", "source_key": "cpu"}}
    """
    conditions: dict[str, str] = {}
    auto_vars: dict[str, dict] = {}

    def _replace_in_expr(expr: str) -> str:
        """在 expr 内部替换所有 node_id.key → var_name"""
        result = expr
        for m in reversed(list(_VAR_REF_PATTERN.finditer(expr))):
            node_id = m.group(1)
            output_key = m.group(2)
            var_name = None
            for existing_var, spec in auto_vars.items():
                if spec['source_act'] == node_id and spec['source_key'] == output_key:
                    var_name = existing_var
                    break
            if var_name is None:
                var_name = f"_gwcond_{node_id}_{output_key}"
                auto_vars[var_name] = {'source_act': node_id, 'source_key': output_key}
            result = result[:m.start()] + var_name + result[m.end():]
        return result

    def _replace_block(m):
        expr = m.group(1).strip()
        rewritten = _replace_in_expr(expr)
        return f"${{{rewritten}}}"

    for edge in edges:
        cond = (edge.get('condition') or '').strip()
        if not cond:
            continue
        key = f"{edge['from']}->{edge['to']}"
        rewritten = _EXPR_PATTERN.sub(_replace_block, cond)
        conditions[key] = rewritten

    return conditions, auto_vars


def _get_condition(conditions: dict, from_id: str, to_id: str, label: str = "") -> str:
    """获取边的自定义条件，fallback 到基于 label 的默认条件"""
    key = f"{from_id}->{to_id}"
    custom = conditions.get(key)
    if custom:
        return custom
    if label == 'failure':
        return '${_result == False}'
    return '${_result == True}'
