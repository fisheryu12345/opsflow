"""
Seed system reference data: categories, knowledge, sample templates,
CMDB models, monitor plugins, connector definitions, menus, IAM.

Usage:
    python manage.py seed_reference           # Add reference data (idempotent)
    python manage.py seed_reference --force    # Force update existing records

This replaces the following individual commands:
    seed_template_categories, seed_knowledge, seed_sample_template,
    opsflow_migrate_projects, seed_cmdb_models, seed_monitor,
    seed_connector_definitions, add_iam_menu, add_app_menus
"""

import json
import logging

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)
User = get_user_model()

# ════════════════════════════════════════════════════════════
# Phase 1: Template Categories (18 standard IT categories)
# ════════════════════════════════════════════════════════════

TEMPLATE_CATEGORIES = [
    {"code": "server", "name": "服务器管理", "icon": "server", "sort_order": 10},
    {"code": "virtualization", "name": "虚拟化", "icon": "virtualization", "sort_order": 20},
    {"code": "storage", "name": "存储管理", "icon": "storage", "sort_order": 30},
    {"code": "network", "name": "网络管理", "icon": "network", "sort_order": 40},
    {"code": "security", "name": "安全运维", "icon": "security", "sort_order": 50},
    {"code": "database", "name": "数据库运维", "icon": "database", "sort_order": 60},
    {"code": "deploy", "name": "应用发布", "icon": "deploy", "sort_order": 70},
    {"code": "backup", "name": "备份与恢复", "icon": "backup", "sort_order": 80},
    {"code": "monitoring", "name": "监控告警", "icon": "monitoring", "sort_order": 90},
    {"code": "inspection", "name": "巡检与合规", "icon": "inspection", "sort_order": 100},
    {"code": "itsm", "name": "IT服务管理", "icon": "itsm", "sort_order": 110},
    {"code": "automation", "name": "自动化作业", "icon": "automation", "sort_order": 120},
    {"code": "notification", "name": "通知告警", "icon": "notification", "sort_order": 130},
    {"code": "integration", "name": "集成与API", "icon": "integration", "sort_order": 140},
    {"code": "maintenance", "name": "系统维护", "icon": "maintenance", "sort_order": 150},
    {"code": "container", "name": "容器与K8s", "icon": "container", "sort_order": 160},
    {"code": "infrastructure", "name": "基础设施", "icon": "infrastructure", "sort_order": 170},
    {"code": "other", "name": "其他", "icon": "other", "sort_order": 999},
]

# ════════════════════════════════════════════════════════════
# Phase 1: Knowledge Base (IT operations knowledge entries)
# ════════════════════════════════════════════════════════════

KNOWLEDGE_ENTRIES = [
    {"title": "Ansible Playbook Execution Best Practices",
     "content": "1. Always test playbooks with --check mode before production execution\n"
                "2. Use ansible-vault for sensitive data (passwords, API keys)\n"
                "3. Organize roles by function, not by host\n"
                "4. Use tags to control which parts of a playbook run\n"
                "5. Keep playbooks idempotent — running twice should produce the same result",
     "tags": ["ansible", "playbook", "automation", "best-practice"], "source": "doc"},
    {"title": "Common Ansible Failures and Solutions",
     "content": "1. SSH connection timeout → check SSH config, ControlMaster settings\n"
                "2. Privilege escalation failure → check sudoers on target\n"
                "3. Module parameter type mismatch → verify variable types\n"
                "4. Template rendering error → check Jinja2 syntax\n"
                "5. Unreachable host → check inventory DNS resolution",
     "tags": ["ansible", "troubleshooting", "automation"], "source": "doc"},
    {"title": "Linux Disk Management and Troubleshooting",
     "content": "1. Check disk usage: df -h, du -sh */\n2. Check inode usage: df -i\n"
                "3. Identify large files: find / -type f -size +100M -exec ls -lh {} \\;\n"
                "4. LVM operations: lvdisplay, vgdisplay, lvextend\n"
                "5. Filesystem repair: umount + fsck (on unmounted FS)\n"
                "6. XFS repair: xfs_repair (always backup first)",
     "tags": ["linux", "disk", "storage", "troubleshooting"], "source": "doc"},
    {"title": "Linux Network Diagnostics Toolkit",
     "content": "1. Connectivity: ping, tcping, mtr\n2. Port check: ss -tlnp, netstat -tlnp\n"
                "3. DNS resolution: nslookup, dig, host\n4. Packet capture: tcpdump, tshark\n"
                "5. Bandwidth: iperf3, nload\n6. Route tracing: traceroute, tracepath",
     "tags": ["linux", "network", "diagnostics"], "source": "doc"},
    {"title": "Linux Memory and Process Management",
     "content": "1. Memory usage: free -h, cat /proc/meminfo\n"
                "2. Top processes: top, htop, ps aux --sort=-%mem\n"
                "3. OOM killer logs: dmesg | grep -i oom\n"
                "4. Swap usage: swapon --show, vmstat 1 5\n"
                "5. Memory pressure: /proc/pressure/memory\n"
                "6. Tune swappiness: sysctl vm.swappiness=10",
     "tags": ["linux", "memory", "process", "performance"], "source": "doc"},
    {"title": "Docker Container Management",
     "content": "1. List containers: docker ps -a\n2. View logs: docker logs -f <container>\n"
                "3. Execute command: docker exec -it <container> /bin/sh\n"
                "4. Resource limits: --memory, --cpus\n"
                "5. Cleanup: docker system prune -a\n6. Check volumes: docker volume ls",
     "tags": ["docker", "container", "management"], "source": "doc"},
    {"title": "Nginx Web Server Configuration",
     "content": "1. Test config: nginx -t\n2. Reload: nginx -s reload\n"
                "3. Common locations: /etc/nginx/, /var/log/nginx/\n"
                "4. SSL best practices: TLS 1.3, HSTS, strong ciphers\n"
                "5. Rate limiting: limit_req_zone, limit_conn_zone\n"
                "6. Reverse proxy headers: proxy_set_header X-Forwarded-*",
     "tags": ["nginx", "web", "proxy", "configuration"], "source": "doc"},
    {"title": "VMware ESXi Host Management",
     "content": "1. Access root shell: SSH to ESXi host\n2. Check VM list: vim-cmd vmsvc/getallvms\n"
                "3. Resource usage: esxtop, vsish\n4. Storage: vmkfstools, esxcli storage\n"
                "5. Network config: esxcli network\n6. Log files: /var/log/hostd.log, /var/log/vpxa.log",
     "tags": ["vmware", "esxi", "virtualization", "hypervisor"], "source": "doc"},
    {"title": "ServiceNow Integration Guide",
     "content": "1. REST API base: https://<instance>.service-now.com/api/now/\n"
                "2. Table API: /table/incident, /table/change_request\n"
                "3. Authentication: Basic Auth or OAuth 2.0\n"
                "4. Rate limits: 10 requests/second per user\n"
                "5. Attachments: /attachment/file?table_name=<t>&table_sys_id=<s>",
     "tags": ["servicenow", "itsm", "api", "integration"], "source": "doc"},
    {"title": "Redfish API / BMC Management",
     "content": "1. Redfish base URL: https://<bmc-ip>/redfish/v1/\n"
                "2. Systems: /Systems/1\n3. Power control: /Systems/1/Actions/ComputerSystem.Reset\n"
                "4. Sensors: /Chassis/1/Thermal, /Chassis/1/Power\n"
                "5. Firmware: /UpdateService/FirmwareInventory\n"
                "6. Common tools: curl, racadm, ipmitool",
     "tags": ["redfish", "bmc", "ipmi", "hardware", "management"], "source": "doc"},
    {"title": "NetApp ONTAP Storage Operation",
     "content": "1. SSH to storage VM: ssh admin@<cluster-mgmt>\n"
                "2. Volume management: vol create, vol modify, vol show\n"
                "3. Snapshot: snapshot create/delete/restore\n"
                "4. NFS export: exportfs, nfs show\n"
                "5. Performance: statistics show, sysstat\n"
                "6. Aggr management: aggr show, aggr add",
     "tags": ["netapp", "storage", "san", "nas", "ontap"], "source": "doc"},
    {"title": "Dell PowerMax/EMC Storage Management",
     "content": "1. Access via Unisphere for PowerMax\n"
                "2. CLI: symcli, symcfg, symdev, symsg\n"
                "3. Storage groups: create sg, add dev, masking\n"
                "4. SRDF replication: symrdf create, failover, failback\n"
                "5. Performance monitoring: symstat, symsnap\n"
                "6. PowerMax REST API: https://<u4v-host>:8443/univmax/rest/",
     "tags": ["dell", "powermax", "emc", "storage", "san"], "source": "doc"},
    {"title": "REST API Design Best Practices",
     "content": "1. Use nouns for resources: /api/v2/users\n"
                "2. HTTP methods: GET read, POST create, PUT/PATCH update, DELETE delete\n"
                "3. Pagination: ?page=1&limit=20\n4. Error format: {\"code\": 4000, \"msg\": \"...\"}\n"
                "5. Versioning: /api/v1/, /api/v2/\n6. Rate limiting headers: X-RateLimit-*",
     "tags": ["api", "rest", "design", "best-practice"], "source": "doc"},
    {"title": "Server Health Check Checklist",
     "content": "1. CPU: top, uptime, /proc/cpuinfo\n"
                "2. Memory: free -m, /proc/meminfo\n3. Disk: df -h, smartctl -a /dev/sda\n"
                "4. Network: ethtool, ip link, netstat\n5. Logs: /var/log/messages, /var/log/syslog\n"
                "6. NTP: timedatectl, ntpq -p\n7. Services: systemctl list-units --failed\n"
                "8. Security: last, journalctl -u sshd",
     "tags": ["monitoring", "health-check", "server", "best-practice"], "source": "doc"},
    {"title": "MySQL Database Administration",
     "content": "1. Slow query log: SET GLOBAL slow_query_log = ON\n"
                "2. Process list: SHOW FULL PROCESSLIST\n3. Kill query: KILL <thread_id>\n"
                "4. Backup: mysqldump, xtrabackup\n5. Replication: SHOW SLAVE STATUS\n"
                "6. Performance: EXPLAIN, SHOW INDEX, pt-query-digest\n"
                "7. Size: SELECT table_schema, ROUND(SUM(data_length+index_length)) ...",
     "tags": ["mysql", "database", "dba", "administration"], "source": "doc"},
    {"title": "Security Hardening Checklist",
     "content": "1. SSH config: disable root login, key-only auth\n"
                "2. Firewall: iptables/nftables, fail2ban\n3. OS updates: unattended-upgrades\n"
                "4. File integrity: aide, tripwire\n5. Audit: auditd, /var/log/auth.log\n"
                "6. SELinux/AppArmor: enforcing mode\n7. Kernel hardening: sysctl settings\n"
                "8. Password policies: pwquality, faillock",
     "tags": ["security", "hardening", "linux", "compliance"], "source": "doc"},
    {"title": "Service Recovery Runbook Template",
     "content": "1. Detection: what alerts/metrics indicate the issue\n"
                "2. Diagnosis: commands to run to identify root cause\n"
                "3. Escalation: who to notify if unable to resolve in N minutes\n"
                "4. Recovery steps: numbered sequence of recovery actions\n"
                "5. Verification: how to confirm service is healthy\n"
                "6. Post-mortem: log RCA, create follow-up action items",
     "tags": ["runbook", "recovery", "sre", "incident"], "source": "doc"},
]

# ════════════════════════════════════════════════════════════
# Phase 1: Sample Templates (2 published onboarding templates)
# ════════════════════════════════════════════════════════════

SAMPLE_TEMPLATES = [
    {
        "name": "Quick Start - Disk Check",
        "category": "server",
        "description": "A simple disk check template that runs df -h. Perfect for first-time users to experience the full template → execute workflow.",
        "pipeline": {
            "nodes": [
                {"id": "node_1", "label": "Start", "node_type": "start_event"},
                {"id": "node_2", "label": "Disk Check", "atom_type": "shell", "node_type": "",
                 "max_retries": 1, "retry_delay": 30, "timeout_seconds": 60,
                 "params": {"command": "df -h", "timeout": 60}},
                {"id": "node_3", "label": "End", "node_type": "end_event"},
            ],
            "edges": [
                {"from": "node_1", "to": "node_2", "label": "success"},
                {"from": "node_2", "to": "node_3", "label": "success"},
            ],
        },
    },
    {
        "name": "Nginx Health Check and Auto-Restore",
        "category": "web",
        "description": "Monitors Nginx health, auto-restarts on failure, sends alerts. Demonstrates branching with exclusive gateway.",
        "pipeline": {
            "nodes": [
                {"id": "node_1", "label": "Start", "node_type": "start_event"},
                {"id": "node_2", "label": "Health Check Nginx", "atom_type": "shell", "node_type": "",
                 "max_retries": 1, "retry_delay": 30, "timeout_seconds": 30,
                 "params": {"command": "curl -sf http://localhost/nginx-health || exit 1", "timeout": 30}},
                {"id": "node_3", "label": "Healthy?", "node_type": "exclusive_gateway"},
                {"id": "node_4", "label": "Report OK", "atom_type": "send_alert", "node_type": "",
                 "params": {"message": "Nginx health check passed", "level": "info"}},
                {"id": "node_5", "label": "Restart Nginx", "atom_type": "shell", "node_type": "",
                 "params": {"command": "systemctl restart nginx", "timeout": 30}},
                {"id": "node_6", "label": "Send Alert", "atom_type": "send_alert", "node_type": "",
                 "params": {"message": "Nginx was down — restart attempted", "level": "warning"}},
                {"id": "node_7", "label": "Converge", "node_type": "converge_gateway"},
                {"id": "node_8", "label": "End", "node_type": "end_event"},
            ],
            "edges": [
                {"from": "node_1", "to": "node_2", "label": "success"},
                {"from": "node_2", "to": "node_3", "label": "success"},
                {"from": "node_3", "to": "node_4", "label": "success"},
                {"from": "node_3", "to": "node_5", "label": "failure"},
                {"from": "node_4", "to": "node_7", "label": "success"},
                {"from": "node_5", "to": "node_6", "label": "success"},
                {"from": "node_5", "to": "node_7", "label": "failure"},
                {"from": "node_6", "to": "node_7", "label": "success"},
                {"from": "node_7", "to": "node_8", "label": "success"},
            ],
        },
    },
]


class Command(BaseCommand):
    help = "Seed system reference data (categories, knowledge, menus, CMDB, plugins, connectors)"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update existing records')

    def handle(self, *args, **options):
        force = options.get('force', False)
        self.stdout.write("=" * 60)
        self.stdout.write("Seed Reference Data")
        self.stdout.write("=" * 60)

        self._seed_template_categories()
        self._seed_knowledge()
        self._seed_app_menus()
        self._seed_cmdb_models()
        self._seed_monitor_plugins()
        self._seed_connector_definitions()
        self._seed_iam_menu()
        self._migrate_projects()
        self._seed_sample_templates()

        self.stdout.write(self.style.SUCCESS("\nAll reference data seeded successfully!"))

    # ── 1. Template Categories ──

    def _seed_template_categories(self):
        from opsflow.models import TemplateCategory
        created = updated = 0
        for cat in TEMPLATE_CATEGORIES:
            obj, is_new = TemplateCategory.objects.update_or_create(
                code=cat["code"],
                defaults={"name": cat["name"], "icon": cat["icon"],
                          "sort_order": cat["sort_order"], "is_active": True},
            )
            if is_new:
                created += 1
            else:
                updated += 1
        self.stdout.write(f"\n>>> Template Categories: {created} new, {updated} updated")

    # ── 2. Knowledge Base ──

    def _seed_knowledge(self):
        from opsflow.models import OpsKnowledge
        created = skipped = 0
        for entry in KNOWLEDGE_ENTRIES:
            _, is_new = OpsKnowledge.objects.update_or_create(
                title=entry["title"],
                defaults={"content": entry["content"], "tags": entry["tags"], "source": entry["source"]},
            )
            if is_new:
                created += 1
            else:
                skipped += 1
        self.stdout.write(f">>> Knowledge Base: {created} new, {skipped} existing")

    # ── 3. App Menus (match current DB structure) ──

    def _seed_app_menus(self):
        from dvadmin.system.models import Menu

        # Deduplicate: keep the oldest record for each web_path (avoid get_or_create failures)
        seen = {}
        for m in Menu.objects.all().order_by('id'):
            if m.web_path:
                if m.web_path in seen:
                    self.stdout.write(f"  Removing duplicate menu: {m.name} (web_path={m.web_path})")
                    m.delete()
                else:
                    seen[m.web_path] = m.id

        # Use web_path as lookup key to avoid duplicate creation from name encoding differences

        def add_catalog(name, path, icon, sort):
            cat, _ = Menu.objects.get_or_create(
                web_path=path, parent=None,
                defaults={
                    "name": name, "icon": icon, "sort": sort,
                    "visible": True, "is_catalog": True, "status": True,
                },
            )
            return cat

        def add_leaf(name, path, component, cname, icon, sort, parent=None):
            item, created = Menu.objects.update_or_create(
                web_path=path,
                defaults={
                    "name": name, "icon": icon, "sort": sort, "status": True,
                    "component": component, "component_name": cname,
                    "parent": parent, "is_catalog": False, "visible": True,
                },
            )
            if not created:
                # Ensure parent is always synced (especially after catalog rebuild)
                if item.parent_id != (parent.id if parent else None):
                    item.parent = parent
                    item.save(update_fields=['parent_id'])
            return item

        # ── Catalog: 运维平台 (sort=4) → OpsAgent pages ──
        cat = add_catalog("运维平台", "/apps", "iconfont icon-gongju", 4)
        add_leaf("运维控制台", "/opsagent", "apps/opsagent/index", "opsagent", "iconfont icon-dianhua", 10, cat)
        add_leaf("会话历史", "/opsagent/sessions", "apps/opsagent/Sessions", "opsagentSessions", "iconfont icon-LoggedinPC", 11, cat)

        # ── Catalog: OpsFlow (sort=6) → OpsFlow pages ──
        cat = add_catalog("OpsFlow", "/opsflow-catalog", "iconfont icon-diannao1", 6)
        add_leaf("运维管理", "/opsflow_desgner", "apps/opsflow/index", "opsflow", "iconfont icon-wenducanshu-05", 1, cat)
        add_leaf("看板大屏", "/ops_dashboard", "apps/opsflow-dashboard/index", "opsflow-dashboard", "iconfont icon-xianshimima", 2, cat)
        add_leaf("任务执行", "/opsflow-execution", "apps/opsflow-execution/index", "opsflow-execution", "iconfont icon-diqiu", 7, cat)
        add_leaf("项目管理", "/opsflow-project", "apps/opsflow-project/index", "opsflow-project", "iconfont icon-dianhua", 8, cat)
        add_leaf("知识库", "/opsflow-knowledge", "apps/opsflow-knowledge/index", "opsflow-knowledge", "iconfont icon-15tupianyulan", 9, cat)
        add_leaf("模板中心", "/opsflow-template", "apps/opsflow-template/index", "opsflow-template", "iconfont icon-shoujidiannao", 10, cat)

        # ── Catalog: 配置管理 (sort=7) → CMDB page ──
        cat = add_catalog("配置管理", "/cmdb-catalog", "iconfont icon-fuwenbenkuang", 7)
        add_leaf("配置管理", "/cmdb", "apps/cmdb/index", "cmdb", "iconfont icon-shuxingtu", 1, cat)

        # ── Standalone leaf pages (no parent) ──
        add_leaf("门户优化", "/portal", "apps/portal/index", "portal", "iconfont icon-tongzhi2", 8)
        add_leaf("工单系统", "/itsm", "apps/itsm/index", "itsm", "iconfont icon-barcode-qr", 9)
        add_leaf("监控平台", "/monitor", "apps/monitor/index", "monitor", "iconfont icon-zhongduancanshuchaxun", 10)
        add_leaf("集成中心", "/interhub", "apps/integration/index", "integration", "iconfont icon-step", 11)
        add_leaf("作业平台", "/job-platform", "apps/job-platform/index", "job-platform", "iconfont icon-siweidaotu", 12)
        add_leaf("统一接口", "/open-api", "apps/open-api/index", "open-api", "iconfont icon-caozuorizhi", 13)

        self.stdout.write(f">>> App Menus: seeded to match DB structure")

    # ── 4. CMDB Models ──

    def _seed_cmdb_models(self):
        from cmdb.models import Classification, AssociationType, ModelDefinition, ModelField, ModelAssociation, MainlineTopo

        # Classifications
        cls_data = [
            ("bk_biz_topo", "业务拓扑", ""), ("bk_host_manage", "主机管理", ""),
            ("bk_organization", "组织架构", ""), ("bk_network", "网络设备", ""),
            ("bk_uncategorized", "未分类", ""),
        ]
        for cls_id, name, desc in cls_data:
            Classification.objects.get_or_create(cls_id=cls_id, defaults={"name": name, "description": desc})
        self.stdout.write(f"  + Classifications: {len(cls_data)}")

        # Association types
        at_data = [
            ("BELONGS_TO", "属于", "属于", "包含", "dest_to_src"),
            ("CONTAINS", "包含", "包含", "属于", "src_to_dest"),
            ("RUNS", "运行", "运行进程", "运行在", "src_to_dest"),
            ("DEPENDS_ON", "依赖", "依赖", "被依赖", "bidirectional"),
            ("CONNECTS_TO", "连接", "连接到", "连接到", "bidirectional"),
        ]
        for code, name_d, name_s, name_t, direction in at_data:
            AssociationType.objects.get_or_create(
                asst_id=code,
                defaults={"name_dest": name_d, "name_source": name_s, "name_target": name_t, "direction": direction},
            )
        self.stdout.write(f"  + AssociationTypes: {len(at_data)}")

        # Model definitions
        models_def = {
            "Biz": {"name": "业务", "cls_id": "bk_biz_topo",
                    "fields": [("name", "业务名"), ("lifecycle", "生命周期"), ("operator", "负责人"), ("description", "描述")]},
            "Set": {"name": "集群", "cls_id": "bk_biz_topo",
                    "fields": [("name", "集群名"), ("env_type", "环境类型"), ("description", "描述")]},
            "Module": {"name": "模块", "cls_id": "bk_biz_topo",
                       "fields": [("name", "模块名"), ("service_type", "服务类型"), ("description", "描述")]},
            "Host": {"name": "主机", "cls_id": "bk_host_manage",
                     "fields": [("ip", "IP地址"), ("hostname", "主机名"), ("os_type", "操作系统"),
                                ("cpu_cores", "CPU核数"), ("memory_mb", "内存(MB)"), ("disk_gb", "磁盘(GB)"),
                                ("status", "状态"), ("region", "地域")]},
            "Process": {"name": "进程", "cls_id": "bk_host_manage",
                        "fields": [("name", "进程名"), ("port", "端口"), ("protocol", "协议"), ("status", "状态"), ("version", "版本")]},
        }

        md_count = f_count = 0
        for code, mdef in models_def.items():
            cls_obj = Classification.objects.filter(cls_id=mdef["cls_id"]).first()
            md, created = ModelDefinition.objects.get_or_create(code=code, defaults={"name": mdef["name"], "classification": cls_obj})
            if created:
                md_count += 1
            for fname, flabel in mdef["fields"]:
                _, fc = ModelField.objects.get_or_create(model_definition=md, name=fname, defaults={"label": flabel})
                if fc:
                    f_count += 1
        self.stdout.write(f"  + Models: {md_count}, Fields: {f_count}")

        # Associations
        asso_data = [
            ("Biz", "Set", "CONTAINS", "1:n", "delete_target"),
            ("Set", "Module", "CONTAINS", "1:n", "delete_target"),
            ("Module", "Host", "CONTAINS", "1:n", "delete_target"),
            ("Host", "Process", "RUNS", "1:n", "delete_target"),
            ("Process", "Process", "DEPENDS_ON", "n:n", "none"),
        ]
        for src, dst, rel_type, cardinality, on_delete in asso_data:
            src_md = ModelDefinition.objects.filter(code=src).first()
            dst_md = ModelDefinition.objects.filter(code=dst).first()
            assoc_type = AssociationType.objects.filter(asst_id=rel_type).first()
            if src_md and dst_md and assoc_type:
                ModelAssociation.objects.get_or_create(source_model=src_md, target_model=dst_md, defaults={
                    "association_type": assoc_type, "mapping": cardinality, "on_delete": on_delete,
                })

        # Mainline
        ml_data = [("Biz", None, 1), ("Set", "Biz", 2), ("Module", "Set", 3), ("Host", "Module", 4)]
        for code, parent_code, sort_order in ml_data:
            md = ModelDefinition.objects.filter(code=code).first()
            pmd = ModelDefinition.objects.filter(code=parent_code).first() if parent_code else None
            if md:
                MainlineTopo.objects.get_or_create(model_definition=md, defaults={"parent_model": pmd, "sort_order": sort_order})
        self.stdout.write(f"  + CMDB Mainline topology: {len(ml_data)} levels")

    # ── 5. Monitor Plugins ──

    def _seed_monitor_plugins(self):
        from monitor.models import ActionPlugin
        plugins = [
            {"plugin_type": "notice", "plugin_key": "wecom_robot", "name": "企业微信机器人",
             "config_schema": {"webhook_url": {"type": "string"}}},
            {"plugin_type": "notice", "plugin_key": "dingtalk_robot", "name": "钉钉机器人",
             "config_schema": {"access_token": {"type": "string"}}},
            {"plugin_type": "notice", "plugin_key": "email_smtp", "name": "邮件通知",
             "config_schema": {"smtp_server": {"type": "string"}, "smtp_port": {"type": "integer"}}},
            {"plugin_type": "webhook", "plugin_key": "generic_webhook", "name": "通用 Webhook",
             "config_schema": {"url": {"type": "string"}, "method": {"type": "string"}}},
            {"plugin_type": "opsflow", "plugin_key": "opsflow_trigger", "name": "OpsFlow自愈流程",
             "config_schema": {"template_id": {"type": "integer"}}},
            {"plugin_type": "itsm", "plugin_key": "itsm_incident", "name": "ITSM事件工单",
             "config_schema": {"urgency": {"type": "string"}, "impact": {"type": "string"}}},
            {"plugin_type": "awx", "plugin_key": "awx_job", "name": "AWX作业",
             "config_schema": {"job_template_id": {"type": "integer"}, "inventory_id": {"type": "integer"}}},
        ]
        for data in plugins:
            ActionPlugin.objects.update_or_create(plugin_key=data["plugin_key"], defaults=data)
        self.stdout.write(f">>> Monitor Plugins: {len(plugins)} seeded")

    # ── 6. Connector Definitions ──

    def _seed_connector_definitions(self):
        from integration.models.connector import ConnectorDefinition

        # Helper: build config_schema with a simple list of {key, title, type, required, default}
        def _schema(fields: list) -> dict:
            props = {}
            required = []
            for f in fields:
                ftype = f.get("type", "string")
                schema_type = "string"
                if ftype == "int":
                    schema_type = "integer"
                elif ftype == "bool":
                    schema_type = "boolean"
                elif ftype == "select":
                    schema_type = "string"
                props[f["key"]] = {
                    "type": schema_type,
                    "title": f["title"],
                    "default": f.get("default", ""),
                    "description": f.get("desc", ""),
                }
                if f.get("select_options"):
                    props[f["key"]]["enum"] = f["select_options"]
                if f.get("required", False):
                    required.append(f["key"])
            return {"type": "object", "properties": props, "required": required}

        connectors = [
            # ─── Cloud ───
            {"code": "aliyun_ecs", "name": "阿里云 ECS", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "地域", "default": "cn-hangzhou", "required": True},
                 {"key": "endpoint", "title": "Endpoint", "default": "ecs.aliyuncs.com"},
             ])},
            {"code": "tencent_cvm", "name": "腾讯云 CVM", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "地域", "default": "ap-guangzhou", "required": True},
             ])},
            {"code": "huawei_ecs", "name": "华为云 ECS", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "区域", "default": "cn-east-3"},
             ])},
            {"code": "aws_ec2", "name": "AWS EC2", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Region", "default": "us-east-1", "required": True},
             ])},
            {"code": "azure_vm", "name": "Azure VM", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Location", "default": "eastus"},
             ])},
            {"code": "gcp_compute", "name": "GCP Compute Engine", "category": "cloud",
             "config_schema": _schema([
                 {"key": "region", "title": "Region", "default": "us-central1"},
                 {"key": "project_id", "title": "Project ID", "required": True},
             ])},
            # ─── Notification ───
            {"code": "aliyun_sms", "name": "阿里云短信", "category": "notification",
             "config_schema": _schema([
                 {"key": "sign_name", "title": "短信签名", "required": True},
             ])},
            {"code": "wecom_bot", "name": "企业微信 Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook 地址", "required": True},
             ])},
            {"code": "dingtalk_bot", "name": "钉钉 Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook 地址", "required": True},
             ])},
            {"code": "email_smtp", "name": "邮件 (SMTP)", "category": "notification",
             "config_schema": _schema([
                 {"key": "smtp_host", "title": "SMTP 服务器", "required": True},
                 {"key": "smtp_port", "title": "端口", "type": "int", "default": 465},
                 {"key": "from_address", "title": "发件地址", "required": True},
             ])},
            {"code": "slack", "name": "Slack", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook URL", "required": True},
                 {"key": "channel", "title": "默认频道", "default": "#general"},
             ])},
            {"code": "teams", "name": "Microsoft Teams", "category": "notification",
             "config_schema": _schema([
                 {"key": "webhook_url", "title": "Webhook URL", "required": True},
             ])},
            {"code": "telegram_bot", "name": "Telegram Bot", "category": "notification",
             "config_schema": _schema([
                 {"key": "bot_token", "title": "Bot Token", "required": True},
                 {"key": "chat_id", "title": "默认 Chat ID"},
             ])},
            # ─── Auth ───
            {"code": "ldap", "name": "LDAP 认证源", "category": "auth",
             "config_schema": _schema([
                 {"key": "host", "title": "LDAP 服务器", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 389},
                 {"key": "base_dn", "title": "Base DN", "required": True},
             ])},
            {"code": "oauth2_oidc", "name": "OAuth2 / OIDC", "category": "auth",
             "config_schema": _schema([
                 {"key": "issuer_url", "title": "Issuer URL", "required": True},
                 {"key": "authorization_endpoint", "title": "授权端点"},
                 {"key": "token_endpoint", "title": "Token 端点"},
             ])},
            {"code": "saml_idp", "name": "SAML IdP", "category": "auth",
             "config_schema": _schema([
                 {"key": "entity_id", "title": "Entity ID", "required": True},
                 {"key": "sso_url", "title": "SSO URL", "required": True},
             ])},
            # ─── AI ───
            {"code": "openai", "name": "OpenAI", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.openai.com"},
                 {"key": "model", "title": "默认模型", "default": "gpt-4o"},
             ])},
            {"code": "deepseek", "name": "DeepSeek", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.deepseek.com"},
                 {"key": "model", "title": "默认模型", "default": "deepseek-chat"},
             ])},
            {"code": "anthropic", "name": "Anthropic Claude", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://api.anthropic.com"},
                 {"key": "model", "title": "默认模型", "default": "claude-sonnet-4-20250514"},
             ])},
            {"code": "tongyi_qwen", "name": "通义千问 (Qwen)", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://dashscope.aliyuncs.com"},
                 {"key": "model", "title": "默认模型", "default": "qwen-plus"},
             ])},
            {"code": "local_llm", "name": "本地 LLM (OpenAI 兼容)", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "http://localhost:8000/v1", "required": True},
                 {"key": "model", "title": "默认模型", "default": "local-model"},
             ])},
            {"code": "gemini", "name": "Google Gemini", "category": "ai",
             "config_schema": _schema([
                 {"key": "api_base_url", "title": "API Base URL", "default": "https://generativelanguage.googleapis.com"},
                 {"key": "model", "title": "默认模型", "default": "gemini-2.0-flash"},
             ])},
            # ─── Automation ───
            {"code": "ansible", "name": "Ansible", "category": "automation",
             "config_schema": _schema([
                 {"key": "host", "title": "控制节点地址"},
                 {"key": "port", "title": "SSH 端口", "type": "int", "default": 22},
             ])},
            {"code": "awx", "name": "AWX / Ansible Tower", "category": "automation",
             "version": "1.0", "provider_class": "integration.adapters.automation.awx.AWXConnector",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://localhost:8080/api/v2", "required": True},
                 {"key": "verify_ssl", "title": "Verify SSL", "type": "bool", "default": False},
                 {"key": "timeout", "title": "Timeout (s)", "type": "int", "default": 30},
                 {"key": "template_id", "title": "默认 Template ID", "type": "int", "default": 1},
             ])},
            {"code": "saltstack", "name": "SaltStack", "category": "automation",
             "config_schema": _schema([
                 {"key": "master_url", "title": "Master 地址", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 4506},
             ])},
            {"code": "puppet", "name": "Puppet", "category": "automation",
             "config_schema": _schema([
                 {"key": "server_url", "title": "Puppet Server", "required": True},
             ])},
            # ─── Database ───
            {"code": "neo4j", "name": "Neo4j 图数据库", "category": "other",
             "version": "1.0", "provider_class": "integration.adapters.database.neo4j.Neo4jConnector",
             "config_schema": _schema([
                 {"key": "host", "title": "主机地址", "default": "127.0.0.1"},
                 {"key": "port", "title": "端口", "type": "int", "default": 7687},
                 {"key": "protocol", "title": "协议", "default": "bolt"},
                 {"key": "user", "title": "默认用户", "default": "neo4j"},
             ])},
            # ─── CI/CD ───
            {"code": "jenkins", "name": "Jenkins", "category": "cicd",
             "config_schema": _schema([
                 {"key": "url", "title": "Jenkins URL", "required": True},
             ])},
            {"code": "gitlab_ci", "name": "GitLab CI", "category": "cicd",
             "config_schema": _schema([
                 {"key": "url", "title": "GitLab URL", "default": "https://gitlab.com"},
             ])},
            {"code": "github_actions", "name": "GitHub Actions", "category": "cicd",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.github.com"},
             ])},
            {"code": "argocd", "name": "ArgoCD", "category": "cicd",
             "config_schema": _schema([
                 {"key": "server_url", "title": "ArgoCD Server", "required": True},
             ])},
            # ─── SCM ───
            {"code": "gitlab", "name": "GitLab", "category": "scm",
             "config_schema": _schema([
                 {"key": "url", "title": "GitLab URL", "default": "https://gitlab.com"},
             ])},
            {"code": "github", "name": "GitHub", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.github.com"},
             ])},
            {"code": "bitbucket", "name": "Bitbucket", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.bitbucket.org"},
             ])},
            {"code": "gitee", "name": "Gitee (码云)", "category": "scm",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://gitee.com/api"},
             ])},
            # ─── Log / Observability ───
            {"code": "elasticsearch", "name": "Elasticsearch", "category": "log",
             "config_schema": _schema([
                 {"key": "hosts", "title": "节点地址", "default": "http://localhost:9200", "required": True},
             ])},
            {"code": "graylog", "name": "Graylog", "category": "log",
             "config_schema": _schema([
                 {"key": "url", "title": "Graylog URL", "required": True},
             ])},
            {"code": "loki", "name": "Grafana Loki", "category": "log",
             "config_schema": _schema([
                 {"key": "url", "title": "Loki URL", "default": "http://localhost:3100"},
             ])},
            {"code": "splunk", "name": "Splunk", "category": "log",
             "config_schema": _schema([
                 {"key": "host", "title": "Splunk Host", "required": True},
                 {"key": "port", "title": "端口", "type": "int", "default": 8089},
             ])},
            # ─── Monitor ───
            {"code": "prometheus", "name": "Prometheus", "category": "monitor",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "http://localhost:9090", "required": True},
             ])},
            {"code": "grafana", "name": "Grafana", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Grafana URL", "default": "http://localhost:3000"},
             ])},
            {"code": "zabbix", "name": "Zabbix", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Zabbix URL", "required": True},
             ])},
            {"code": "nagios", "name": "Nagios", "category": "monitor",
             "config_schema": _schema([
                 {"key": "url", "title": "Nagios URL", "default": "http://localhost/nagios"},
             ])},
            {"code": "datadog", "name": "Datadog", "category": "monitor",
             "config_schema": _schema([
                 {"key": "site", "title": "Site", "default": "datadoghq.com"},
             ])},
            # ─── PaaS / Container ───
            {"code": "kubernetes", "name": "Kubernetes", "category": "paas",
             "config_schema": _schema([
                 {"key": "api_server", "title": "API Server", "required": True},
                 {"key": "namespace", "title": "默认 Namespace", "default": "default"},
             ])},
            {"code": "docker", "name": "Docker", "category": "paas",
             "config_schema": _schema([
                 {"key": "host", "title": "Docker Host", "default": "unix:///var/run/docker.sock"},
             ])},
            {"code": "rancher", "name": "Rancher", "category": "paas",
             "config_schema": _schema([
                 {"key": "server_url", "title": "Rancher URL", "required": True},
             ])},
            {"code": "openshift", "name": "OpenShift", "category": "paas",
             "config_schema": _schema([
                 {"key": "api_server", "title": "API Server", "required": True},
             ])},
            # ─── ITSM / Ops ───
            {"code": "jira", "name": "Jira", "category": "other",
             "config_schema": _schema([
                 {"key": "url", "title": "Jira URL", "required": True},
             ])},
            {"code": "confluence", "name": "Confluence", "category": "other",
             "config_schema": _schema([
                 {"key": "url", "title": "Confluence URL", "required": True},
             ])},
            {"code": "pagerduty", "name": "PagerDuty", "category": "other",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.pagerduty.com"},
             ])},
            {"code": "opsgenie", "name": "Opsgenie", "category": "other",
             "config_schema": _schema([
                 {"key": "api_url", "title": "API URL", "default": "https://api.opsgenie.com"},
             ])},
            {"code": "service_now", "name": "ServiceNow", "category": "other",
             "config_schema": _schema([
                 {"key": "instance_url", "title": "Instance URL", "required": True},
             ])},
        ]
        c_count = 0
        for c in connectors:
            _, created = ConnectorDefinition.objects.update_or_create(
                code=c["code"], defaults=c
            )
            if created:
                c_count += 1
        self.stdout.write(f">>> Connector Definitions: {c_count} new, {len(connectors) - c_count} existing (config_schema updated)")
        self.stdout.write(f"    新增 {c_count} 个连接器定义，{len(connectors) - c_count} 个已有定义配置已同步")

    # ── 7. IAM Menu ──

    def _seed_iam_menu(self):
        from dvadmin.system.models import Menu
        catalog, _ = Menu.objects.get_or_create(
            name="权限管理", web_path="/iam",
            defaults={"icon": "iconfont icon-safe", "sort": 5, "status": True, "parent": None},
        )
        menu, created = Menu.objects.get_or_create(
            name="权限申请", parent=catalog,
            defaults={
                "web_path": "", "icon": "iconfont icon-safe", "sort": 1, "status": True,
                "component": "apps/iam/index", "component_name": "iam",
            },
        )
        self.stdout.write(f">>> IAM Menu: {'created' if created else 'found'}")

    # ── 8. Migrate Projects ──

    def _migrate_projects(self):
        from opsflow.models import OpsProject, FlowTemplate, FlowExecution
        from opsflow.models import SchedulePlan, OpsKnowledge, ExecutionScheme, ProjectMember

        default_project, created = OpsProject.objects.get_or_create(
            name="Default Project",
            defaults={"description": "Default project for existing data", "is_active": True},
        )

        # Migrate orphan data
        migrated_total = 0
        for model, name in [
            (FlowTemplate, "templates"), (FlowExecution, "executions"),
            (SchedulePlan, "schedule_plans"), (OpsKnowledge, "knowledge"),
            (ExecutionScheme, "execution_schemes"),
        ]:
            count = model.objects.filter(project__isnull=True).update(project=default_project)
            migrated_total += count
            if count:
                self.stdout.write(f"  Migrated {count} orphan {name}")

        # Ensure project owner is member
        for project in OpsProject.objects.filter(owner__isnull=False):
            ProjectMember.objects.get_or_create(
                project=project, user=project.owner,
                defaults={"role": ProjectMember.Role.ADMIN},
            )

        self.stdout.write(f">>> Projects: default project {'created' if created else 'found'}, "
                          f"{migrated_total} orphan records migrated")

    # ── 9. Sample Templates ──

    def _seed_sample_templates(self):
        from opsflow.models import OpsProject, FlowTemplate, TemplateCategory
        from opsflow.core.node_sync import sync_template_nodes

        # Ensure Demo Project exists (created by add_mock_data, but bootstrap may skip demo)
        project, _ = OpsProject.objects.get_or_create(
            name="Demo Project",
            defaults={"description": "Auto-created demo project for onboarding", "is_active": True},
        )

        def _seed_one(name, category, desc, pipeline):
            tpl, created = FlowTemplate.objects.get_or_create(
                name=name,
                defaults={
                    "project": project, "category": category, "description": desc,
                    "pipeline_tree": pipeline, "is_draft": False, "version": 1,
                },
            )
            if created:
                tpl.created_by = User.objects.filter(is_superuser=True).first()
                tpl.save(update_fields=["created_by"] if tpl.created_by else [])
                # Publish snapshot
                from opsflow.models import TemplateVersion
                TemplateVersion.objects.get_or_create(
                    template=tpl, version=1,
                    defaults={"created_by": tpl.created_by, "pipeline_tree": pipeline},
                )
                from opsflow.core.pipeline_builder import publish_pipeline_snapshot
                publish_pipeline_snapshot(tpl)
                sync_template_nodes(tpl, pipeline.get("nodes", []))
                return tpl, True
            return tpl, False

        for tpl in SAMPLE_TEMPLATES:
            _, created = _seed_one(tpl["name"], tpl["category"], tpl["description"], tpl["pipeline"])
            self.stdout.write(f"  Sample template: {'created' if created else 'found'} — {tpl['name']}")
