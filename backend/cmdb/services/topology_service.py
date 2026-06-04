# -*- coding: utf-8 -*-
"""Topology query service for CMDB

拓扑查询 — 图遍历、影响分析、全局搜索
"""

import logging

logger = logging.getLogger(__name__)


def get_biz_topology(biz):
    """获取业务的完整拓扑树"""
    from ..models.node_types import Set, Module, Host, Process

    nodes = [{'id': biz.biz_id, 'label': biz.name, 'type': 'biz'}]
    edges = []

    for s in biz.sets.all():
        nodes.append({'id': s.set_id, 'label': s.name, 'type': 'set'})
        edges.append({'from': biz.biz_id, 'to': s.set_id, 'type': 'contains'})
        for m in s.modules.all():
            nodes.append({'id': m.module_id, 'label': m.name, 'type': 'module'})
            edges.append({'from': s.set_id, 'to': m.module_id, 'type': 'contains'})
            for h in m.hosts.all():
                nodes.append({'id': h.host_id, 'label': h.hostname or h.ip, 'type': 'host'})
                edges.append({'from': m.module_id, 'to': h.host_id, 'type': 'contains'})
                for p in h.processes.all():
                    nodes.append({'id': p.process_id, 'label': f"{p.name}:{p.port}", 'type': 'process'})
                    edges.append({'from': h.host_id, 'to': p.process_id, 'type': 'runs'})

    return {'nodes': nodes, 'edges': edges}


def get_host_graph(host):
    """获取以主机为中心的关联图"""
    from ..models.node_types import Module

    nodes = []
    edges = []
    seen = set()

    # 主机自身
    host_key = f"host:{host.host_id}"
    nodes.append({'id': host_key, 'label': host.hostname or host.ip, 'type': 'host'})
    seen.add(host_key)

    # 所属模块
    for m in host.module.all():
        mod_key = f"module:{m.module_id}"
        if mod_key not in seen:
            nodes.append({'id': mod_key, 'label': m.name, 'type': 'module'})
            seen.add(mod_key)
        edges.append({'from': mod_key, 'to': host_key, 'type': 'belongs_to'})

        # 模块下其他主机
        for other in m.hosts.all():
            if other.host_id != host.host_id:
                other_key = f"host:{other.host_id}"
                if other_key not in seen:
                    nodes.append({'id': other_key, 'label': other.hostname or other.ip, 'type': 'host'})
                    seen.add(other_key)
                edges.append({'from': mod_key, 'to': other_key, 'type': 'contains'})

    # 主机上运行的进程
    for p in host.processes.all():
        proc_key = f"process:{p.process_id}"
        if proc_key not in seen:
            nodes.append({'id': proc_key, 'label': f"{p.name}:{p.port}", 'type': 'process'})
            seen.add(proc_key)
        edges.append({'from': host_key, 'to': proc_key, 'type': 'runs'})

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
