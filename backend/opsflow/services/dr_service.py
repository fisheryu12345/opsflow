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

DR Pipeline 的结构必须包含以下步骤：
1. 停止主站进程（process_stop）— 逐个停止主站运行中的进程
2. 启动备站进程（process_start）— 逐个启动备站对应的进程
3. 验证备站健康（process_status）— 验证备站进程是否正常

约束：
- node id 用 node_1, node_2, node_3... 格式（严格遵循此格式）
- 每个 process_stop/start 节点的 params.instance_id 填写正确的 CMDB instance_id
- 按依赖顺序停止（先停上层应用，再停中间件，最后停数据库）
- 按依赖顺序启动（先启数据库，再启中间件，最后启应用）

Pipeline Tree JSON 格式：
{
  "nodes": [
    {"id": "node_1", "label": "Node label", "node_type": "", "atom_type": "process_stop", "params": {"instance_id": "..."}},
    {"id": "node_2", "label": "Node label", "node_type": "", "atom_type": "process_start", "params": {"instance_id": "..."}}
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


def neighbors_to_pipeline(processes: list) -> dict:
    """将拓扑数据生成为标准 pipeline 格式"""
    nodes = []
    edges = []
    prev_id = None
    idx = 1

    primary = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
               for p in processes if "dr" not in str(p.get("host_instance_id", "")).lower()]
    standby = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
               for p in processes if "dr" in str(p.get("host_instance_id", "")).lower()]

    if not standby:
        standby = [(p.get("instance_id", ""), p.get("name", ""), p.get("host_instance_id", ""))
                   for p in processes]

    for pid, pname, hid in primary:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"关闭 {pname} ({hid})", "node_type": "", "atom_type": "process_stop", "params": {"instance_id": pid, "force": False}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    for pid, pname, hid in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"启动 {pname} ({hid})", "node_type": "", "atom_type": "process_start", "params": {"instance_id": pid}})
        if prev_id: edges.append({"from": prev_id, "to": nid, "label": "success"})
        prev_id = nid; idx += 1

    for pid, pname, hid in standby:
        nid = f"n{idx}"
        nodes.append({"id": nid, "label": f"验证 {pname} ({hid})", "node_type": "", "atom_type": "process_status", "params": {"instance_id": pid}})
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
