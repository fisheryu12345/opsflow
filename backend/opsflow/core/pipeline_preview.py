"""Pipeline 预览与清理 — 执行方案预览树生成

根据 ExecutionScheme 排除节点后，生成清理后的 pipeline_tree：

  1. 移除排除节点（重连上下游）
  2. 移除无用的并行→汇聚网关对
  3. 清理未引用的全局变量

参考 bk_sops pipeline_web/preview_base.py PipelineTemplateWebPreviewer
     + pipeline_web/parser/clean.py PipelineWebTreeCleaner
"""

import copy
import logging

logger = logging.getLogger(__name__)


class PipelinePreviewService:
    """执行方案预览服务 — 根据排除节点生成清理后的 pipeline 树"""

    @staticmethod
    def preview_exclude_nodes(pipeline_tree: dict, exclude_nodes_id: list) -> dict:
        """根据排除节点 ID 列表生成预览树

        Args:
            pipeline_tree: 原始 pipeline tree (nodes/edges 格式)
            exclude_nodes_id: 要排除的节点 ID 列表

        Returns:
            dict: 清理后的 pipeline tree
        """
        if not exclude_nodes_id:
            return copy.deepcopy(pipeline_tree)

        result = copy.deepcopy(pipeline_tree)
        nodes = result.get('nodes', [])
        edges = result.get('edges', [])

        if not nodes or not edges:
            return result

        # 收集生效节点（排除起止事件）
        effective_ids = {n['id'] for n in nodes
                        if n.get('node_type') not in ('start_event', 'end_event')}

        # 校验排除节点存在
        for nid in exclude_nodes_id:
            if nid not in effective_ids:
                logger.warning("[Preview] 排除节点 '%s' 不在有效节点列表中", nid)

        # 1. 移除排除节点（重连上下游）
        for nid in exclude_nodes_id:
            edges = PipelinePreviewService._remove_node(nid, edges)

        # 从 nodes 中移除排除的节点
        result['nodes'] = [n for n in nodes if n['id'] not in exclude_nodes_id]
        result['edges'] = edges

        # 2. 移除无用的并行→汇聚网关对
        result = PipelinePreviewService._remove_useless_parallel(result)

        # 3. 清理未引用的全局变量
        result['global_vars'] = PipelinePreviewService._remove_useless_global_vars(
            result, exclude_nodes_id,
        )

        return result

    @staticmethod
    def _remove_node(node_id: str, edges: list) -> list:
        """移除一个节点，重连上下游

        前驱节点 → [被移除节点] → 后继节点
        变为：
        前驱节点 → 后继节点
        """
        # 找出入边和出边
        incoming = [e for e in edges if e.get('to') == node_id]
        outgoing = [e for e in edges if e.get('from') == node_id]

        if not incoming or not outgoing:
            # 孤立节点或边界节点，直接移除其关联边
            return [e for e in edges
                    if e.get('from') != node_id and e.get('to') != node_id]

        # 从 edges 中移除入边和出边
        remaining = [e for e in edges
                     if e.get('from') != node_id and e.get('to') != node_id]

        # 将每个入边的源节点连接到每个出边的目标节点
        for ie in incoming:
            for oe in outgoing:
                remaining.append({
                    'from': ie.get('from'),
                    'to': oe.get('to'),
                    'label': oe.get('label', ''),
                })

        return remaining

    @staticmethod
    def _remove_useless_parallel(tree: dict) -> dict:
        """移除无用的并行网关对

        查找 parallel_gateway → 中间没有任何其他节点 → converge_gateway 的模式，
        如果 parallel 的所有出边都汇聚到同一个 converge，删除这对网关。

        Reference: bk_sops _remove_useless_parallel()
        """
        nodes = tree.get('nodes', [])
        edges = tree.get('edges', [])

        # 构建邻接表和逆向邻接表
        out_map = {}  # node_id -> [(target, edge)]
        in_map = {}   # node_id -> [(source, edge)]
        for e in edges:
            f = e.get('from')
            t = e.get('to')
            out_map.setdefault(f, []).append((t, e))
            in_map.setdefault(t, []).append((f, e))

        # 找出所有并行网关
        parallel_nodes = [n for n in nodes
                          if n.get('node_type') == 'parallel_gateway']
        converge_nodes = {n['id'] for n in nodes
                          if n.get('node_type') == 'converge_gateway'}

        removed_ids = set()

        for pn in parallel_nodes:
            pid = pn['id']
            if pid in removed_ids:
                continue

            # 获取并行网关所有出边目标
            outgoing_targets = {t for t, _ in out_map.get(pid, [])}

            if not outgoing_targets:
                continue

            # 检查所有这些目标的唯一共同汇聚点
            # BFS 从每个出边目标找汇聚网关
            common_converge = None
            all_converge_to_same = True

            for target in outgoing_targets:
                converge = PipelinePreviewService._bfs_find_converge(target, edges, converge_nodes)
                if converge is None:
                    all_converge_to_same = False
                    break
                if common_converge is None:
                    common_converge = converge
                elif converge != common_converge:
                    all_converge_to_same = False
                    break

            if not all_converge_to_same or common_converge is None:
                continue

            cid = common_converge

            # 检查 parallel 和 converge 之间是否无其他节点
            nodes_between = PipelinePreviewService._find_nodes_between(
                pid, cid, edges, {pid, cid},
            )
            if nodes_between:
                continue

            # 可安全移除这对网关
            removed_ids.add(pid)
            removed_ids.add(cid)

            # 重连：parallel 的前驱 -> converge 的后继
            parallel_preds = [s for s, _ in in_map.get(pid, [])]
            converge_succs = [t for t, _ in out_map.get(cid, [])]

            # 移除 parallel 相关边
            edges = [e for e in edges
                     if e.get('from') != pid and e.get('to') != pid
                     and e.get('from') != cid and e.get('to') != cid]

            # 添加新边：前驱 -> 后继
            for pred in parallel_preds:
                for succ in converge_succs:
                    edges.append({'from': pred, 'to': succ})

            # 更新 out_map/in_map 用于后续迭代
            # (copy 时已非引用，此处重建)
            out_map = {}
            in_map = {}
            for e in edges:
                f = e.get('from')
                t = e.get('to')
                out_map.setdefault(f, []).append((t, e))
                in_map.setdefault(t, []).append((f, e))

        # 移除被删除的网关节点
        tree['nodes'] = [n for n in nodes if n['id'] not in removed_ids]
        tree['edges'] = edges

        return tree

    @staticmethod
    def _bfs_find_converge(start_id: str, edges: list, converge_ids: set) -> str | None:
        """BFS 从 start_id 向下游查找第一个汇聚网关"""
        from collections import deque

        visited = {start_id}
        queue = deque([start_id])

        while queue:
            nid = queue.popleft()
            if nid in converge_ids:
                return nid
            for e in edges:
                if e.get('from') == nid and e.get('to') not in visited:
                    visited.add(e['to'])
                    queue.append(e['to'])

        return None

    @staticmethod
    def _find_nodes_between(start_id: str, end_id: str, edges: list,
                            excluded: set) -> set:
        """BFS 找 start 到 end 之间的所有中间节点"""
        from collections import deque

        visited = {start_id}
        queue = deque([(start_id, set())])

        while queue:
            nid, path = queue.popleft()
            if nid == end_id:
                # path 中排除 excluded 和端节点
                return {n for n in path if n not in excluded and n != start_id and n != end_id}

            for e in edges:
                if e.get('from') == nid and e.get('to') not in visited:
                    visited.add(e['to'])
                    new_path = path | {e['to']}
                    queue.append((e['to'], new_path))

        return set()

    @staticmethod
    def _remove_useless_global_vars(tree: dict, exclude_nodes_id: list) -> dict:
        """清理未引用的全局变量

        追踪所有节点的 params 中对全局变量的引用，
        移除未被任何节点引用的变量。

        Reference: bk_sops _remove_useless_constants()
        """
        nodes = tree.get('nodes', [])
        global_vars = tree.get('global_vars', {})
        edges = tree.get('edges', [])

        if not global_vars:
            return global_vars

        # 收集所有被引用的变量键名
        referenced = set()

        # 节点 params 中的引用
        for node in nodes:
            if node['id'] in exclude_nodes_id:
                continue
            params = node.get('params', {}) or {}
            for k, v in params.items():
                if isinstance(v, str):
                    # 检查 ${key} 引用模式
                    import re
                    for m in re.finditer(r'\$\{[^}]+\}', v):
                        referenced.add(m.group(0))
                # params 中值为 key 本身也可能引用
                if isinstance(v, str) and v.startswith('${') and v.endswith('}'):
                    referenced.add(v)

        # 边条件中的引用
        for e in edges:
            cond = e.get('condition', '')
            if cond:
                import re
                for m in re.finditer(r'\$\{[^}]+\}', cond):
                    referenced.add(m.group(0))

        # 保留被引用的变量
        new_vars = {k: v for k, v in global_vars.items() if k in referenced}

        # 记录被清理的变量
        removed = set(global_vars.keys()) - set(new_vars.keys())
        if removed:
            logger.info("[Preview] Removed %d unreferenced global vars: %s",
                        len(removed), removed)

        return new_vars
