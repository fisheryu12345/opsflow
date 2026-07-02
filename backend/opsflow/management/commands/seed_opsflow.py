"""Seed OpsFlow reference & mock data"""

from iam.models import Project, ProjectMember
from opsflow.models import (FlowTemplate, TemplateCategory, TemplateNode, TemplatePreset,
    OpsKnowledge, SchedulePlan, FlowExecution, ExecutionScheme, PluginMeta,
    ApiToken, ProjectEnvironmentVariable, WebhookConfig, OperationRecord)
from opsflow.core.node_sync import sync_template_nodes
from opsflow.plugins.registry import discover_plugins
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

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
    help = "Seed OpsFlow data"

    def handle(self, *args, **options):
        self._seed_template_categories()
        self._seed_knowledge()
        self._migrate_projects()
        self._seed_sample_templates()
        self._create_projects()
        self._create_template_categories()
        self._create_templates()
        self._create_plugins()
        self._create_schedules()
        self._create_webhooks()
        self._create_knowledge()
        self._create_api_tokens()
        self._create_env_vars()
        self._create_executions()
        self._create_execution_schemes()
        self._create_audit_records()
        self.stdout.write(self.style.SUCCESS("OpsFlow seed complete!"))

    def _get_or_create(self, model_class, defaults_update=None, **lookup):
        """Get or create a model instance. With --force, update defaults."""
        obj, created = model_class.objects.get_or_create(defaults={}, **lookup)
        if not created and self.force:
            if defaults_update:
                for k, v in defaults_update.items():
                    setattr(obj, k, v)
                obj.save()
        elif created and defaults_update:
            for k, v in defaults_update.items():
                setattr(obj, k, v)
            obj.save()
        return obj, created

    def _random_project(self):
        import random
        if not self.project_map:
            return None
        ids = list(self.project_map.keys())
        return self.project_map[random.choice(ids)]

    def _random_template(self):
        from opsflow.models import FlowTemplate
        qs = FlowTemplate.objects.all()
        if not qs.exists():
            return None
        import random
        return random.choice(list(qs))

    # ── data creators ──

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

    def _migrate_projects(self):
        from iam.models import Project, ProjectMember
        from opsflow.models import FlowTemplate, FlowExecution
        from opsflow.models import SchedulePlan, OpsKnowledge, ExecutionScheme

        default_project, created = Project.objects.get_or_create(
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
        for project in Project.objects.filter(owner__isnull=False):
            ProjectMember.objects.get_or_create(
                project=project, user=project.owner,
                defaults={"role": ProjectMember.Role.ADMIN},
            )

        self.stdout.write(f">>> Projects: default project {'created' if created else 'found'}, "
                          f"{migrated_total} orphan records migrated")

    # ── 9. Sample Templates ──

    def _seed_sample_templates(self):
        from iam.models import Project
        from opsflow.models import FlowTemplate, TemplateCategory
        from opsflow.core.node_sync import sync_template_nodes

        # Ensure Demo Project exists (created by add_mock_data, but bootstrap may skip demo)
        project, _ = Project.objects.get_or_create(
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

    def _create_projects(self):
        self.stdout.write("\n>>> Creating Projects ...")
        from iam.models import Project, ProjectMember
        for p in SAMPLE_PROJECTS:
            obj, created = self._get_or_create(Project, name=p["name"])
            if created or self.force:
                obj.owner = self.admin_user
                obj.save(update_fields=['owner'] if not created else [])
            self.project_map[obj.id] = obj
            # add project member
            ProjectMember.objects.get_or_create(project=obj, user=self.admin_user, defaults={'role': 'admin'})
            self.stdout.write(f"  {'+' if created else ' '} Project: {p['name']}")

    def _create_template_categories(self):
        self.stdout.write("\n>>> Creating Template Categories ...")
        from django.db.utils import IntegrityError
        from opsflow.models import TemplateCategory
        existing_codes = set(TemplateCategory.objects.values_list('code', flat=True))
        existing_names = set(TemplateCategory.objects.values_list('name', flat=True))
        for c in SAMPLE_TEMPLATE_CATEGORIES:
            if c["code"] in existing_codes:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (exists)")
                continue
            if c["name"] in existing_names:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (name exists, skip)")
                continue
            try:
                obj = TemplateCategory.objects.create(code=c["code"], name=c["name"])
                self.stdout.write(f"  + Category: {obj.name} ({obj.code})")
            except IntegrityError as e:
                self.stdout.write(f"    Category: {c['name']} ({c['code']}) (skip: {e})")

    def _create_templates(self):
        self.stdout.write("\n>>> Creating Templates + Nodes + Versions ...")
        from opsflow.models import FlowTemplate, TemplateNode, TemplateVersion

        for i, t in enumerate(SAMPLE_TEMPLATES):
            proj = self._random_project()
            obj, created = self._get_or_create(
                FlowTemplate, name=t["name"],
                defaults_update={
                    "project": proj,
                    "category": t["category_code"],
                    "pipeline_tree": t["pipeline_tree"],
                    "is_draft": False,
                    "description": f"{t['name']} — auto-generated mock template",
                    "version": 1,
                }
            )
            if created:
                obj.created_by = self.admin_user
                obj.save(update_fields=['created_by'])
            self.stdout.write(f"  {'+' if created else ' '} Template: {t['name']}")

            # Create template nodes
            if created or self.force:
                for node in t["pipeline_tree"].get("nodes", []):
                    TemplateNode.objects.get_or_create(
                        template=obj,
                        node_id=node["id"],
                        defaults={"node_type": node.get("type", "task"), "label": node.get("label", "")},
                    )

            # Create version
            TemplateVersion.objects.get_or_create(
                template=obj, version=1,
                defaults={
                    "created_by": self.admin_user,
                    "pipeline_tree": t["pipeline_tree"],
                },
            )

    def _create_plugins(self):
        self.stdout.write("\n>>> Creating Plugins ...")
        from opsflow.models import PluginMeta
        for p in SAMPLE_PLUGINS:
            obj, created = self._get_or_create(PluginMeta, code=p["code"], name=p["name"], group=p["group"],
                                                defaults_update={"risk_level": "low", "is_active": True})
            self.stdout.write(f"  {'+' if created else ' '} Plugin: {p['name']}")

    def _create_schedules(self):
        self.stdout.write("\n>>> Creating Schedule Plans ...")
        from opsflow.models import SchedulePlan
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:5])
        for i, t in enumerate(templates[:3]):
            obj, created = self._get_or_create(
                SchedulePlan, template=t, name=f"{t.name} 每日执行",
                defaults_update={
                    "schedule_type": "cron",
                    "cron_expr": "0 3 * * *",
                    "project": self._random_project(),
                    "created_by": self.admin_user,
                }
            )
            self.stdout.write(f"  {'+' if created else ' '} Schedule: {obj.name}")

    def _create_webhooks(self):
        self.stdout.write("\n>>> Creating Webhook Configs ...")
        from opsflow.models import WebhookConfig, FlowTemplate
        templates = list(FlowTemplate.objects.all()[:5])
        webhook_defs = [
            {"name": "企业微信通知", "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock-key"},
            {"name": "钉钉机器人", "url": "https://oapi.dingtalk.com/robot/send?access_token=mock-token"},
            {"name": "飞书机器人", "url": "https://open.feishu.cn/open-apis/bot/v2/hook/mock"},
        ]
        for t in templates[:3]:
            for w in webhook_defs:
                obj, created = self._get_or_create(
                    WebhookConfig, template=t, name=w["name"], url=w["url"],
                    defaults_update={"created_by": self.admin_user},
                )
                if created:
                    self.stdout.write(f"  + Webhook: {w['name']} -> {t.name}")

    def _create_knowledge(self):
        self.stdout.write("\n>>> Creating Knowledge Base ...")
        from opsflow.models import OpsKnowledge
        for k in SAMPLE_KNOWLEDGE:
            obj, created = self._get_or_create(
                OpsKnowledge, title=k["title"],
                defaults_update={"content": k["content"], "tags": k["tags"], "source": "doc"},
            )
            self.stdout.write(f"  {'+' if created else ' '} Knowledge: {k['title']}")

    def _create_api_tokens(self):
        self.stdout.write("\n>>> Creating API Tokens ...")
        import uuid
        from opsflow.models import ApiToken
        tokens = [
            {"name": "CMDB 同步 Token", "allowed_actions": ["cmdb.sync"]},
            {"name": "监控告警 Token", "allowed_actions": ["monitor.push_alert"]},
            {"name": "CI/CD Token", "allowed_actions": ["execution.create", "execution.start"]},
        ]
        for t in tokens:
            obj, created = self._get_or_create(
                ApiToken, name=t["name"],
                defaults_update={
                    "token": uuid.uuid4().hex[:32],
                    "created_by": self.admin_user,
                    "allowed_actions": t["allowed_actions"],
                },
            )
            self.stdout.write(f"  {'+' if created else ' '} ApiToken: {t['name']}")

    def _create_env_vars(self):
        self.stdout.write("\n>>> Creating Environment Variables ...")
        from opsflow.models import ProjectEnvironmentVariable
        env_vars = [
            {"key": "NGINX_HOME", "value": "/usr/local/nginx", "var_type": "input"},
            {"key": "MYSQL_ROOT_PASSWORD", "value": "******", "var_type": "password"},
            {"key": "JAVA_HOME", "value": "/usr/lib/jvm/java-11", "var_type": "input"},
            {"key": "LOG_RETENTION_DAYS", "value": "30", "var_type": "int"},
            {"key": "ALERT_WEBHOOK_URL", "value": "https://alert.example.com/hook", "var_type": "input"},
        ]
        projects = list(self.project_map.values())
        for proj in projects[:3]:
            for ev in env_vars:
                obj, created = self._get_or_create(
                    ProjectEnvironmentVariable, project=proj, key=ev["key"],
                    defaults_update={"value": ev["value"], "var_type": ev["var_type"]},
                )
                if created:
                    self.stdout.write(f"  + EnvVar: {ev['key']} -> {proj.name}")

    def _create_executions(self):
        self.stdout.write("\n>>> Creating Executions ...")
        from opsflow.models import FlowTemplate, FlowExecution, ExecutionNode
        from opsflow.models.execution import NodeExecutionTrace
        templates = list(FlowTemplate.objects.all()[:6])
        statuses = ["completed", "running", "failed", "paused", "cancelled"]
        for i, t in enumerate(templates):
            status = statuses[i % len(statuses)]
            now = timezone.now()
            started = now - datetime.timedelta(hours=random.randint(1, 72))
            ended = now if status == "running" else started + datetime.timedelta(minutes=random.randint(5, 60))
            exec_obj, created = FlowExecution.objects.get_or_create(
                template=t,
                status=status,
                created_by=self.admin_user,
                defaults={
                    "project": self._random_project(),
                    "state_tree": {},
                    "context": {"dry_run": False},
                    "template_snapshot": {
                        "pipeline_tree": t.pipeline_tree,
                        "global_vars": {},
                        "template_version": t.version,
                    },
                },
            )
            if created:
                # Create execution nodes
                nodes_data = (t.pipeline_tree or {}).get("nodes", [])
                for nd in nodes_data:
                    ExecutionNode.objects.get_or_create(
                        execution=exec_obj, node_id=nd["id"],
                        defaults={"node_type": nd.get("type", "task"), "status": status if status != "running" else "completed"},
                    )
                self.stdout.write(f"  + Execution #{exec_obj.id} ({t.name}): {status}")
            else:
                self.stdout.write(f"    Execution #{exec_obj.id} ({t.name}): {status} (exists)")

    def _create_execution_schemes(self):
        self.stdout.write("\n>>> Creating Execution Schemes ...")
        from opsflow.models import ExecutionScheme
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:4])
        scheme_names = ["快速执行方案", "全量部署方案", "灰度发布方案", "回滚方案"]
        for i, t in enumerate(templates):
            name = scheme_names[i % len(scheme_names)]
            obj, created = self._get_or_create(
                ExecutionScheme, template=t, name=name,
                defaults_update={
                    "project": self._random_project(),
                    "created_by": self.admin_user,
                    "excluded_nodes": [],
                },
            )
            self.stdout.write(f"  {'+' if created else ' '} Scheme: {name} -> {t.name}")

    def _create_audit_records(self):
        self.stdout.write("\n>>> Creating Operation Records ...")
        from opsflow.models import OperationRecord, OpsLog
        from opsflow.models import FlowTemplate
        templates = list(FlowTemplate.objects.all()[:3])
        actions = ["create", "update", "publish", "execute", "approve"]
        count = 0
        for t in templates:
            for idx, action in enumerate(actions):
                # Use unique detail + resource_id to avoid MultipleObjectsReturned
                detail = {"template_name": t.name, "version": t.version, "action_index": idx}
                op, created = OperationRecord.objects.get_or_create(
                    action=action,
                    resource_type="template",
                    resource_id=str(t.id),
                    operator=self.admin_user,
                    defaults={"detail": detail},
                )
                if created:
                    count += 1
        self.stdout.write(f"  + Created {count} OperationRecords")
