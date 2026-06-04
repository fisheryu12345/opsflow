# -*- coding: utf-8 -*-
"""Topology query service for CMDB

拓扑查询 — 图遍历、影响分析、全局搜索
"""

import logging

logger = logging.getLogger(__name__)


def get_biz_topology(biz):
    """获取业务的完整拓扑树"""
    from ..models.node_types import Set, Module, Host, Process

    biz_node = {'id': biz.biz_id, 'label': biz.name, 'type': 'biz', 'attrs': {
        'lifecycle': biz.lifecycle, 'operator': biz.operator, 'description': biz.description,
    }}
    nodes = [biz_node]
    edges = []
    process_ids = set()

    for s in biz.sets.all():
        nodes.append({'id': s.set_id, 'label': s.name, 'type': 'set', 'attrs': {
            'env_type': s.env_type, 'description': s.description,
        }})
        edges.append({'from': biz.biz_id, 'to': s.set_id, 'type': 'contains'})
        for m in s.modules.all():
            nodes.append({'id': m.module_id, 'label': m.name, 'type': 'module', 'attrs': {
                'service_type': m.service_type, 'description': m.description,
            }})
            edges.append({'from': s.set_id, 'to': m.module_id, 'type': 'contains'})
            for h in m.hosts.all():
                nodes.append({
                    'id': h.host_id, 'label': h.hostname or h.ip, 'type': 'host',
                    'attrs': {
                        'ip': h.ip, 'hostname': h.hostname, 'status': h.status,
                        'os_type': h.os_type, 'cpu_cores': h.cpu_cores,
                        'memory_mb': h.memory_mb, 'disk_gb': h.disk_gb,
                        'agent_status': h.agent_status, 'region': h.region,
                    },
                })
                edges.append({'from': m.module_id, 'to': h.host_id, 'type': 'contains'})
                for p in h.processes.all():
                    pid = p.process_id
                    process_ids.add(pid)
                    nodes.append({
                        'id': pid, 'label': f"{p.name}:{p.port}", 'type': 'process',
                        'attrs': {
                            'name': p.name, 'port': p.port, 'protocol': p.protocol,
                            'status': p.status, 'version': p.version,
                        },
                    })
                    edges.append({'from': h.host_id, 'to': pid, 'type': 'runs'})

    # 补充 Process DEPENDS_ON 跨进程依赖关系
    for p in Process.nodes.all():
        if p.process_id in process_ids:
            for dep in p.depends_on.all():
                if dep.process_id in process_ids:
                    edges.append({'from': p.process_id, 'to': dep.process_id, 'type': 'depends_on'})

    return {'nodes': nodes, 'edges': edges}


def get_host_graph(host):
    """获取以主机为中心的关联图"""
    from ..models.node_types import Module

    nodes = []
    edges = []
    seen = set()

    # 主机自身
    host_key = f"host:{host.host_id}"
    nodes.append({
        'id': host_key, 'label': host.hostname or host.ip, 'type': 'host',
        'attrs': {
            'ip': host.ip, 'hostname': host.hostname, 'status': host.status,
            'os_type': host.os_type, 'cpu_cores': host.cpu_cores,
            'memory_mb': host.memory_mb, 'disk_gb': host.disk_gb,
            'agent_status': host.agent_status, 'region': host.region,
        },
    })
    seen.add(host_key)

    # 所属模块
    for m in host.module.all():
        mod_key = f"module:{m.module_id}"
        if mod_key not in seen:
            nodes.append({
                'id': mod_key, 'label': m.name, 'type': 'module',
                'attrs': {
                    'service_type': m.service_type, 'description': m.description,
                },
            })
            seen.add(mod_key)
        edges.append({'from': mod_key, 'to': host_key, 'type': 'belongs_to'})

        # 模块下其他主机
        for other in m.hosts.all():
            if other.host_id != host.host_id:
                other_key = f"host:{other.host_id}"
                if other_key not in seen:
                    nodes.append({
                        'id': other_key, 'label': other.hostname or other.ip, 'type': 'host',
                        'attrs': {
                            'ip': other.ip, 'hostname': other.hostname, 'status': other.status,
                            'os_type': other.os_type, 'cpu_cores': other.cpu_cores,
                            'memory_mb': other.memory_mb, 'disk_gb': other.disk_gb,
                            'agent_status': other.agent_status, 'region': other.region,
                        },
                    })
                    seen.add(other_key)
                edges.append({'from': mod_key, 'to': other_key, 'type': 'contains'})

    # 主机上运行的进程
    for p in host.processes.all():
        proc_key = f"process:{p.process_id}"
        if proc_key not in seen:
            nodes.append({
                'id': proc_key, 'label': f"{p.name}:{p.port}", 'type': 'process',
                'attrs': {
                    'name': p.name, 'port': p.port, 'protocol': p.protocol,
                    'status': p.status, 'version': p.version,
                },
            })
            seen.add(proc_key)
        edges.append({'from': host_key, 'to': proc_key, 'type': 'runs'})

    # 进程 DEPENDS_ON 跨进程依赖
    for p in host.processes.all():
        proc_key = f"process:{p.process_id}"
        for dep in p.depends_on.all():
            dep_key = f"process:{dep.process_id}"
            if dep_key in seen:
                edges.append({'from': proc_key, 'to': dep_key, 'type': 'depends_on'})
            elif dep_key not in seen:
                # Also add the dependency node if not already in graph
                nodes.append({
                    'id': dep_key, 'label': f"{dep.name}:{dep.port}", 'type': 'process',
                    'attrs': {
                        'name': dep.name, 'port': dep.port, 'protocol': dep.protocol,
                        'status': dep.status, 'version': dep.version,
                    },
                })
                seen.add(dep_key)
                edges.append({'from': proc_key, 'to': dep_key, 'type': 'depends_on'})

    return {'nodes': nodes, 'edges': edges}


def get_impact_analysis(node_id: str, node_type: str = 'host') -> dict:
    """影响分析 — 给定节点挂了，哪些上下游受影响"""
    from ..models.node_types import Biz, Set, Module, Host, Process

    impacted = []
    paths = []

    try:
        if node_type == 'host':
            host = Host.nodes.get(host_id=node_id)
            impacted.append({'id': host.host_id, 'label': host.hostname or host.ip, 'type': 'host', 'impact': 'direct'})

            # 受影响的上层: 模块 → 集群 → 业务
            for m in host.module.all():
                impacted.append({'id': m.module_id, 'label': m.name, 'type': 'module', 'impact': 'indirect'})
                paths.append({'from': host.host_id, 'to': m.module_id, 'type': 'belongs_to'})
                for s in m.set_.all():
                    impacted.append({'id': s.set_id, 'label': s.name, 'type': 'set', 'impact': 'indirect'})
                    paths.append({'from': m.module_id, 'to': s.set_id, 'type': 'belongs_to'})
                    for b in s.biz.all():
                        impacted.append({'id': b.biz_id, 'label': b.name, 'type': 'biz', 'impact': 'indirect'})
                        paths.append({'from': s.set_id, 'to': b.biz_id, 'type': 'belongs_to'})

            # 受影响的进程
            for p in host.processes.all():
                impacted.append({'id': p.process_id, 'label': f"{p.name}:{p.port}", 'type': 'process', 'impact': 'direct'})
                paths.append({'from': host.host_id, 'to': p.process_id, 'type': 'runs'})

        elif node_type == 'biz':
            biz = Biz.nodes.get(biz_id=node_id)
            impacted.append({'id': biz.biz_id, 'label': biz.name, 'type': 'biz', 'impact': 'direct'})
            for s in biz.sets.all():
                impacted.append({'id': s.set_id, 'label': s.name, 'type': 'set', 'impact': 'indirect'})
                paths.append({'from': biz.biz_id, 'to': s.set_id, 'type': 'contains'})
                for m in s.modules.all():
                    impacted.append({'id': m.module_id, 'label': m.name, 'type': 'module', 'impact': 'indirect'})
                    paths.append({'from': s.set_id, 'to': m.module_id, 'type': 'contains'})
                    for h in m.hosts.all():
                        impacted.append({'id': h.host_id, 'label': h.hostname or h.ip, 'type': 'host', 'impact': 'indirect'})
                        paths.append({'from': m.module_id, 'to': h.host_id, 'type': 'contains'})
    except Exception as e:
        logger.error(f"影响分析失败: {e}")
        return {'impacted': [], 'paths': [], 'error': str(e)}

    return {'impacted': impacted, 'paths': paths, 'total': len(impacted)}


def search_nodes(query: str) -> list:
    """全局搜索 CMDB 节点"""
    from ..models.node_types import Biz, Set, Module, Host, Process

    results = []
    q = query.lower()

    # 搜索业务
    for biz in Biz.nodes.all():
        if q in biz.name.lower() or q in (biz.description or '').lower():
            results.append({'id': biz.biz_id, 'label': biz.name, 'type': 'biz'})

    # 搜索主机
    for host in Host.nodes.all():
        if q in (host.hostname or '').lower() or q in (host.ip or '') or q in (host.private_ip or ''):
            results.append({'id': host.host_id, 'label': host.hostname or host.ip, 'type': 'host'})

    # 搜索进程
    for proc in Process.nodes.all():
        if q in proc.name.lower():
            results.append({'id': proc.process_id, 'label': f"{proc.name}:{proc.port}", 'type': 'process'})

    # 搜索模块
    for mod in Module.nodes.all():
        if q in mod.name.lower():
            results.append({'id': mod.module_id, 'label': mod.name, 'type': 'module'})

    return results[:50]
