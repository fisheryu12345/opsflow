"""
Generate mock Neo4j CMDB topology data (graph nodes + relationships).

Usage:
    python manage.py add_mock_neo4j                  # Create mock graph data
    python manage.py add_mock_neo4j --clear          # Delete all existing nodes first
    python manage.py add_mock_neo4j --scale=small    # small / medium (default) / large

Creates a realistic CMDB topology:
  Biz  ->  Set  ->  Module  ->  Host  ->  Process
  plus cross-process DEPENDS_ON relationships.

Requires Neo4j to be running and neomodel configured (CMDB app).
"""

import logging
import random

from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Scale configuration: (num_biz, sets_per_biz, modules_per_set, hosts_per_module, procs_per_host)
SCALES = {
    "small":  (2, 2, 2, 2, 2),
    "medium": (3, 3, 3, 3, 2),
    "large":  (5, 4, 4, 5, 3),
}

BIZ_NAMES = [
    "电商平台", "支付系统", "内部OA", "大数据平台", "AI训练平台",
    "物联网平台", "视频直播", "在线教育",
]

SET_TEMPLATES = [
    {"name_tpl": "{biz}-生产集群", "env": "生产"},
    {"name_tpl": "{biz}-测试集群", "env": "测试"},
    {"name_tpl": "{biz}-容灾集群", "env": "生产"},
    {"name_tpl": "{biz}-开发集群", "env": "开发"},
    {"name_tpl": "{biz}-灰度集群", "env": "测试"},
]

MODULE_TEMPLATES = [
    {"name_tpl": "{biz}-WEB", "svc": "web"},
    {"name_tpl": "{biz}-API网关", "svc": "lb"},
    {"name_tpl": "{biz}-数据库", "svc": "db"},
    {"name_tpl": "{biz}-缓存", "svc": "cache"},
    {"name_tpl": "{biz}-消息队列", "svc": "mq"},
    {"name_tpl": "{biz}-定时任务", "svc": "other"},
]

# Process definitions: name -> (port, protocol, depends_on)
PROCESS_DEFS = [
    {"name": "nginx",    "port": 80,   "protocol": "http", "deps": []},
    {"name": "app-server", "port": 8080, "protocol": "http", "deps": ["redis", "mysql"]},
    {"name": "mysql",    "port": 3306, "protocol": "tcp",  "deps": []},
    {"name": "redis",    "port": 6379, "protocol": "tcp",  "deps": []},
    {"name": "rabbitmq", "port": 5672, "protocol": "tcp",  "deps": ["mysql"]},
    {"name": "tomcat",   "port": 8000, "protocol": "http", "deps": ["redis", "mysql"]},
    {"name": "prometheus", "port": 9090, "protocol": "http", "deps": []},
    {"name": "grafana",  "port": 3000, "protocol": "http", "deps": ["prometheus"]},
    {"name": "elasticsearch", "port": 9200, "protocol": "http", "deps": []},
    {"name": "kibana",   "port": 5601, "protocol": "http", "deps": ["elasticsearch"]},
    {"name": "zookeeper","port": 2181, "protocol": "tcp",  "deps": []},
    {"name": "kafka",    "port": 9092, "protocol": "tcp",  "deps": ["zookeeper"]},
    {"name": "minio",    "port": 9000, "protocol": "http", "deps": []},
    {"name": "etcd",     "port": 2379, "protocol": "tcp",  "deps": []},
]

OS_TYPES = ["linux", "linux", "linux", "linux", "windows"]
OS_VERSIONS = ["CentOS 7.9", "Ubuntu 22.04", "Debian 11", "AlmaLinux 9", "Rocky 8"]
REGIONS = ["cn-hangzhou", "cn-beijing", "cn-shanghai", "cn-shenzhen", "cn-qingdao"]


class Command(BaseCommand):
    help = "Generate mock Neo4j CMDB topology data (graph nodes + relationships)"

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete all CMDB nodes first')
        parser.add_argument('--scale', type=str, default='medium', choices=['small', 'medium', 'large'],
                            help='Scale of mock data (default: medium)')

    def handle(self, *args, **options):
        self.scale_key = options['scale']
        clear = options.get('clear', False)

        if self.scale_key not in SCALES:
            raise CommandError(f"Invalid scale: {self.scale_key}. Choose from: {', '.join(SCALES.keys())}")

        num_biz, sets_per_biz, mods_per_set, hosts_per_mod, procs_per_host = SCALES[self.scale_key]

        # Ensure neomodel is connected
        try:
            from neomodel import config as neomodel_config
            from django.conf import settings

            protocol = getattr(settings, 'NEO4J_PROTOCOL', 'bolt')
            host = getattr(settings, 'NEO4J_HOST', 'localhost')
            port = getattr(settings, 'NEO4J_PORT', 7687)
            user = getattr(settings, 'NEO4J_USER', 'neo4j')
            password = getattr(settings, 'NEO4J_PASSWORD', 'password')

            neomodel_config.DATABASE_URL = f"{protocol}://{user}:{password}@{host}:{port}"

            from neomodel import db as neomodel_db
            results, _ = neomodel_db.cypher_query("RETURN 1 AS n")
            self.stdout.write(f"  Neo4j connected (scale={self.scale_key})")
        except Exception as e:
            raise CommandError(f"Neo4j connection failed: {e}")

        if clear:
            self._clear_all()

        self.stdout.write("=" * 60)
        self.stdout.write(f"CMDB Mock Data Generator — scale={self.scale_key}")
        self.stdout.write("=" * 60)

        self._create_topology(num_biz, sets_per_biz, mods_per_set, hosts_per_mod, procs_per_host)

        self.stdout.write(self.style.SUCCESS(
            f"\nNeo4j mock data created! "
            f"Biz={num_biz}, Set={num_biz*sets_per_biz}, "
            f"Module={num_biz*sets_per_biz*mods_per_set}, "
            f"Host={num_biz*sets_per_biz*mods_per_set*hosts_per_mod}, "
            f"Process={num_biz*sets_per_biz*mods_per_set*hosts_per_mod*procs_per_host}"
        ))

    # ──────────────────────────────────────────────
    #  Clear
    # ──────────────────────────────────────────────

    def _clear_all(self):
        """Delete all CMDB nodes and relationships."""
        self.stdout.write("\n>>> Clearing existing CMDB nodes ...")
        from neomodel import db as neomodel_db
        # Delete in dependency order (children first) to avoid constraint issues
        neomodel_db.cypher_query("MATCH (n:Process) DETACH DELETE n")
        neomodel_db.cypher_query("MATCH (n:Host) DETACH DELETE n")
        neomodel_db.cypher_query("MATCH (n:Module) DETACH DELETE n")
        neomodel_db.cypher_query("MATCH (n:Set) DETACH DELETE n")
        neomodel_db.cypher_query("MATCH (n:Biz) DETACH DELETE n")
        self.stdout.write(self.style.SUCCESS("  All CMDB nodes deleted."))

    # ──────────────────────────────────────────────
    #  Topology creation
    # ──────────────────────────────────────────────

    def _create_topology(self, num_biz, sets_per_biz, mods_per_set, hosts_per_mod, procs_per_host):
        from cmdb.models.node_types import Biz, Set, Module, Host, Process

        biz_names = BIZ_NAMES[:num_biz]
        ip_base = 1

        for bi, biz_name in enumerate(biz_names):
            biz = Biz(
                name=biz_name,
                lifecycle="生产" if bi < 3 else random.choice(["生产", "测试", "开发"]),
                operator="admin",
                description=f"{biz_name} — 核心业务系统",
                labels={"tier": "core" if bi < 3 else "normal", "management_ip": f"10.0.{bi}.10"},
            ).save()
            self.stdout.write(f"\n[Biz] {biz_name}")

            for si in range(sets_per_biz):
                st = SET_TEMPLATES[si % len(SET_TEMPLATES)]
                set_name = st["name_tpl"].format(biz=biz_name)
                cluster = Set(
                    name=set_name,
                    env_type=st["env"],
                    description=f"{biz_name} {st['env']}环境集群",
                    labels={"region": REGIONS[si % len(REGIONS)]},
                ).save()
                biz.sets.connect(cluster)
                self.stdout.write(f"  ├─[Set] {set_name}")

                for mi in range(mods_per_set):
                    mt = MODULE_TEMPLATES[mi % len(MODULE_TEMPLATES)]
                    mod_name = mt["name_tpl"].format(biz=biz_name)
                    module = Module(
                        name=mod_name,
                        service_type=mt["svc"],
                        description=f"{biz_name} {mt['svc']} 模块",
                        labels={"language": random.choice(["java", "go", "python", "nodejs"])},
                    ).save()
                    cluster.modules.connect(module)
                    # Also connect biz directly to module for quick lookup
                    try:
                        biz.sets.connect(module)
                    except Exception:
                        pass  # already connected via cluster chain

                    self.stdout.write(f"    ├─[Module] {mod_name}")

                    for hi in range(hosts_per_mod):
                        host_ip = f"10.0.{bi}.{ip_base}"
                        hostname = f"node-{biz_name.lower()}-{mod_name.lower()}-{hi+1}"
                        ip_base += 1

                        host = Host(
                            ip=host_ip,
                            hostname=hostname,
                            os_type=random.choice(OS_TYPES),
                            os_version=random.choice(OS_VERSIONS),
                            cpu_cores=random.choice([4, 8, 16, 32, 64]),
                            memory_mb=random.choice([8192, 16384, 32768, 65536]),
                            disk_gb=random.choice([100, 200, 500, 1000]),
                            status=random.choices(
                                ["normal", "normal", "normal", "alarm", "offline", "maintenance"],
                                weights=[70, 15, 5, 5, 3, 2]
                            )[0],
                            agent_status=random.choices(
                                ["online", "online", "online", "offline", "unknown"],
                                weights=[75, 15, 5, 3, 2]
                            )[0],
                            agent_version=f"2.{random.randint(0,9)}.{random.randint(0,5)}",
                            region=REGIONS[si % len(REGIONS)],
                            private_ip=host_ip,
                            public_ip=f"{random.randint(100,223)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}" if random.random() > 0.5 else "",
                            labels={"monitored": True},
                        ).save()
                        module.hosts.connect(host)
                        self.stdout.write(f"      ├─[Host] {hostname} ({host_ip})")

                        # Create processes on this host
                        procs_for_host = random.sample(PROCESS_DEFS, min(procs_per_host, len(PROCESS_DEFS)))
                        process_nodes = []
                        for pd in procs_for_host:
                            proc = Process(
                                name=pd["name"],
                                port=pd["port"] + random.randint(0, 2),  # slight port variation
                                protocol=pd["protocol"],
                                status=random.choices(
                                    ["running", "running", "running", "stopped", "error"],
                                    weights=[80, 10, 5, 3, 2]
                                )[0],
                                version=f"{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}",
                                pid_file=f"/var/run/{pd['name']}.pid",
                                startup_command=f"systemctl start {pd['name']}",
                                labels={"auto_restart": True},
                            ).save()
                            host.processes.connect(proc)
                            process_nodes.append(proc)
                            self.stdout.write(f"        ├─[Process] {pd['name']}:{pd['port']}")

                        # Add DEPENDS_ON relationships between processes on this host
                        for proc_node in process_nodes:
                            pd = next((p for p in PROCESS_DEFS if p["name"] == proc_node.name), None)
                            if pd and pd["deps"]:
                                for dep_name in pd["deps"]:
                                    dep_node = next((pn for pn in process_nodes if pn.name == dep_name), None)
                                    if dep_node:
                                        try:
                                            proc_node.depends_on.connect(dep_node)
                                        except Exception:
                                            pass

        self.stdout.write("\n>>> Creating cross-service dependency links ...")
        self._add_cross_host_dependencies()

    def _add_cross_host_dependencies(self):
        """Add extra DEPENDS_ON links between processes on different hosts for richer graph."""
        from neomodel import db as neomodel_db
        # Link some app-server processes to redis/mysql on other hosts
        neomodel_db.cypher_query("""
            MATCH (app:Process {name: 'app-server'})
            MATCH (redis:Process {name: 'redis'})
            WHERE app <> redis
            WITH app, redis LIMIT 20
            MERGE (app)-[:DEPENDS_ON]->(redis)
        """)
        neomodel_db.cypher_query("""
            MATCH (app:Process {name: 'app-server'})
            MATCH (mysql:Process {name: 'mysql'})
            WHERE app <> mysql
            WITH app, mysql LIMIT 20
            MERGE (app)-[:DEPENDS_ON]->(mysql)
        """)
        neomodel_db.cypher_query("""
            MATCH (tomcat:Process {name: 'tomcat'})
            MATCH (redis:Process {name: 'redis'})
            WHERE tomcat <> redis
            WITH tomcat, redis LIMIT 15
            MERGE (tomcat)-[:DEPENDS_ON]->(redis)
        """)
        neomodel_db.cypher_query("""
            MATCH (kafka:Process {name: 'kafka'})
            MATCH (zk:Process {name: 'zookeeper'})
            WHERE kafka <> zk
            WITH kafka, zk LIMIT 15
            MERGE (kafka)-[:DEPENDS_ON]->(zk)
        """)
        self.stdout.write(self.style.SUCCESS("  Cross-host dependencies added."))
