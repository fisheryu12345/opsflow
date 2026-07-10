# -*- coding: utf-8 -*-
"""ITSM Workflow Validator — deploy-time structural checks.

Validates a workflow's states/transitions graph before deployment.
Modeled after OpsFlow's bamboo_validator.py + conflict_checker.py,
but adapted for ITSM's State/Transition data format.

All 12 checks are blocking (status='fail') — deploy is rejected if any fail.
Supports bilingual messages via lang='en' / lang='zh' parameter.
"""

import re
from collections import deque

# BoolRule-supported operators only
VALID_CONDITION_OPS = frozenset({'==', '!=', '>', '<', '>=', '<=', 'in', 'notin'})
_INVALID_OPS_PAT = re.compile(r'\b(contains|startsWith|endsWith|regex|not contains)\b', re.IGNORECASE)
# Match ${node_key.field} references in condition strings
_CONDITION_REF_PAT = re.compile(r'\$\{([^.}]+)\.')


# ─── Bilingual message catalog ───
_MSG = {
    # E1: start_end_exist
    'start_exist_pass':       {'zh': 'START 节点已存在',          'en': 'START node exists'},
    'end_exist_pass':         {'zh': 'END 节点已存在',            'en': 'END node exists'},
    'start_missing_fail':     {'zh': '缺少 START 节点',           'en': 'Missing START node'},
    'start_missing_hint':     {'zh': '请在画布上添加一个 START 节点作为流程起点',
                               'en': 'Please add a START node on the canvas as the workflow entry point'},
    'end_missing_fail':       {'zh': '缺少 END 节点',             'en': 'Missing END node'},
    'end_missing_hint':       {'zh': '请在画布上添加一个 END 节点作为流程终点',
                               'en': 'Please add an END node on the canvas as the workflow exit point'},

    # E2: dag_no_cycle
    'dag_cycle_pass':         {'zh': '流程图为合法 DAG，无环路',    'en': 'Valid DAG, no cycles detected'},
    'dag_cycle_skip':         {'zh': '跳过（缺少 START 节点）',    'en': 'Skipped (no START node)'},
    'dag_cycle_fail':         {'zh': '流程图中存在环路：{path}。请删除或重连连线打破环路',
                               'en': 'Cycle detected: {path}. Please remove or reconnect edges to break the cycle'},
    'dag_cycle_hint':         {'zh': '请检查以上节点间的连线，确保流程为有向无环图（DAG）',
                               'en': 'Check the edges between the above nodes to ensure the workflow is a DAG'},

    # E3: transition_refs_valid
    'trans_ref_pass':         {'zh': '所有连线引用有效',            'en': 'All transition references are valid'},
    'trans_ref_from_fail':    {'zh': "连线 '{name}' 的起点指向不存在的节点 '{key}'，请重新连接",
                               'en': "Transition '{name}' starts from non-existent node '{key}'. Please reconnect"},
    'trans_ref_to_fail':      {'zh': "连线 '{name}' 的终点指向不存在的节点 '{key}'，请重新连接",
                               'en': "Transition '{name}' points to non-existent node '{key}'. Please reconnect"},
    'trans_ref_hint':         {'zh': '请检查连线端点是否已被删除',    'en': 'Check if the connected node has been deleted'},

    # E4: exclusive_gateway_min_edges
    'gw_e4_pass':             {'zh': '排他网关出边数量正常（共 {n} 个）', 'en': 'Exclusive gateway edge count OK ({n} total)'},
    'gw_e4_skip':             {'zh': '无排他网关，跳过',             'en': 'No exclusive gateway, skipped'},
    'gw_e4_fail':             {'zh': "排他网关 '{label}' (key={key}) 只有 {n} 条出边，至少需要 2 条分支",
                               'en': "Exclusive gateway '{label}' (key={key}) has only {n} outgoing edge(s), at least 2 required"},
    'gw_e4_hint':             {'zh': '请为该排他网关添加至少 2 条出边连线',
                               'en': 'Add at least 2 outgoing edges from this exclusive gateway'},

    # E5: exclusive_gateway_conditions
    'gw_e5_pass':             {'zh': '排他网关条件设置正常（共 {n} 个）', 'en': 'Exclusive gateway conditions OK ({n} total)'},
    'gw_e5_skip':             {'zh': '无排他网关，跳过',             'en': 'No exclusive gateway, skipped'},
    'gw_e5_fail':             {'zh': "排他网关 '{label}' (key={key}) 共 {total} 条分支，其中 {miss} 条未设置条件：{edges}。请至少为其中 {need} 条设置条件表达式",
                               'en': "Exclusive gateway '{label}' (key={key}) has {total} branches, {miss} missing conditions: {edges}. At least {need} branch(es) need condition expressions"},
    'gw_e5_hint':             {'zh': '请在排他网关的每条分支上设置条件表达式（可留一条作为默认分支）',
                               'en': 'Set a condition expression on each branch (one may be left as default)'},

    # E6: conditional_parallel_conditions
    'gw_e6_pass':             {'zh': '条件并行网关条件设置正常（共 {n} 个）', 'en': 'Conditional parallel gateway conditions OK ({n} total)'},
    'gw_e6_skip':             {'zh': '无条件并行网关，跳过',           'en': 'No conditional parallel gateway, skipped'},
    'gw_e6_fail':             {'zh': "条件并行网关 '{label}' (key={key}) 的分支 '{edge}' (key={tid}) 未设置条件表达式",
                               'en': "Conditional parallel gateway '{label}' (key={key}) branch '{edge}' (key={tid}) has no condition expression"},
    'gw_e6_hint':             {'zh': '条件并行网关每条分支都必须设置条件，请在该分支上添加条件表达式',
                               'en': 'Every branch of a conditional parallel gateway must have a condition. Add one to this branch'},

    # E7: converge_gateway_min_in
    'gw_e7_pass':             {'zh': '汇聚网关入边数量正常（共 {n} 个）', 'en': 'Converge gateway in-edge count OK ({n} total)'},
    'gw_e7_skip':             {'zh': '无汇聚网关，跳过',             'en': 'No converge gateway, skipped'},
    'gw_e7_fail':             {'zh': "汇聚网关 '{label}' (key={key}) 只有 {n} 条入边，汇聚网关至少需要 2 条入边，否则请改用普通节点",
                               'en': "Converge gateway '{label}' (key={key}) has only {n} in-edge(s). A converge gateway needs at least 2, otherwise use a normal node instead"},
    'gw_e7_hint':             {'zh': '请为该汇聚网关添加至少 2 条入边连线，或将节点类型改为普通节点',
                               'en': 'Add at least 2 incoming edges to this converge gateway, or change its type to a normal node'},

    # E8: duplicate_node_key
    'dup_key_pass':           {'zh': '所有节点 key 唯一',          'en': 'All node keys are unique'},
    'dup_key_fail':           {'zh': "节点 key '{key}' 重复出现在 '{name1}' 和 '{name2}'，请确保每个节点有唯一标识",
                               'en': "Duplicate node key '{key}' found on '{name1}' and '{name2}'. Each node must have a unique key"},
    'dup_key_hint':           {'zh': '请修改其中一个节点的 key 或删除重复节点',
                               'en': 'Change one of the node keys or remove the duplicate node'},

    # E9: orphan_nodes
    'orphan_pass':            {'zh': '所有节点均有入边和出边',        'en': 'All nodes have incoming and outgoing edges'},
    'orphan_no_in_fail':      {'zh': "节点 '{label}' (key={key}) 没有任何入边，请为其添加入边连线",
                               'en': "Node '{label}' (key={key}) has no incoming edges. Please add an incoming edge"},
    'orphan_no_out_fail':     {'zh': "节点 '{label}' (key={key}) 没有任何出边",
                               'en': "Node '{label}' (key={key}) has no outgoing edges"},
    'orphan_no_in_hint':      {'zh': '请从上游节点添加一条连线指向该节点',
                               'en': 'Add an edge from an upstream node to this node'},
    'orphan_no_out_hint':     {'zh': '请从该节点添加一条连线指向下游节点',
                               'en': 'Add an edge from this node to a downstream node'},

    # E10: unreachable_nodes
    'unreachable_pass':       {'zh': '所有节点从 START 可达',       'en': 'All nodes reachable from START'},
    'unreachable_fail':       {'zh': "节点 '{label}' (key={key}) 从 START 无法到达，请添加连线或删除该节点",
                               'en': "Node '{label}' (key={key}) is unreachable from START. Add an edge or delete this node"},
    'unreachable_hint':       {'zh': '请检查是否有连线通往该节点，或直接删除',
                               'en': 'Check if any edge leads to this node, or delete it'},

    # E11: dead_end_paths
    'dead_end_pass':          {'zh': '所有非 END 节点均有出边',       'en': 'All non-END nodes have outgoing edges'},
    'dead_end_fail':          {'zh': "节点 '{label}' (key={key}) 没有任何出边且不是 END 节点，流程到此会中断",
                               'en': "Node '{label}' (key={key}) has no outgoing edges and is not an END node. The workflow will dead-end here"},
    'dead_end_hint':          {'zh': '请从该节点添加连线到下游节点或 END 节点',
                               'en': 'Add an edge from this node to a downstream node or the END node'},

    # E12: condition_invalid_syntax
    'cond_syntax_pass':       {'zh': '所有条件表达式运算符合法',       'en': 'All condition expression operators are valid'},
    'cond_syntax_fail':       {'zh': "网关 '{from_label}' 的分支 '→{to_label}' (key={tid}) 条件表达式包含不支持的运算符 '{op}'（仅支持 {valid_ops}）",
                               'en': "Gateway '{from_label}' branch '→{to_label}' (key={tid}) contains unsupported operator '{op}' (only {valid_ops} supported)"},
    'cond_syntax_hint':       {'zh': "请将 '{op}' 替换为支持的运算符。例如 'contains' 可改为 'in': ${{node.field}} in ['值1','值2']",
                               'en': "Replace '{op}' with a supported operator. E.g. 'contains' → 'in': ${{node.field}} in ['val1','val2']"},

    # E13: processor check for approval/sign nodes
    'processor_pass':         {'zh': '所有审批/会签节点已配置处理人',    'en': 'All approval/sign nodes have processors configured'},
    'processor_fail':         {'zh': "节点 '{label}' (key={key}, type={stype}) 未配置处理人",
                               'en': "Node '{label}' (key={key}, type={stype}) has no processor configured"},
    'processor_hint':         {'zh': '请点击该节点，选择处理人类型并指定处理人',
                               'en': 'Click the node, select a processor type and assign a processor'},
    'processor_skip':         {'zh': '无审批/会签节点，跳过',           'en': 'No approval/sign nodes, skipped'},

    # E14: fork-join gateway count matching
    'gw_balance_pass':        {'zh': '并行网关与汇聚网关数量匹配',       'en': 'Fork and join gateway counts match'},
    'gw_balance_fail':        {'zh': '并行/条件并行网关 ({forks} 个) 与汇聚网关 ({joins} 个) 数量不匹配，请为每个分支网关添加对应的汇聚网关',
                               'en': 'Fork gateways ({forks}) and join gateways ({joins}) count mismatch. Add a converge gateway for each fork'},
    'gw_balance_hint':        {'zh': '每个 PARALLEL / CONDITIONAL_PARALLEL 网关必须有一个 COVERAGE 汇聚网关配对',
                               'en': 'Each PARALLEL / CONDITIONAL_PARALLEL gateway must have a matching COVERAGE converge gateway'},
    'gw_balance_skip':        {'zh': '无并行/汇聚网关，跳过',            'en': 'No parallel/converge gateways, skipped'},
}


def _t(msg_key: str, lang: str = 'zh', **fmt) -> str:
    """Lookup bilingual message by msg_key and fill format placeholders."""
    entry = _MSG.get(msg_key, {})
    text = entry.get(lang, entry.get('zh', msg_key))
    if fmt:
        text = text.format(**fmt)
    return text


def validate_workflow(states: dict, transitions: dict, lang: str = 'zh') -> dict:
    """Validate ITSM workflow structure before deployment.

    Args:
        states: dict keyed by node_key (or id), each value is a dict with at least
                {'type': str, 'name': str, 'node_key': str}.
        transitions: dict keyed by transition id, each value is a dict with at least
                     {'from_node_key': str, 'to_node_key': str, 'condition': str|dict,
                      'name': str, 'condition_type': str}.
        lang: 'zh' or 'en' — language for message/suggestion output.

    Returns:
        {'valid': bool, 'checks': list[dict]} where each check has
        {'rule': str, 'status': 'pass'|'fail', 'message': str, 'suggestion': str}.
    """
    checks = []

    # ─── E1: START/END existence ───
    start_keys = _find_type(states, 'START')
    end_keys = _find_type(states, 'END')
    if start_keys:
        checks.append(_pass('start_end_exist', _t('start_exist_pass', lang)))
    else:
        checks.append(_fail('start_end_exist', _t('start_missing_fail', lang),
                            _t('start_missing_hint', lang)))
    if end_keys:
        checks.append(_pass('start_end_exist', _t('end_exist_pass', lang)))
    else:
        checks.append(_fail('start_end_exist', _t('end_missing_fail', lang),
                            _t('end_missing_hint', lang)))

    # ─── E3: Transition references must point to existing states ───
    valid_keys = set(states.keys())
    for tid, t in transitions.items():
        t_name = t.get('name', '') or tid
        fnk = t.get('from_node_key', '')
        tnk = t.get('to_node_key', '')
        if fnk and fnk not in valid_keys:
            checks.append(_fail('transition_refs_valid',
                                _t('trans_ref_from_fail', lang, name=t_name, key=fnk),
                                _t('trans_ref_hint', lang)))
        if tnk and tnk not in valid_keys:
            checks.append(_fail('transition_refs_valid',
                                _t('trans_ref_to_fail', lang, name=t_name, key=tnk),
                                _t('trans_ref_hint', lang)))
    if not any(c['rule'] == 'transition_refs_valid' for c in checks):
        checks.append(_pass('transition_refs_valid', _t('trans_ref_pass', lang)))

    # ─── Build adjacency for graph algorithms ───
    # Build id→key lookup for resolving transitions with empty node_keys
    id_to_key = {}
    for k, s in states.items():
        sid = s.get('id')
        if sid:
            id_to_key[sid] = k
            id_to_key[str(sid)] = k

    adj = {k: set() for k in states}
    in_deg = {k: 0 for k in states}
    edge_map = {}  # (from_key, to_key) -> transition id
    for tid, t in transitions.items():
        f = t.get('from_node_key', '')
        tgt = t.get('to_node_key', '')
        # Fallback: resolve via state ID when node_key is empty
        if not f:
            fsid = t.get('from_state_id')
            if fsid and fsid in id_to_key:
                f = id_to_key[fsid]
        if not tgt:
            tsid = t.get('to_state_id')
            if tsid and tsid in id_to_key:
                tgt = id_to_key[tsid]
        if f in valid_keys and tgt in valid_keys:
            adj[f].add(tgt)
            in_deg[tgt] += 1
            edge_map[(f, tgt)] = tid

    # ─── E8: Duplicate node_key ───
    seen_keys = {}
    dupes = []
    for k, s in states.items():
        nk = s.get('node_key', '') or k
        if nk in seen_keys:
            dupes.append((nk, seen_keys[nk], s.get('name', k)))
        else:
            seen_keys[nk] = s.get('name', k)
    if dupes:
        for nk, name1, name2 in dupes:
            checks.append(_fail('duplicate_node_key',
                                _t('dup_key_fail', lang, key=nk, name1=name1, name2=name2),
                                _t('dup_key_hint', lang)))
    else:
        checks.append(_pass('duplicate_node_key', _t('dup_key_pass', lang)))

    # ─── E2: DAG cycle detection (DFS) ───
    if start_keys:
        has_cycle, cycle_nodes = _detect_cycle(adj, states)
        if has_cycle:
            path = ' → '.join(states.get(n, {}).get('name', n) for n in cycle_nodes)
            checks.append(_fail('dag_no_cycle',
                                _t('dag_cycle_fail', lang, path=path),
                                _t('dag_cycle_hint', lang)))
        else:
            checks.append(_pass('dag_no_cycle', _t('dag_cycle_pass', lang)))
    else:
        checks.append(_pass('dag_no_cycle', _t('dag_cycle_skip', lang)))

    # ─── E9: Orphan nodes ───
    orphan_found = False
    for k, s in states.items():
        stype = s.get('type', '')
        if stype in ('START', 'END'):
            continue
        label = s.get('name', k)
        if in_deg.get(k, 0) == 0:
            orphan_found = True
            checks.append(_fail('orphan_nodes',
                                _t('orphan_no_in_fail', lang, label=label, key=k),
                                _t('orphan_no_in_hint', lang)))
        if k in adj and len(adj[k]) == 0:
            orphan_found = True
            checks.append(_fail('orphan_nodes',
                                _t('orphan_no_out_fail', lang, label=label, key=k),
                                _t('orphan_no_out_hint', lang)))
    if not orphan_found:
        checks.append(_pass('orphan_nodes', _t('orphan_pass', lang)))

    # ─── E10: Unreachable nodes ───
    unreachable_found = False
    if start_keys:
        reachable = _bfs(start_keys, adj)
        for k, s in states.items():
            if k not in reachable:
                label = s.get('name', k)
                unreachable_found = True
                checks.append(_fail('unreachable_nodes',
                                    _t('unreachable_fail', lang, label=label, key=k),
                                    _t('unreachable_hint', lang)))
    if not unreachable_found:
        checks.append(_pass('unreachable_nodes', _t('unreachable_pass', lang)))

    # ─── E11: Dead-end paths ───
    dead_end_found = False
    for k, s in states.items():
        stype = s.get('type', '')
        if stype == 'END':
            continue
        if k in adj and len(adj[k]) == 0:
            label = s.get('name', k)
            dead_end_found = True
            checks.append(_fail('dead_end_paths',
                                _t('dead_end_fail', lang, label=label, key=k),
                                _t('dead_end_hint', lang)))
    if not dead_end_found:
        checks.append(_pass('dead_end_paths', _t('dead_end_pass', lang)))

    # ─── E13: Processor configuration check for APPROVAL/SIGN nodes ───
    # PERSON type needs explicit user IDs; other types (STARTER, ROLE, etc.)
    # auto-resolve at runtime so empty processors field is valid.
    proc_found = False
    proc_fails = []
    for k, s in states.items():
        stype = s.get('type', '')
        if stype not in ('APPROVAL', 'SIGN'):
            continue
        proc_found = True
        proc_type = (s.get('processors_type') or '').strip()
        # Only PERSON type requires explicit processor IDs
        if proc_type == 'PERSON':
            processors = (s.get('processors') or '').strip()
            if not processors or processors in ('[]', '[ ]'):
                label = s.get('name', k)
                proc_fails.append((label, k, stype))
    if proc_fails:
        for label, k, stype in proc_fails:
            checks.append(_fail('processor_check',
                                _t('processor_fail', lang, label=label, key=k, stype=stype),
                                _t('processor_hint', lang)))
    if proc_found:
        if not proc_fails:
            checks.append(_pass('processor_check', _t('processor_pass', lang)))
    else:
        checks.append(_pass('processor_check', _t('processor_skip', lang)))

    # ─── E4-E7, E12, E14: Gateway constraints + condition checks ───
    gw_checks = _check_gateways(states, transitions, adj, in_deg, lang)
    checks.extend(gw_checks)

    # ─── Build result ───
    valid = not any(c['status'] == 'fail' for c in checks)
    return {'valid': valid, 'checks': checks}


# ─── Helpers ───

def _pass(rule: str, message: str) -> dict:
    return {'rule': rule, 'status': 'pass', 'message': message, 'suggestion': ''}


def _fail(rule: str, message: str, suggestion: str) -> dict:
    return {'rule': rule, 'status': 'fail', 'message': message, 'suggestion': suggestion}


def _find_type(states: dict, type_name: str) -> list:
    return [k for k, s in states.items() if s.get('type') == type_name]


def _detect_cycle(adj: dict, states: dict) -> tuple:
    """DFS-based cycle detection. Returns (has_cycle: bool, cycle_path: list).

    Uses 3-color marking: WHITE=unvisited, GRAY=in current path, BLACK=done.
    A back-edge to a GRAY node indicates a cycle.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {k: WHITE for k in adj}
    parent = {}
    cycle_nodes = []

    def dfs(node):
        color[node] = GRAY
        for neighbor in adj.get(node, set()):
            if color[neighbor] == GRAY:
                # Found a cycle — reconstruct path
                path = [neighbor, node]
                cur = node
                while cur in parent and parent[cur] != neighbor:
                    cur = parent[cur]
                    path.append(cur)
                path.append(neighbor)
                path.reverse()
                cycle_nodes.extend(path)
                return True
            if color[neighbor] == WHITE:
                parent[neighbor] = node
                if dfs(neighbor):
                    return True
        color[node] = BLACK
        return False

    for node in adj:
        if color[node] == WHITE:
            if dfs(node):
                return True, cycle_nodes

    return False, []


def _bfs(start_keys: list, adj: dict) -> set:
    reachable = set(start_keys)
    queue = deque(start_keys)
    while queue:
        node = queue.popleft()
        for nb in adj.get(node, set()):
            if nb not in reachable:
                reachable.add(nb)
                queue.append(nb)
    return reachable


def _check_gateways(states: dict, transitions: dict, adj: dict,
                    in_deg: dict, lang: str = 'zh') -> list:
    """Run E4-E7 + E12 gateway checks. Each rule gets its own pass/fail line."""
    checks = []
    valid_ops_str = ' '.join(sorted(VALID_CONDITION_OPS))

    exclusive_gws = [(k, s) for k, s in states.items() if s.get('type') == 'EXCLUSIVE']
    cond_parallel_gws = [(k, s) for k, s in states.items() if s.get('type') == 'CONDITIONAL_PARALLEL']
    converge_gws = [(k, s) for k, s in states.items() if s.get('type') == 'COVERAGE']

    # ─── E4: Exclusive gateway min edges ───
    if exclusive_gws:
        e4_fails = []
        for k, s in exclusive_gws:
            label = s.get('name', k)
            out_edges = [t for _, t in transitions.items() if t.get('from_node_key') == k]
            if len(out_edges) < 2:
                e4_fails.append((label, k, len(out_edges)))
        if e4_fails:
            for label, k, n in e4_fails:
                checks.append(_fail('exclusive_gateway_min_edges',
                                    _t('gw_e4_fail', lang, label=label, key=k, n=n),
                                    _t('gw_e4_hint', lang)))
        else:
            checks.append(_pass('exclusive_gateway_min_edges',
                                _t('gw_e4_pass', lang, n=len(exclusive_gws))))
    else:
        checks.append(_pass('exclusive_gateway_min_edges', _t('gw_e4_skip', lang)))

    # ─── E5: Exclusive gateway conditions ───
    if exclusive_gws:
        e5_fails = []
        for k, s in exclusive_gws:
            label = s.get('name', k)
            out_edges = [t for _, t in transitions.items() if t.get('from_node_key') == k]
            if len(out_edges) >= 2:
                missing = []
                for t in out_edges:
                    tid = t.get('id', '?')
                    cond = _extract_condition(t)
                    if not cond:
                        tgt_key = t.get('to_node_key', '?')
                        tgt_label = states.get(tgt_key, {}).get('name', tgt_key)
                        t_name = t.get('name', '') or f'→{tgt_label}'
                        missing.append(f"'{t_name}' (key={tid})")
                # At most 1 default branch (no condition) allowed — fail if 2+ missing
                if len(missing) > 1:
                    e5_fails.append((label, k, len(out_edges), len(missing), ' '.join(missing)))
        if e5_fails:
            for label, k, total, miss_cnt, edges_str in e5_fails:
                checks.append(_fail('exclusive_gateway_conditions',
                                    _t('gw_e5_fail', lang, label=label, key=k, total=total,
                                       miss=miss_cnt, edges=edges_str, need=total - 1),
                                    _t('gw_e5_hint', lang)))
        else:
            checks.append(_pass('exclusive_gateway_conditions',
                                _t('gw_e5_pass', lang, n=len(exclusive_gws))))
    else:
        checks.append(_pass('exclusive_gateway_conditions', _t('gw_e5_skip', lang)))

    # ─── E6: Conditional parallel gateway conditions ───
    if cond_parallel_gws:
        e6_fails = []
        for k, s in cond_parallel_gws:
            label = s.get('name', k)
            out_edges = [t for _, t in transitions.items() if t.get('from_node_key') == k]
            for t in out_edges:
                cond = _extract_condition(t)
                if not cond:
                    tid = t.get('id', '?')
                    tgt_key = t.get('to_node_key', '?')
                    tgt_label = states.get(tgt_key, {}).get('name', tgt_key)
                    t_name = t.get('name', '') or f'→{tgt_label}'
                    e6_fails.append((label, k, t_name, tid))
        if e6_fails:
            for label, k, t_name, tid in e6_fails:
                checks.append(_fail('conditional_parallel_conditions',
                                    _t('gw_e6_fail', lang, label=label, key=k, edge=t_name, tid=tid),
                                    _t('gw_e6_hint', lang)))
        else:
            checks.append(_pass('conditional_parallel_conditions',
                                _t('gw_e6_pass', lang, n=len(cond_parallel_gws))))
    else:
        checks.append(_pass('conditional_parallel_conditions', _t('gw_e6_skip', lang)))

    # ─── E7: Converge gateway min in-edges ───
    if converge_gws:
        e7_fails = []
        for k, s in converge_gws:
            label = s.get('name', k)
            in_count = in_deg.get(k, 0)
            if in_count < 2:
                e7_fails.append((label, k, in_count))
        if e7_fails:
            for label, k, n in e7_fails:
                checks.append(_fail('converge_gateway_min_in',
                                    _t('gw_e7_fail', lang, label=label, key=k, n=n),
                                    _t('gw_e7_hint', lang)))
        else:
            checks.append(_pass('converge_gateway_min_in',
                                _t('gw_e7_pass', lang, n=len(converge_gws))))
    else:
        checks.append(_pass('converge_gateway_min_in', _t('gw_e7_skip', lang)))

    # ─── E14: Fork-join gateway count matching ───
    fork_count = len(exclusive_gws) + len(cond_parallel_gws)
    # PARALLEL gateways also count as forks
    parallel_gws = [(k, s) for k, s in states.items() if s.get('type') == 'PARALLEL']
    fork_count += len(parallel_gws)
    join_count = len(converge_gws)
    if fork_count > 0 or join_count > 0:
        if fork_count <= join_count:
            checks.append(_pass('gw_balance',
                                _t('gw_balance_pass', lang)))
        else:
            checks.append(_fail('gw_balance',
                                _t('gw_balance_fail', lang, forks=fork_count, joins=join_count),
                                _t('gw_balance_hint', lang)))
    else:
        checks.append(_pass('gw_balance', _t('gw_balance_skip', lang)))

    # ─── E12: Condition operator syntax ───
    bad_found = False
    for tid, t in transitions.items():
        cond = _extract_condition(t)
        if not cond or not isinstance(cond, str):
            continue
        bad_ops = _INVALID_OPS_PAT.findall(cond)
        if bad_ops:
            f_key = t.get('from_node_key', '?')
            tgt_key = t.get('to_node_key', '?')
            from_s = states.get(f_key, {})
            tgt_s = states.get(tgt_key, {})
            from_label = from_s.get('name', f_key)
            tgt_label = tgt_s.get('name', tgt_key)
            bad_op = bad_ops[0]
            checks.append(_fail('condition_invalid_syntax',
                                _t('cond_syntax_fail', lang, from_label=from_label,
                                   to_label=tgt_label, tid=tid, op=bad_op, valid_ops=valid_ops_str),
                                _t('cond_syntax_hint', lang, op=bad_op)))
            bad_found = True
    if not bad_found:
        checks.append(_pass('condition_invalid_syntax', _t('cond_syntax_pass', lang)))

    return checks


def _extract_condition(transition: dict) -> str:
    """Extract condition string from transition. Returns '' for structured dicts
    (by_field type) — E12 regex only applies to string expressions."""
    cond = transition.get('condition', '')
    if isinstance(cond, dict):
        # Structured by_field condition — inspect rules for inline expressions
        # but don't return str(cond) which would introduce Python repr artifacts
        rules = cond.get('rules', [])
        if isinstance(rules, list):
            # Concatenate only the expressions from structured rules
            parts = []
            for r in rules:
                if isinstance(r, dict) and r.get('value') and isinstance(r['value'], str):
                    parts.append(r['value'])
            return ' '.join(parts) if parts else ''
        return ''
    if isinstance(cond, str):
        return cond.strip()
    return ''
