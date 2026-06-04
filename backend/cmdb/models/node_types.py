# -*- coding: utf-8 -*-
"""Neo4j node definitions for CMDB

使用 neomodel (StructuredNode) 定义 CMDB 核心节点类型。
所有节点存储于 Neo4j 图数据库，关系通过 RelationshipTo/From 定义。
"""

import logging
from neomodel import (
    StructuredNode, StructuredRel,
    StringProperty, IntegerProperty, FloatProperty,
    BooleanProperty, DateTimeProperty, JSONProperty,
    UniqueIdProperty, RelationshipTo, RelationshipFrom,
)

logger = logging.getLogger(__name__)


class Biz(StructuredNode):
    """
    业务 (Business)
    最顶层组织单元，包含多个集群。
    """
    biz_id = UniqueIdProperty()
    name = StringProperty(required=True)
    lifecycle = StringProperty(default='生产', choices={
        '生产': '生产', '测试': '测试', '开发': '开发', '预发': '预发',
    })
    operator = StringProperty()
    description = StringProperty()
    labels = JSONProperty(default={})
    created_at = DateTimeProperty(default_now=True)

    # 关系
    sets = RelationshipTo('Set', 'CONTAINS')

    @property
    def display_name(self):
        return f"{self.name} (业务)"


class Set(StructuredNode):
    """
    集群 (Cluster/Set)
    业务下的集群单元，包含多个模块。
    """
    set_id = UniqueIdProperty()
    name = StringProperty(required=True)
    env_type = StringProperty(default='生产', choices={
        '生产': '生产', '测试': '测试', '开发': '开发',
    })
    description = StringProperty()
    labels = JSONProperty(default={})
    created_at = DateTimeProperty(default_now=True)

    # 关系
    biz = RelationshipFrom('Biz', 'CONTAINS')
    modules = RelationshipTo('Module', 'CONTAINS')

    @property
    def display_name(self):
        return f"{self.name} (集群)"


class Module(StructuredNode):
    """
    模块 (Module)
    集群下的模块单元，如 Web 服务、数据库、缓存。
    """
    module_id = UniqueIdProperty()
    name = StringProperty(required=True)
    service_type = StringProperty(default='web', choices={
        'web': 'Web 服务', 'db': '数据库', 'cache': '缓存',
        'mq': '消息队列', 'lb': '负载均衡', 'other': '其他',
    })
    description = StringProperty()
    labels = JSONProperty(default={})
    created_at = DateTimeProperty(default_now=True)

    # 关系
    set_ = RelationshipFrom('Set', 'CONTAINS')
    hosts = RelationshipTo('Host', 'CONTAINS')

    @property
    def display_name(self):
        return f"{self.name} (模块)"


class Host(StructuredNode):
    """
    主机 (Host)
    物理机、虚拟机或容器实例。
    """
    host_id = UniqueIdProperty()
    ip = StringProperty(required=True)
    hostname = StringProperty()
    os_type = StringProperty(default='linux', choices={
        'linux': 'Linux', 'windows': 'Windows', 'aix': 'AIX',
    })
    os_version = StringProperty()
    cpu_cores = IntegerProperty(default=0)
    memory_mb = IntegerProperty(default=0)
    disk_gb = IntegerProperty(default=0)
    status = StringProperty(default='normal', choices={
        'normal': '正常', 'alarm': '告警', 'offline': '已下线',
        'maintenance': '维护中', 'unknown': '未知',
    })
    agent_status = StringProperty(default='unknown', choices={
        'online': '在线', 'offline': '离线', 'unknown': '未知',
    })
    agent_version = StringProperty()
    cloud_instance_id = StringProperty()
    private_ip = StringProperty()
    public_ip = StringProperty()
    region = StringProperty()
    labels = JSONProperty(default={})
    created_at = DateTimeProperty(default_now=True)

    # 关系
    module = RelationshipFrom('Module', 'CONTAINS')
    processes = RelationshipTo('Process', 'RUNS')

    @property
    def display_name(self):
        return f"{self.hostname or self.ip} (主机)"


class Process(StructuredNode):
    """
    进程 (Process)
    主机上运行的服务进程。
    """
    process_id = UniqueIdProperty()
    name = StringProperty(required=True)
    port = IntegerProperty(default=0)
    protocol = StringProperty(default='tcp', choices={
        'tcp': 'TCP', 'udp': 'UDP', 'http': 'HTTP', 'grpc': 'gRPC',
    })
    status = StringProperty(default='running', choices={
        'running': '运行中', 'stopped': '已停止', 'error': '异常',
    })
    version = StringProperty()
    pid_file = StringProperty()
    startup_command = StringProperty()
    labels = JSONProperty(default={})
    created_at = DateTimeProperty(default_now=True)

    # 关系
    host = RelationshipFrom('Host', 'RUNS')
    depends_on = RelationshipTo('Process', 'DEPENDS_ON')

    @property
    def display_name(self):
        return f"{self.name}:{self.port} (进程)"
