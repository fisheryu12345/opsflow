"""
Seed DR baseline models: Process model definition + AssociationTypes + Mock data.

Usage:
    python manage.py seed_dr_models              # Seed DR models (idempotent)
    python manage.py seed_dr_models --mock        # Also create mock Neo4j instances
    python manage.py seed_dr_models --force       # Force update existing records

This seeds:
    1. AssociationType: RUNS_ON, CALLS, EXPOSES
    2. ModelDefinition: Process (with all fields)
    3. ModelAssociation: Process→Host, Process→Process
    4. --mock: Creates sample Process instances + CALLS relationships in Neo4j
"""
import json
import logging
import uuid
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)


# ── Association Types ────────────────────────────────────────

ASSOCIATION_TYPES = [
    {
        "asst_id": "RUNS_ON",
        "name": "运行在",
        "src_to_dest_note": "进程运行在主机上",
        "dest_to_src_note": "主机运行进程",
        "direction": "src_to_dest",
    },
    {
        "asst_id": "CALLS",
        "name": "调用",
        "src_to_dest_note": "进程调用另一进程",
        "dest_to_src_note": "被进程调用",
        "direction": "src_to_dest",
    },
    {
        "asst_id": "EXPOSES",
        "name": "暴露",
        "src_to_dest_note": "进程暴露端口提供服务",
        "dest_to_src_note": "服务被进程暴露",
        "direction": "dest_to_src",
    },
    # ── DR Phase 2 ─────────────────────────────────────────
    {
        "asst_id": "FAILOVER_TO",
        "name": "容灾切换",
        "src_to_dest_note": "站点容灾切换到",
        "dest_to_src_note": "被容灾切换",
        "direction": "src_to_dest",
    },
    {
        "asst_id": "BELONGS_TO",
        "name": "属于",
        "src_to_dest_note": "进程属于 DR 组",
        "dest_to_src_note": "DR 组包含进程",
        "direction": "src_to_dest",
    },
    {
        "asst_id": "PROTECTED_BY",
        "name": "被保护",
        "src_to_dest_note": "DR 组保护进程",
        "dest_to_src_note": "进程受 DR 组保护",
        "direction": "src_to_dest",
    },
    {
        "asst_id": "SITE_CONTAINS",
        "name": "站点包含",
        "src_to_dest_note": "站点包含主机",
        "dest_to_src_note": "主机属于站点",
        "direction": "src_to_dest",
    },
]

# ── Process Model Fields ─────────────────────────────────────

PROCESS_FIELDS = [
    # (name, label, field_type, required, default, options, unit)
    ("name", "进程名称", "string", True, "", None, ""),
    ("pid", "进程 PID", "integer", True, 0, None, ""),
    ("user", "运行用户", "string", True, "", None, ""),
    ("status", "进程状态", "enum", True, "running", ["running", "stopped", "zombie"], ""),
    ("command", "启动命令", "string", False, "", None, ""),
    ("listen_addresses", "监听地址", "json", False, [], None, ""),
    ("remote_connections", "远程连接", "json", False, [], None, ""),
    ("cpu_percent", "CPU 使用率", "float", False, 0.0, None, "%"),
    ("memory_mb", "内存占用(MB)", "integer", False, 0, None, "MB"),
    ("host_instance_id", "所属主机 ID", "string", False, "", None, ""),
]

# ── Mock Data ────────────────────────────────────────────────

# ── DR Phase 2: DrSite Model Fields ──────────────────────────

DRSITE_FIELDS = [
    ("name", "站点名称", "string", True, "", None, ""),
    ("site_type", "站点类型", "enum", True, "primary", ["primary", "standby", "dr"], ""),
    ("region", "地域", "string", False, "", None, ""),
    ("status", "站点状态", "enum", True, "normal", ["normal", "warning", "down"], ""),
    ("description", "描述", "string", False, "", None, ""),
    ("priority", "切换优先级", "integer", True, 1, None, ""),
]

# ── DR Phase 2: DrGroup Model Fields ─────────────────────────

DRGROUP_FIELDS = [
    ("name", "DR 组名称", "string", True, "", None, ""),
    ("description", "描述", "string", False, "", None, ""),
    ("status", "DR 组状态", "enum", True, "active",
     ["active", "failed_over", "recovering", "disconnected"], ""),
]

# ── DR Phase 2: Mock DrSite/DrGroup Data ─────────────────────

MOCK_DRSITES = [
    {"name": "主站-北京", "site_type": "primary", "region": "北京", "status": "normal", "priority": 1,
     "host_ids": ["host-web-01", "host-web-02", "host-app-01", "host-app-02",
                   "host-db-01", "host-db-02", "host-cache-01", "host-mq-01", "host-monitor-01"]},
    {"name": "灾备站-上海", "site_type": "standby", "region": "上海", "status": "normal", "priority": 2,
     "host_ids": ["host-dr-web-01", "host-dr-app-01", "host-dr-db-01", "host-dr-mq-01"]},
]

MOCK_DRGROUPS = [
    {"name": "核心交易链路", "description": "核心交易链路：nginx → order-service → mysql/redis/rabbitmq", "status": "active"},
    {"name": "支付服务链路", "description": "支付服务链路：nginx → payment-service → mysql", "status": "active"},
]

MOCK_FAILOVER = [
    ("主站-北京", "灾备站-上海"),
]

MOCK_DRGROUP_PROCESSES = [
    # 核心交易链路: nginx(web-01) → order-service(app-01) → mysqld/redis/rabbitmq
    ("核心交易链路", "order-service"),
    ("核心交易链路", "mysqld"),
    ("核心交易链路", "redis-server"),
    ("核心交易链路", "rabbitmq-server"),
    # 支付服务链路: nginx(web-02) → payment-service(app-02) → mysqld
    ("支付服务链路", "payment-service"),
    ("支付服务链路", "mysqld"),
]

# ── Mock Hosts ────────────────────────────────────────────────

MOCK_HOSTS = [
    {"instance_id": "host-web-01", "name": "Web服务器-01", "ip": "192.168.1.10", "region": "北京"},
    {"instance_id": "host-web-02", "name": "Web服务器-02", "ip": "192.168.1.11", "region": "北京"},
    {"instance_id": "host-app-01", "name": "应用服务器-01(订单)", "ip": "192.168.1.20", "region": "北京"},
    {"instance_id": "host-app-02", "name": "应用服务器-02(支付)", "ip": "192.168.1.21", "region": "北京"},
    {"instance_id": "host-db-01", "name": "数据库主库(交易)", "ip": "192.168.1.30", "region": "北京"},
    {"instance_id": "host-db-02", "name": "数据库从库(报表)", "ip": "192.168.1.31", "region": "北京"},
    {"instance_id": "host-cache-01", "name": "缓存服务器", "ip": "192.168.1.40", "region": "北京"},
    {"instance_id": "host-mq-01", "name": "消息队列", "ip": "192.168.1.50", "region": "北京"},
    {"instance_id": "host-monitor-01", "name": "监控服务器", "ip": "192.168.1.60", "region": "北京"},
    {"instance_id": "host-dr-web-01", "name": "灾备-Web-01", "ip": "192.168.2.10", "region": "上海"},
    {"instance_id": "host-dr-app-01", "name": "灾备-应用-01", "ip": "192.168.2.20", "region": "上海"},
    {"instance_id": "host-dr-db-01", "name": "灾备-数据库", "ip": "192.168.2.30", "region": "上海"},
    {"instance_id": "host-dr-mq-01", "name": "灾备-消息队列", "ip": "192.168.2.50", "region": "上海"},
]

MOCK_PROCESSES = [
    # ── 核心业务：订单服务 ──
    {"name": "nginx", "pid": 1001, "user": "www-data", "status": "running",
     "command": "/usr/sbin/nginx -c /etc/nginx/nginx.conf",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 80, "protocol": "tcp"},
                          {"ip": "0.0.0.0", "port": 443, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.1.20", "remote_port": 8080, "protocol": "tcp", "local_port": 54321},
                            {"remote_ip": "192.168.1.30", "remote_port": 3306, "protocol": "tcp", "local_port": 54322}],
     "cpu_percent": 2.5, "memory_mb": 64, "host_id": "host-web-01"},
    {"name": "nginx", "pid": 2001, "user": "www-data", "status": "running",
     "command": "/usr/sbin/nginx -c /etc/nginx/nginx.conf",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 80, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.1.21", "remote_port": 8080, "protocol": "tcp", "local_port": 54323}],
     "cpu_percent": 1.8, "memory_mb": 56, "host_id": "host-web-02"},
    {"name": "order-service", "pid": 3001, "user": "appuser", "status": "running",
     "command": "/usr/lib/jvm/java-11/bin/java -jar /opt/app/order-service.jar --port=8080",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 8080, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.1.30", "remote_port": 3306, "protocol": "tcp", "local_port": 54330},
                            {"remote_ip": "192.168.1.40", "remote_port": 6379, "protocol": "tcp", "local_port": 54331},
                            {"remote_ip": "192.168.1.50", "remote_port": 5672, "protocol": "tcp", "local_port": 54332}],
     "cpu_percent": 45.2, "memory_mb": 1024, "host_id": "host-app-01"},
    {"name": "payment-service", "pid": 4001, "user": "appuser", "status": "running",
     "command": "/usr/lib/jvm/java-11/bin/java -jar /opt/app/payment-service.jar --port=8081",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 8081, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.1.30", "remote_port": 3306, "protocol": "tcp", "local_port": 54333}],
     "cpu_percent": 32.1, "memory_mb": 768, "host_id": "host-app-02"},

    # ── 数据层 ──
    {"name": "mysqld", "pid": 5001, "user": "mysql", "status": "running",
     "command": "/usr/sbin/mysqld --basedir=/usr --datadir=/var/lib/mysql --port=3306",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 3306, "protocol": "tcp"},
                          {"ip": "0.0.0.0", "port": 3307, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 12.3, "memory_mb": 2048, "host_id": "host-db-01"},
    {"name": "mysqld", "pid": 6001, "user": "mysql", "status": "running",
     "command": "/usr/sbin/mysqld --basedir=/usr --datadir=/var/lib/mysql-slave --port=3306",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 3306, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 5.1, "memory_mb": 1024, "host_id": "host-db-02"},

    # ── 中间件层 ──
    {"name": "redis-server", "pid": 7001, "user": "redis", "status": "running",
     "command": "/usr/bin/redis-server 0.0.0.0:6379",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 6379, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 3.2, "memory_mb": 256, "host_id": "host-cache-01"},

    {"name": "rabbitmq-server", "pid": 8001, "user": "rabbitmq", "status": "running",
     "command": "/usr/sbin/rabbitmq-server",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 5672, "protocol": "tcp"},
                          {"ip": "0.0.0.0", "port": 15672, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 6.7, "memory_mb": 512, "host_id": "host-mq-01"},

    {"name": "prometheus", "pid": 9001, "user": "monitor", "status": "running",
     "command": "/usr/local/bin/prometheus --config.file=/etc/prometheus/prometheus.yml",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 9090, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 8.3, "memory_mb": 2048, "host_id": "host-monitor-01"},

    # ── 备站 (上海) — 停止状态（保持 listen_addresses 以便 CALLS 发现）──
    {"name": "nginx", "pid": 0, "user": "www-data", "status": "stopped",
     "command": "/usr/sbin/nginx -c /etc/nginx/nginx.conf",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 80, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.2.20", "remote_port": 8080, "protocol": "tcp", "local_port": 54321}],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-web-01"},
    {"name": "order-service", "pid": 0, "user": "appuser", "status": "stopped",
     "command": "/usr/lib/jvm/java-11/bin/java -jar /opt/app/order-service.jar --port=8080",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 8080, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.2.30", "remote_port": 3306, "protocol": "tcp", "local_port": 54330},
                            {"remote_ip": "192.168.2.30", "remote_port": 6379, "protocol": "tcp", "local_port": 54331},
                            {"remote_ip": "192.168.2.50", "remote_port": 5672, "protocol": "tcp", "local_port": 54332}],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-app-01"},
    {"name": "payment-service", "pid": 0, "user": "appuser", "status": "stopped",
     "command": "/usr/lib/jvm/java-11/bin/java -jar /opt/app/payment-service.jar --port=8081",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 8081, "protocol": "tcp"}],
     "remote_connections": [{"remote_ip": "192.168.2.30", "remote_port": 3306, "protocol": "tcp", "local_port": 54333}],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-app-01"},
    {"name": "mysqld", "pid": 0, "user": "mysql", "status": "stopped",
     "command": "/usr/sbin/mysqld --basedir=/usr --datadir=/var/lib/mysql --port=3306",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 3306, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-db-01"},
    {"name": "redis-server", "pid": 0, "user": "redis", "status": "stopped",
     "command": "/usr/bin/redis-server 0.0.0.0:6379",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 6379, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-db-01"},
    {"name": "rabbitmq-server", "pid": 0, "user": "rabbitmq", "status": "stopped",
     "command": "/usr/sbin/rabbitmq-server",
     "listen_addresses": [{"ip": "0.0.0.0", "port": 5672, "protocol": "tcp"}],
     "remote_connections": [],
     "cpu_percent": 0, "memory_mb": 0, "host_id": "host-dr-mq-01"},
]


class Command(BaseCommand):
    help = "Seed DR baseline: Process model + AssociationTypes + optional mock data"

    def add_arguments(self, parser):
        parser.add_argument("--mock", action="store_true", help="Also create mock Neo4j instances")
        parser.add_argument("--force", action="store_true", help="Force update existing records")

    def handle(self, *args, **options):
        self._seed_association_types(options)
        self._seed_process_model(options)
        self._seed_model_associations(options)
        self._seed_drsite_model(options)
        self._seed_drgroup_model(options)

        if options.get("mock"):
            self.stdout.write("  Cleaning old mock data...")
            self._clean_mock_neo4j()
            self._seed_mock_neo4j(options)
            self._seed_mock_drsites(options)
            self._seed_mock_drgroups(options)

        self.stdout.write(self.style.SUCCESS("DR baseline seeding complete."))

    def _seed_association_types(self, options):
        """创建关联类型：RUNS_ON, CALLS, EXPOSES"""
        from cmdb.models.association import AssociationType
        count = 0
        for at in ASSOCIATION_TYPES:
            obj, created = AssociationType.objects.get_or_create(
                asst_id=at["asst_id"],
                defaults={
                    "name": at["name"],
                    "src_to_dest_note": at["src_to_dest_note"],
                    "dest_to_src_note": at["dest_to_src_note"],
                    "direction": at["direction"],
                },
            )
            if created:
                count += 1
            elif options.get("force"):
                for k, v in at.items():
                    if k != "asst_id":
                        setattr(obj, k, v)
                obj.save()
        self.stdout.write(f"  + AssociationTypes: {count} created, {len(ASSOCIATION_TYPES)} total")

    def _seed_process_model(self, options):
        """创建 Process 模型定义及字段"""
        from cmdb.models import Classification, ModelDefinition, ModelField

        # 获取或创建分类
        cls_obj, _ = Classification.objects.get_or_create(
            cls_id="bk_host_manage",
            defaults={"name": "主机管理", "description": "主机和进程管理"},
        )

        # 创建 Process 模型定义
        md, created = ModelDefinition.objects.get_or_create(
            code="Process",
            defaults={
                "name": "进程",
                "classification": cls_obj,
                "description": "操作系统进程 — 通过 ProcessManager 自动发现和上报",
                "is_builtin": False,
                "source": "custom",
            },
        )
        if not created and options.get("force"):
            md.name = "进程"
            md.description = "操作系统进程 — 通过 ProcessManager 自动发现和上报"
            md.classification = cls_obj
            md.save()

        self.stdout.write(f"  + ModelDefinition 'Process': {'created' if created else 'already exists'}")

        # 创建字段
        f_count = 0
        for name, label, ftype, required, default, enum_opts, unit in PROCESS_FIELDS:
            defaults = {
                "label": label,
                "field_type": ftype,
                "required": required,
                "default_value": default if default != "" else None,
                "options": enum_opts,
                "unit": unit,
            }
            obj, created = ModelField.objects.get_or_create(
                model_definition=md,
                name=name,
                defaults=defaults,
            )
            if created:
                f_count += 1
            elif options.get("force"):
                for k, v in defaults.items():
                    setattr(obj, k, v)
                obj.save()
        self.stdout.write(f"  + ModelFields: {f_count} created, {len(PROCESS_FIELDS)} total")

    def _seed_model_associations(self, options):
        """创建模型关联：Process→Host(RUNS_ON), Process→Process(CALLS/EXPOSES)"""
        from cmdb.models import ModelDefinition, AssociationType, ModelAssociation

        process_md = ModelDefinition.objects.filter(code="Process").first()
        host_md = ModelDefinition.objects.filter(code="Host").first()

        if not process_md:
            self.stdout.write(self.style.WARNING("  ! Process model not found, skip associations"))
            return

        associations = [
            (process_md, host_md, "RUNS_ON", "n:1", "none"),
            (process_md, process_md, "CALLS", "n:n", "none"),
            (process_md, process_md, "EXPOSES", "n:n", "none"),
        ]

        count = 0
        for src, dst, asst_id, mapping, on_delete in associations:
            at = AssociationType.objects.filter(asst_id=asst_id).first()
            if not at:
                self.stdout.write(self.style.WARNING(f"  ! AssociationType '{asst_id}' not found"))
                continue
            if not dst:
                self.stdout.write(self.style.WARNING(f"  ! Destination model not found for {asst_id}"))
                continue

            _, created = ModelAssociation.objects.get_or_create(
                source_model=src,
                target_model=dst,
                association_type=at,
                defaults={"mapping": mapping, "on_delete": on_delete, "is_pre": True},
            )
            if created:
                count += 1
        self.stdout.write(f"  + ModelAssociations: {count} created")

    def _seed_drsite_model(self, options):
        """创建 DrSite 模型定义及字段"""
        from cmdb.models import Classification, ModelDefinition, ModelField

        cls_obj, _ = Classification.objects.get_or_create(
            cls_id="bk_uncategorized",
            defaults={"name": "未分类", "description": "未分类"},
        )
        md, created = ModelDefinition.objects.get_or_create(
            code="DrSite",
            defaults={
                "name": "DR 站点",
                "classification": cls_obj,
                "description": "灾备站点 — DR 切换的基本单元",
                "is_builtin": False,
                "source": "custom",
            },
        )
        self.stdout.write(f"  + ModelDefinition 'DrSite': {'created' if created else 'already exists'}")

        f_count = 0
        for name, label, ftype, required, default, enum_opts, unit in DRSITE_FIELDS:
            obj, created = ModelField.objects.get_or_create(
                model_definition=md, name=name,
                defaults={"label": label, "field_type": ftype, "required": required,
                          "default_value": default if default != "" else None,
                          "options": enum_opts, "unit": unit},
            )
            if created:
                f_count += 1
        self.stdout.write(f"  + DrSite Fields: {f_count}")

    def _seed_drgroup_model(self, options):
        """创建 DrGroup 模型定义及字段"""
        from cmdb.models import Classification, ModelDefinition, ModelField

        cls_obj, _ = Classification.objects.get_or_create(
            cls_id="bk_uncategorized",
            defaults={"name": "未分类"},
        )
        md, created = ModelDefinition.objects.get_or_create(
            code="DrGroup",
            defaults={
                "name": "DR 组",
                "classification": cls_obj,
                "description": "灾备保护组 — DR 切换的最小逻辑单元",
                "is_builtin": False,
                "source": "custom",
            },
        )
        self.stdout.write(f"  + ModelDefinition 'DrGroup': {'created' if created else 'already exists'}")

        f_count = 0
        for name, label, ftype, required, default, enum_opts, unit in DRGROUP_FIELDS:
            obj, created = ModelField.objects.get_or_create(
                model_definition=md, name=name,
                defaults={"label": label, "field_type": ftype, "required": required,
                          "default_value": default if default != "" else None,
                          "options": enum_opts, "unit": unit},
            )
            if created:
                f_count += 1
        self.stdout.write(f"  + DrGroup Fields: {f_count}")

    def _clean_mock_neo4j(self):
        """清理旧的 Mock 数据"""
        from cmdb.services.neo4j_client import graph_driver
        mock_host_ids = [h["instance_id"] for h in MOCK_HOSTS]
        host_filter = " OR ".join(f"n.host_instance_id = '{hid}'" for hid in mock_host_ids)
        with graph_driver.session() as session:
            session.run("MATCH (n:DrGroup) DETACH DELETE n")
            session.run("MATCH (n:DrSite) DETACH DELETE n")
            if host_filter:
                session.run(f"MATCH (n:Process) WHERE {host_filter} DETACH DELETE n")
        self.stdout.write("    Cleaned old mock data: DrGroup, DrSite, Process")

    def _seed_mock_neo4j(self, options):
        """创建 Mock 进程实例到 Neo4j + 建立 CALLS 关系"""
        self.stdout.write("  Creating mock Neo4j data...")

        from cmdb.services.neo4j_client import graph_driver
        from uuid import uuid4

        # 确保 Host 节点存在
        host_count = 0
        with graph_driver.session() as session:
            for h in MOCK_HOSTS:
                try:
                    session.run(
                        "MERGE (h:Host {instance_id: $hid}) "
                        "ON CREATE SET h.name = $name, h.ip = $ip, "
                        "  h.region = $reg, h.__model_code = 'Host', "
                        "  h.__created_at = toString(datetime()) "
                        "ON MATCH SET h.__model_code = 'Host'",
                        hid=h["instance_id"], name=h["name"], ip=h["ip"], reg=h.get("region", ""),
                    )
                    host_count += 1
                except Exception:
                    pass
        if host_count:
            self.stdout.write(f"  + Hosts: {host_count}")

        created_ids = {}

        for proc in MOCK_PROCESSES:
            new_id = str(uuid4())
            key = proc["name"] + "@" + proc["host_id"]
            addrs = json.dumps(proc["listen_addresses"], ensure_ascii=False)
            conns = json.dumps(proc["remote_connections"], ensure_ascii=False)

            with graph_driver.session() as session:
                try:
                    result = session.run(
                        "MERGE (p:Process {name: $name, host_instance_id: $hid}) "
                        "ON CREATE SET "
                        "  p.instance_id = $iid, p.__model_code = 'Process', "
                        "  p.__created_at = toString(datetime()), p.pid = $pid, "
                        "  p.user = $user, p.status = $status, p.command = $cmd, "
                        "  p.listen_addresses = $addrs, p.remote_connections = $conns, "
                        "  p.cpu_percent = $cpu, p.memory_mb = $mem "
                        "ON MATCH SET "
                        "  p.__model_code = 'Process', p.pid = $pid, p.status = $status, p.cpu_percent = $cpu, "
                        "  p.memory_mb = $mem, p.listen_addresses = $addrs, "
                        "  p.remote_connections = $conns, p.command = $cmd "
                        "RETURN p.instance_id as iid",
                        name=proc["name"], hid=proc["host_id"], iid=new_id,
                        pid=proc["pid"], user=proc["user"], status=proc["status"],
                        cmd=proc["command"], addrs=addrs, conns=conns,
                        cpu=proc["cpu_percent"], mem=proc["memory_mb"],
                    )
                    row = result.single()
                    if row:
                        created_ids[key] = row["iid"]
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"    Skip {key}: {e}"))

        self.stdout.write(f"  + Mock Processes: {len(created_ids)} instances")

        # 建立 RUNS_ON 关系（Process → Host，MERGE 幂等）
        runs_count = 0
        with graph_driver.session() as session:
            for proc in MOCK_PROCESSES:
                src_key = proc["name"] + "@" + proc["host_id"]
                src_id = created_ids.get(src_key)
                if not src_id:
                    continue
                try:
                    session.run(
                        "MERGE (h:Host {instance_id: $hid}) "
                        "ON CREATE SET h.__model_code = 'Host', "
                        "  h.name = $hid, h.ip = '0.0.0.0' "
                        "ON MATCH SET h.__model_code = 'Host' "
                        "WITH h "
                        "MATCH (p {instance_id: $pid}) "
                        "MERGE (p)-[:RUNS_ON]->(h)",
                        pid=src_id, hid=proc["host_id"],
                    )
                    runs_count += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"    RUNS_ON failed {proc['name']}@{proc['host_id']}: {e}"))
        self.stdout.write(f"  + RUNS_ON relations: {runs_count}")

        # 建立 CALLS 关系（MERGE 幂等）
        calls_created = 0
        with graph_driver.session() as session:
            for proc in MOCK_PROCESSES:
                src_key = proc["name"] + "@" + proc["host_id"]
                src_id = created_ids.get(src_key)
                if not src_id:
                    continue
                src_is_dr = "dr-" in proc["host_id"]
                for conn in proc.get("remote_connections", []):
                    for other in MOCK_PROCESSES:
                        dst_is_dr = "dr-" in other["host_id"]
                        if src_is_dr != dst_is_dr:
                            continue
                        for addr in other.get("listen_addresses", []):
                            if (addr["ip"] in ("0.0.0.0", conn["remote_ip"]) and
                                    addr["port"] == conn["remote_port"]):
                                dst_key = other["name"] + "@" + other["host_id"]
                                dst_id = created_ids.get(dst_key)
                                if dst_id and src_id != dst_id:
                                    try:
                                        session.run(
                                            "MATCH (src {instance_id: $sid}) "
                                            "MATCH (dst {instance_id: $did}) "
                                            "MERGE (src)-[:CALLS]->(dst)",
                                            sid=src_id, did=dst_id,
                                        )
                                        calls_created += 1
                                        self.stdout.write(f"    CALLS: {src_key} → {dst_key}")
                                    except Exception:
                                        pass
                                break

        self.stdout.write(f"  + CALLS relations: {calls_created}")

    def _seed_mock_drsites(self, options):
        """创建 Mock DrSite 实例到 Neo4j + SITE_CONTAINS + FAILOVER_TO"""
        self.stdout.write("  Creating mock DrSite data...")
        from cmdb.services.neo4j_client import graph_driver
        from cmdb.services.association_service import AssociationService
        from uuid import uuid4

        asst = AssociationService()
        site_ids = {}

        for site in MOCK_DRSITES:
            new_id = str(uuid4())
            with graph_driver.session() as session:
                result = session.run(
                    "MERGE (s:DrSite {name: $name}) "
                    "ON CREATE SET s.instance_id = $iid, s.__model_code = 'DrSite', "
                    "  s.__created_at = toString(datetime()), s.site_type = $stype, "
                    "  s.region = $region, s.status = $status, s.priority = $pri, "
                    "  s.description = $desc "
                    "ON MATCH SET s.__model_code = 'DrSite', s.status = $status "
                    "RETURN s.instance_id as iid",
                    name=site["name"], iid=new_id, stype=site["site_type"],
                    region=site["region"], status=site["status"],
                    pri=site["priority"], desc=f"{site['site_type']}站点 - {site['region']}",
                )
                row = result.single()
                if row:
                    sid = row["iid"]
                    site_ids[site["name"]] = sid
                    self.stdout.write(f"    DrSite: {site['name']} → {sid[:8]}...")

                    # SITE_CONTAINS → Host
                    for hid in site.get("host_ids", []):
                        try:
                            session.run(
                                "MERGE (h:Host {instance_id: $hid}) "
                                "ON CREATE SET h.__model_code = 'Host', h.name = $hid "
                                "WITH h "
                                "MATCH (s:DrSite {instance_id: $sid}) "
                                "MERGE (s)-[:SITE_CONTAINS]->(h)",
                                sid=sid, hid=hid,
                            )
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"    SITE_CONTAINS failed {sid[:8]}→{hid}: {e}"))

        # FAILOVER_TO 关系（先删后建）
        with graph_driver.session() as session:
            for src_name, dst_name in MOCK_FAILOVER:
                src_id = site_ids.get(src_name)
                dst_id = site_ids.get(dst_name)
                if src_id and dst_id:
                    try:
                        session.run(
                            "MATCH (src:DrSite {instance_id: $src_id}) "
                            "MATCH (dst:DrSite {instance_id: $dst_id}) "
                            "MERGE (src)-[:FAILOVER_TO]->(dst)",
                            src_id=src_id, dst_id=dst_id,
                        )
                        self.stdout.write(f"    FAILOVER_TO: {src_name} → {dst_name}")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"    FAILOVER_TO failed: {e}"))

        self.stdout.write(f"  + DrSites: {len(site_ids)} created")

    def _seed_mock_drgroups(self, options):
        """创建 Mock DrGroup 实例 + BELONGS_TO"""
        self.stdout.write("  Creating mock DrGroup data...")
        from cmdb.services.neo4j_client import graph_driver
        from cmdb.services.association_service import AssociationService

        asst = AssociationService()
        group_ids = {}

        for grp in MOCK_DRGROUPS:
            from uuid import uuid4
            new_id = str(uuid4())
            with graph_driver.session() as session:
                result = session.run(
                    "MERGE (g:DrGroup {name: $name}) "
                    "ON CREATE SET g.instance_id = $iid, "
                    "  g.__model_code = 'DrGroup', g.__created_at = toString(datetime()), "
                    "  g.description = $desc, g.status = $status "
                    "ON MATCH SET g.__model_code = 'DrGroup', g.status = $status "
                    "RETURN g.instance_id as iid",
                    name=grp["name"], iid=new_id, desc=grp["description"], status=grp["status"],
                )
                row = result.single()
                if row:
                    gid = row["iid"]
                    group_ids[grp["name"]] = gid
                    self.stdout.write(f"    DrGroup: {grp['name']} → {gid[:8]}...")

        # 查询 Process 节点，匹配 BELONGS_TO 和 PROTECTED_BY
        from cmdb.services.node_service import NodeService as NS
        proc_ns = NS("Process")
        try:
            all_procs = proc_ns.list({}, page_size=500).get("items", [])
        except Exception:
            all_procs = []

        name_to_group = {}
        for grp_name, proc_pattern in MOCK_DRGROUP_PROCESSES:
            name_to_group.setdefault(proc_pattern, []).append(grp_name)

        # 使用 Cypher MERGE 创建 BELONGS_TO 关系（幂等，重跑不报错）
        with graph_driver.session() as session:
            for proc in all_procs:
                pname = proc.get("name", "")
                matched_groups = name_to_group.get(pname, [])
                pid = proc.get("instance_id", "")
                if not pid:
                    continue
                for grp_name in matched_groups:
                    gid = group_ids.get(grp_name)
                    if gid:
                        try:
                            session.run(
                                "MATCH (p:Process {instance_id: $pid}) "
                                "MATCH (g:DrGroup {instance_id: $gid}) "
                                "MERGE (p)-[:BELONGS_TO]->(g)",
                                pid=pid, gid=gid,
                            )
                        except Exception:
                            pass

        self.stdout.write(f"  + DrGroups: {len(group_ids)} created, BELONGS_TO relationships created")
