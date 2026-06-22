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

拓扑信息中会包含 CALLS（应用间调用关系）列表，**这是判断启停顺序的核心依据**。

DR Pipeline 的结构必须包含以下步骤：
1. 停止主站进程（agent_process_stop）— 逐个停止主站运行中的进程
2. 启动备站进程（agent_process_start）— 逐个启动备站对应的进程
3. 验证备站健康（process_status）— 验证备站进程是否正常

===== CALLS 依赖顺序规则（严格遵循） =====

拓扑中会给出应用间的 CALLS 关系，例如：
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

- 应用名以 `_cont` 结尾 = DR 备站点（如 `nginx_cont`），否则为主站点
- node id 用 node_1, node_2, node_3... 格式（严格遵循此格式）
- 每个 agent_process_stop 节点的 params: {"service_name": "应用名", "target_host": "主机IP"}
- 每个 agent_process_start 节点的 params: {"service_name": "应用名", "target_host": "主机IP"}
- 用 service_name（应用名）作为目标标识，不使用 instance_id

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
    """基于 Neo4j 查询 DR 组拓扑—Application 级

    两步 Cypher 查询：
      1. MATCH PROTECTED_BY → Application
      2. MATCH Application 之间的 CALLS 关系

    Returns:
        {"dr_group": dict, "applications": [dict], "calls": [dict], "hosts": [dict]}
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

    applications = []
    calls = []
    hosts = {}

    with graph_driver.session() as session:
        try:
            result = session.run(
                """
                MATCH (g:DrGroup {instance_id: $gid})
                MATCH (g)<-[:PROTECTED_BY]-(a:Application)
                OPTIONAL MATCH (a)-[:HAS_PROCESS]->(p:Process)
                OPTIONAL MATCH (p)-[:RUNS_ON]->(h:Host)
                WITH DISTINCT a, p, h
                RETURN a, collect(DISTINCT p) AS processes, collect(DISTINCT h) AS hosts
                """,
                gid=dr_group_id,
            )
            seen_apps = set()
            for record in result:
                a_node = record.get("a")
                if a_node:
                    aid = a_node.get("instance_id")
                    if aid and aid not in seen_apps:
                        seen_apps.add(aid)
                        app_dict = dict(a_node)
                        procs = [dict(p) for p in record.get("processes", []) if p]
                        app_dict['_processes'] = procs
                        if procs:
                            addrs = procs[0].get('listen_addresses', '[]')
                            if isinstance(addrs, str):
                                try:
                                    addrs = json.loads(addrs)
                                except (json.JSONDecodeError, TypeError):
                                    addrs = []
                            app_dict['listen_addrs'] = addrs
                        applications.append(app_dict)
                        for h_node in record.get("hosts", []):
                            if h_node:
                                hid = h_node.get("instance_id")
                                if hid and hid not in hosts:
                                    hosts[hid] = dict(h_node)
        except Exception as e:
            logger.warning("[DR] Application query failed: %s", e)

        app_ids = [f"'{a.get('instance_id', '')}'" for a in applications if a.get('instance_id')]
        if app_ids:
            calls_cypher = f"""
                MATCH (src:Application)-[:CALLS]->(dst:Application)
                WHERE src.instance_id IN [{', '.join(app_ids)}]
                  AND dst.instance_id IN [{', '.join(app_ids)}]
                RETURN DISTINCT src.instance_id as src_id, dst.instance_id as dst_id
            """
            try:
                for record in session.run(calls_cypher):
                    calls.append({"from": record["src_id"], "to": record["dst_id"]})
            except Exception as e:
                logger.warning("[DR] Application CALLS query failed: %s", e)

    logger.info("[DR] DrGroup=%s: %d applications, %d calls", dr_group_id, len(applications), len(calls))
    return {"dr_group": group_node, "applications": applications, "calls": calls, "hosts": list(hosts.values())}


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


def neighbors_to_pipeline(applications: list, calls: list = None) -> dict:
    """将 Application 级拓扑数据生成为标准 pipeline 格式（支持 CALLS 依赖排序）"""
    nodes = []
    edges = []
    prev_id = None
    idx = 1
    calls = calls or []

    # Primary/standby by naming convention: A = PROD, A_cont = DR
    primary = [(a.get("instance_id", ""), a.get("name", ""), a.get("host_ip", ""))
               for a in applications if not str(a.get("name", "")).endswith("_cont")]
    standby = [(a.get("instance_id", ""), a.get("name", ""), a.get("host_ip", ""))
               for a in applications if str(a.get("name", "")).endswith("_cont")]

    if not standby:
        # Fallback: host IP convention
        standby = [(a.get("instance_id", ""), a.get("name", ""), a.get("host_ip", ""))
                   for a in applications if "dr" in str(a.get("host_ip", "")).lower()]

    if not standby:
        standby = [(a.get("instance_id", ""), a.get("name", ""), a.get("host_ip", ""))
                   for a in applications]

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

    # 停止阶段：按依赖正序（先停调用方/上层，再停被依赖方/底层）
    for aid, aname, ahost in primary:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"关闭 {aname} ({ahost})", "node_type": "", "atom_type": "agent_process_stop", "params": {"service_name": aname, "target_host": ahost}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    # 启动阶段：按依赖正序
    for aid, aname, ahost in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"启动 {aname} ({ahost})", "node_type": "", "atom_type": "agent_process_start", "params": {"service_name": aname, "target_host": ahost}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    # 验证阶段
    for aid, aname, ahost in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"验证 {aname} ({ahost})", "node_type": "", "atom_type": "agent_process_status", "params": {"service_name": aname, "target_host": ahost}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    return {"nodes": nodes, "edges": edges}


def build_topology_description(topology: dict) -> str:
    """将拓扑数据转为 AI 可读的文本描述（Application 级）"""
    group = topology.get("dr_group", {})
    applications = topology.get("applications", [])
    calls = topology.get("calls", [])

    lines = []
    lines.append(f"DR组: {group.get('name', 'unknown')}")
    lines.append(f"状态: {group.get('status', 'unknown')}")
    lines.append("")

    lines.append("受保护应用:")
    for a in applications:
        aid = a.get("instance_id", "")[:8]
        name = a.get("name", "")
        host = a.get("host_ip", "")
        status = a.get("status", "")
        cmd = a.get("command", "")[:60]
        lines.append(f"  - [{aid}] {name} on {host} ({status})")
        if cmd:
            lines.append(f"    command: {cmd}")
        addrs = a.get('listen_addrs', [])
        for addr in addrs:
            lines.append(f"    listen: {addr.get('ip', '')}:{addr.get('port', '')}")

    lines.append("")
    lines.append("应用调用关系 (CALLS):")
    for c in calls:
        lines.append(f"  {c.get('from', '')[:8]} → {c.get('to', '')[:8]}")

    return "\n".join(lines)
