"""DR 拓扑服务 — Neo4j 查询 + AI Prompt + 拓扑描述

职责（从 views/mixins/template_dr.py 拆分）:
  - 基于 Neo4j 查询 DR 组拓扑
  - 构建 AI readable 的拓扑描述
  - 内置 pipeline fallback 生成
"""
import json
import logging

logger = logging.getLogger(__name__)


# ── DR Pipeline AI Prompt 模板 ───────────────────────────────

DR_SYSTEM_PROMPT = """你是一个运维 DR (Disaster Recovery) 专家。请根据给定的 DR 拓扑信息，生成一个标准的灾备切换 Pipeline。

拓扑信息中会包含 CALLS（进程调用关系）列表，**这是判断启停顺序的核心依据**。

DR Pipeline 的结构必须包含以下步骤：
1. 停止主站进程（agent_process_stop）— 逐个停止主站运行中的进程
2. 启动备站进程（agent_process_start）— 逐个启动备站对应的进程
3. 验证备站健康（process_status）— 验证备站进程是否正常

===== CALLS 依赖顺序规则（严格遵循） =====

拓扑中会给出进程间的 CALLS 关系，例如：
  myapp → redis
  myapp → mysql
  表示 myapp 调用了 redis 和 mysql

**停止顺序**（依赖反序，先停调用方）：
  CALLS 关系的方向是 A→B 表示 A 依赖 B。
  停止时必须先停 A（调用方/上层），再停 B（被依赖方/底层）。
  示例: myapp → redis → mysql  →  停止顺序: myapp → redis → mysql

**启动顺序**（依赖正序，先启被依赖方）：
  启动时先启 B（被依赖方/底层），再启 A（调用方/上层）。
  示例: myapp → redis → mysql  →  启动顺序: mysql → redis → myapp

**并行规则**：
  互相之间没有 CALLS 关系的进程可以放在同一个并行阶段。
  例如：redis 和 mysql 互不调用 → 可以同时启/停。

===== 输出约束 =====

- node id 用 node_1, node_2, node_3... 格式（严格遵循此格式）
- 每个 agent_process_stop 节点的 params: {"service_name": "进程名", "target_host": "主机IP"}
- 每个 agent_process_start 节点的 params: {"service_name": "进程名", "target_host": "主机IP"}
- 用 service_name（进程名）作为目标标识，不使用 instance_id

Pipeline Tree JSON 格式：
{
  "nodes": [
    {"id": "node_1", "label": "停止 myapp", "node_type": "", "atom_type": "agent_process_stop", "params": {"service_name": "myapp", "target_host": "10.0.1.2"}},
    {"id": "node_2", "label": "启动 myapp", "node_type": "", "atom_type": "agent_process_start", "params": {"service_name": "myapp", "target_host": "10.0.1.3"}}
  ],
  "edges": [
    {"from": "node_1", "to": "node_2", "label": "success"}
  ]
}

不要使用 stages 嵌套结构，不要使用 node_id 字段（用 id），严格使用 node_1, node_2, node_3... 格式（不是 n1, n2）。
"""


def get_dr_group_topology(dr_group_id: str) -> dict:
    """直接基于 Neo4j 查询 DR 组拓扑信息

    两步 Cypher 查询：
      1. MATCH BELONGS_TO → Process + RUNS_ON → Host
      2. MATCH Process 之间的 CALLS 关系

    Returns:
        {"dr_group": dict, "processes": [dict], "calls": [dict], "hosts": [dict]}
    """
    from cmdb.services.neo4j_client import graph_driver
    from cmdb.services.node_service import NodeService

    try:
        ns = NodeService("DrGroup")
        group_node = ns.retrieve(dr_group_id)
    except Exception as e:
        logger.warning("Failed to retrieve DrGroup %s: %s", dr_group_id, e)
        return {}
    if not group_node:
        return {}

    processes = []
    calls = []
    hosts = {}

    with graph_driver.session() as session:
        cypher = """
            MATCH (g:DrGroup {instance_id: $gid})
            MATCH (g)<-[:BELONGS_TO]-(p:Process)
            OPTIONAL MATCH (p)-[:RUNS_ON]->(h)
            WITH DISTINCT p, h
            RETURN p, h
        """
        try:
            result = session.run(cypher, gid=dr_group_id)
            seen_pids = set()
            for record in result:
                p_node = record.get("p")
                if p_node:
                    pid = p_node.get("instance_id")
                    if pid and pid not in seen_pids:
                        seen_pids.add(pid)
                        processes.append(dict(p_node))
                h_node = record.get("h")
                if h_node:
                    hid = h_node.get("instance_id")
                    if hid and hid not in hosts:
                        hosts[hid] = dict(h_node)
        except Exception as e:
            logger.warning("[DR] BELONGS_TO query failed: %s", e)

        if processes:
            pids = [f"'{p.get('instance_id', '')}'" for p in processes if p.get('instance_id')]
            if pids:
                calls_cypher = f"""
                    MATCH (src)-[:CALLS]->(dst)
                    WHERE src.instance_id IN [{', '.join(pids)}]
                      AND dst.instance_id IN [{', '.join(pids)}]
                    RETURN DISTINCT src.instance_id as src_id, dst.instance_id as dst_id
                """
                try:
                    for record in session.run(calls_cypher):
                        calls.append({"from": record["src_id"], "to": record["dst_id"]})
                except Exception as e:
                    logger.warning("[DR] CALLS query failed: %s", e)

    logger.info("[DR] DrGroup=%s: %d processes, %d calls", dr_group_id, len(processes), len(calls))
    return {"dr_group": group_node, "processes": processes, "calls": calls, "hosts": list(hosts.values())}


def _topo_sort(processes: list, calls: list) -> list:
    """按 CALLS 依赖拓扑排序：先依赖的排前面（启动顺序）

    使用 Kahn 算法：
      - indegree=0 的节点先出列
      - 处理后相邻节点的 indegree-1
    """
    pids = [p.get("instance_id", "") for p in processes if p.get("instance_id")]
    if not calls or not pids:
        return pids

    indegree = {pid: 0 for pid in pids}
    adj = {pid: [] for pid in pids}

    # 只考虑 calls 两端都在本 DR 组内的
    for c in calls:
        src = c.get("from", "")
        dst = c.get("to", "")
        if src in indegree and dst in indegree:
            adj[src].append(dst)
            indegree[dst] += 1

    queue = [pid for pid, d in indegree.items() if d == 0]
    result = []
    while queue:
        pid = queue.pop(0)
        result.append(pid)
        for neighbor in adj.get(pid, []):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    # 有环或孤立节点 → 追加到末尾
    remaining = [pid for pid in pids if pid not in result]
    return result + remaining


def _processes_by_ids(processes: list, pids: list) -> list:
    """按 PID 顺序重建 process 列表"""
    pmap = {p.get("instance_id", ""): p for p in processes}
    return [pmap[pid] for pid in pids if pid in pmap]


def neighbors_to_pipeline(processes: list, calls: list = None) -> dict:
    """将拓扑数据生成为标准 pipeline 格式（支持 CALLS 依赖排序）"""
    nodes = []
    edges = []
    prev_id = None
    idx = 1
    calls = calls or []

    primary = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
               for p in processes if "dr" not in str(p.get("host_instance_id", "")).lower()]
    standby = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
               for p in processes if "dr" in str(p.get("host_instance_id", "")).lower()]

    if not standby:
        standby = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
                   for p in processes]

    # 用 CALLS 拓扑排序决定 stop 顺序（反序停止：先停调用方）
    if calls:
        primary_ids = _topo_sort(
            [{"instance_id": pid} for pid, _, _ in primary],
            calls,
        )
        primary = sorted(primary, key=lambda x: primary_ids.index(x[0]) if x[0] in primary_ids else 999)

        standby_ids = _topo_sort(
            [{"instance_id": pid} for pid, _, _ in standby],
            calls,
        )
        standby = sorted(standby, key=lambda x: standby_ids.index(x[0]) if x[0] in standby_ids else 999)

    # 停止阶段：按依赖反序
    for pid, pname, hid in reversed(primary):
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"关闭 {pname} ({hid})", "node_type": "", "atom_type": "agent_process_stop", "params": {"service_name": pname, "target_host": hid}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    # 启动阶段：按依赖正序
    for pid, pname, hid in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"启动 {pname} ({hid})", "node_type": "", "atom_type": "agent_process_start", "params": {"service_name": pname, "target_host": hid}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    # 验证阶段
    for pid, pname, hid in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"验证 {pname} ({hid})", "node_type": "", "atom_type": "agent_process_status", "params": {"service_name": pname, "target_host": hid}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    return {"nodes": nodes, "edges": edges}


def build_topology_description(topology: dict) -> str:
    """将拓扑数据转为 AI 可读的文本描述"""
    group = topology.get("dr_group", {})
    processes = topology.get("processes", [])
    calls = topology.get("calls", [])

    lines = []
    lines.append(f"DR组: {group.get('name', 'unknown')}")
    lines.append(f"状态: {group.get('status', 'unknown')}")
    lines.append("")

    lines.append("受保护进程:")
    for p in processes:
        pid = p.get("instance_id", "")[:8]
        name = p.get("name", "")
        host = p.get("host_instance_id", "")
        status = p.get("status", "")
        cmd = p.get("command", "")[:60]
        lines.append(f"  - [{pid}] {name} on {host} ({status})")
        lines.append(f"    command: {cmd}")
        addrs = p.get("listen_addresses", "[]")
        if isinstance(addrs, str):
            try:
                addrs = json.loads(addrs)
            except (json.JSONDecodeError, TypeError):
                addrs = []
        for addr in addrs:
            lines.append(f"    listen: {addr.get('ip', '')}:{addr.get('port', '')}")

    lines.append("")
    lines.append("进程调用关系 (CALLS):")
    for c in calls:
        lines.append(f"  {c.get('from', '')[:8]} → {c.get('to', '')[:8]}")

    return "\n".join(lines)
