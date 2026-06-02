"""pipeline 构建 - 条件解析模块"""
import logging
from collections import deque

from opsflow.core.bamboo_validator import _EXPR_PATTERN, _VAR_REF_PATTERN

logger = logging.getLogger(__name__)


def _parse_edge_conditions(
    edges: list[dict],
    effective_nodes: list[dict] = None,
) -> tuple[dict[str, str], dict[str, dict]]:
    """扫描边定义中的条件和标签，生成 bamboo_engine 可用的条件表达式和 NodeOutput 变量。

    处理逻辑：
    1. 自定义条件（edge.condition）：提取 ${node_id.key} 引用，重写为 var 名（_gwcond_xxx）
    2. success/failure 标签边（从非网关节点或网关节点发出）：
       - 非网关节点：自动注册 _result_{from_id} 变量，
         生成 `${_result_{from_id}} == True/False` 格式。
       - 网关节点：BFS 回溯前驱非网关节点 pred_id，
         生成 `${_result_{pred_id}} == True/False` 格式，
         使条件能正确引用前驱活动节点的执行结果。

    Returns:
        conditions: {"from->to": "condition_expression"}
        auto_vars: {"_result_n1": {"source_act": "n1", "source_key": "_result"}, ...}
    """
    conditions: dict[str, str] = {}
    auto_vars: dict[str, dict] = {}

    # 识别网关节点
    gateway_types = {'exclusive_gateway', 'parallel_gateway', 'conditional_parallel_gateway', 'converge_gateway'}
    gateway_ids = set()
    if effective_nodes:
        gateway_ids = {n['id'] for n in effective_nodes if n.get('node_type') in gateway_types}

    # 构建入边邻接表（用于网关前驱回溯）
    in_edges: dict[str, list[str]] = {}
    for e in edges:
        in_edges.setdefault(e['to'], []).append(e['from'])

    def _find_predecessor_activity(gateway_id: str) -> str | None:
        """BFS 回溯网关的前驱，找到第一个非网关节点 ID"""
        visited = {gateway_id}
        q = deque(in_edges.get(gateway_id, []))
        while q:
            nid = q.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            if nid not in gateway_ids:
                return nid
            for pred in in_edges.get(nid, []):
                if pred not in visited:
                    q.append(pred)
        return None

    def _get_or_create_var(node_id: str, output_key: str) -> str:
        """查找或创建 auto_var 条目，返回变量名"""
        for existing_var, spec in auto_vars.items():
            if spec['source_act'] == node_id and spec['source_key'] == output_key:
                return existing_var
        if output_key == '_result':
            var_name = f"_result_{node_id}"
        else:
            var_name = f"_gwcond_{node_id}_{output_key}"
        auto_vars[var_name] = {'source_act': node_id, 'source_key': output_key}
        return var_name

    def _replace_in_expr(expr: str) -> str:
        """在 expr 内部替换所有 node_id.key → var_name"""
        result = expr
        for m in reversed(list(_VAR_REF_PATTERN.finditer(expr))):
            node_id = m.group(1)
            output_key = m.group(2)
            var_name = _get_or_create_var(node_id, output_key)
            result = result[:m.start()] + var_name + result[m.end():]
        return result

    def _replace_block(m):
        expr = m.group(1).strip()
        rewritten = _replace_in_expr(expr)
        return f"${{{rewritten}}}"

    for edge in edges:
        cond = (edge.get('condition') or '').strip()
        label = (edge.get('label') or '').strip()
        key = f"{edge['from']}->{edge['to']}"

        if cond:
            # 自定义条件：处理 ${node_id.key} 变量引用
            rewritten = _EXPR_PATTERN.sub(_replace_block, cond)
            conditions[key] = rewritten
        elif label in ('success', 'failure') and edge['from'] not in gateway_ids:
            # 非网关出边：自动注册 _result_{from_id} 变量并生成条件
            # 使用 ${_result_n1} == True 格式（变量引用 + 字面比较）而非 ${_result == True}
            # 前者经 Mako 渲染后为 "True == True"，BoolRule 可解析；
            # 后者经 Mako 整体求值为 "True"/"False" 字符串，BoolRule 无法解析。
            var_name = _get_or_create_var(edge['from'], '_result')
            if label == 'success':
                conditions[key] = f"${{{var_name}}} == True"
            else:
                conditions[key] = f"${{{var_name}}} == False"
        elif label in ('success', 'failure') and edge['from'] in gateway_ids:
            # 网关出边（有成功/失败标签）：BFS 回溯前驱活动节点，引用其 _result
            # 网关本身不产生 _result 输出，必须引用前驱活动节点的执行结果
            pred = _find_predecessor_activity(edge['from'])
            if pred:
                var_name = _get_or_create_var(pred, '_result')
                if label == 'success':
                    conditions[key] = f"${{{var_name}}} == True"
                else:
                    conditions[key] = f"${{{var_name}}} == False"

    return conditions, auto_vars


def _get_condition(conditions: dict, from_id: str, to_id: str, label: str = "") -> str:
    """获取边的条件表达式

    优先从 conditions 字典取自定义条件，取不到则根据 label 返回兜底格式。
    兜底格式使用 ${_result} == True/False（变量引用 + 字面比较），确保
    Mako 渲染后 BoolRule 能正确解析。

    正常情况下兜底分支很少执行，因为 _parse_edge_conditions 已为所有
    success/failure 标签边自动生成了条件表达式。
    """
    key = f"{from_id}->{to_id}"
    custom = conditions.get(key)
    if custom:
        return custom
    if label == 'failure':
        return '${_result} == False'
    return '${_result} == True'
