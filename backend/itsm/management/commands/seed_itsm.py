"""Seed complete ITSM test data — all models"""
from django.core.management.base import BaseCommand
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = "Seed complete ITSM test data"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pid = None
        self._bid = None
        self.admin_user = None
        self.cat_map = {}
        self.sla_map = {}
        self.group_map = {}
        self.wf_list = []

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', default=False,
                            help='Update existing records')

    def _resolve_tenant(self):
        from iam.models import Project, Business
        p = Project.objects.first()
        b = Business.objects.first()
        self._pid = p.id if p else None
        self._bid = b.id if b else None
        if self._pid:
            self.stdout.write(f"  Project: {p.name} (id={self._pid})")
        if self._bid:
            self.stdout.write(f"  Business: {b.name} (id={self._bid})")

    def _resolve_admin(self):
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.filter(is_superuser=True).first()
        self.admin_user = u
        if u:
            self.stdout.write(f"  Admin: {u.username}")

    def handle(self, *args, **options):
        self.force = options['force']
        self._resolve_admin()
        self._resolve_tenant()

        self._create_service_categories()
        self._create_sla_policies()
        self._create_skill_groups()
        self._create_workflows()
        self._create_escalation_levels()
        self._create_assign_rules()
        self._create_on_duty_schedules()
        self._create_incidents_and_legacy()
        self._create_service_items()

        self.stdout.write(self.style.SUCCESS("\nSeed complete!"))

    # ── Service Categories ──
    def _create_service_categories(self):
        self.stdout.write("\n>>> Service Categories ...")
        from itsm.models import ServiceCategory

        cat_defs = [
            {"name": "Server Ops", "code": "server-ops", "children": [
                {"name": "Server Reboot", "code": "server-reboot"},
                {"name": "Disk Expand", "code": "disk-expand"},
                {"name": "OS Reinstall", "code": "os-reinstall"},
            ]},
            {"name": "App Support", "code": "app-support", "children": [
                {"name": "App Deploy", "code": "app-deploy"},
                {"name": "Config Change", "code": "config-change"},
                {"name": "Log Query", "code": "log-query"},
            ]},
            {"name": "Network Ops", "code": "network-ops", "children": [
                {"name": "VPN Apply", "code": "vpn-apply"},
                {"name": "Firewall Change", "code": "firewall-change"},
            ]},
            {"name": "DB Ops", "code": "db-ops", "children": [
                {"name": "DB Backup", "code": "db-backup"},
                {"name": "SQL Execute", "code": "sql-exec"},
            ]},
        ]
        for pd in cat_defs:
            p, _ = ServiceCategory.objects.get_or_create(
                code=pd["code"],
                defaults={"name": pd["name"], "project_id": self._pid},
            )
            self.cat_map[p.code] = p
            for i, cd in enumerate(pd.get("children", [])):
                c, _ = ServiceCategory.objects.get_or_create(
                    code=cd["code"],
                    defaults={"name": cd["name"], "parent": p, "sort_order": i,
                              "project_id": self._pid},
                )
                self.cat_map[c.code] = c
        self.stdout.write(f"  + {ServiceCategory.objects.count()} categories")

    # ── SLA Policies ──
    def _create_sla_policies(self):
        self.stdout.write(">>> SLA Policies ...")
        from itsm.models import SlaPolicy

        for d in [
            ("P1 Critical", "P1", 15, 60),
            ("P2 High", "P2", 30, 180),
            ("P3 Normal", "P3", 60, 480),
            ("P4 Low", "P4", 240, 1440),
        ]:
            obj, _ = SlaPolicy.objects.get_or_create(
                priority=d[1],
                defaults={"name": d[0], "response_minutes": d[2],
                          "resolve_minutes": d[3], "project_id": self._pid},
            )
            self.sla_map[d[1]] = obj
        self.stdout.write(f"  + {SlaPolicy.objects.count()} SLA policies")

    # ── Skill Groups ──
    def _create_skill_groups(self):
        self.stdout.write(">>> Skill Groups ...")
        from itsm.models.skill_group import SkillGroup

        groups = [
            ("Network Team", "net-team", "Network infrastructure"),
            ("DBA Team", "dba-team", "Database administration"),
            ("App Team", "app-team", "Application support"),
            ("Platform Team", "platform-team", "K8s / cloud platform"),
            ("Security Team", "sec-team", "Security & compliance"),
        ]
        for name, code, desc in groups:
            grp, _ = SkillGroup.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc,
                          "business_id": self._bid},
            )
            if self.admin_user:
                grp.leader = self.admin_user
                grp.save(update_fields=['leader'])
                grp.members.add(self.admin_user)
            self.group_map[code] = grp
        self.stdout.write(f"  + {SkillGroup.objects.count()} groups")

    # ── Workflows (flow templates) ──
    def _create_workflows(self):
        self.stdout.write(">>> Workflows ...")
        from itsm.models import Workflow, State, Transition

        wf_defs = [
            {
                "name": "Server Change Approval",
                "itsm_type": "change",
                "nodes": [
                    {"type": "NORMAL", "name": "Fill Form", "is_builtin": True},
                    {"type": "APPROVAL", "name": "Manager Approve",
                     "processors_type": "PERSON", "processors": str(self.admin_user.id) if self.admin_user else ""},
                    {"type": "APPROVAL", "name": "Director Approve",
                     "processors_type": "PERSON", "processors": str(self.admin_user.id) if self.admin_user else ""},
                    {"type": "TASK", "name": "Execute Change"},
                    {"type": "NORMAL", "name": "Verify", "is_builtin": True},
                ],
            },
            {
                "name": "Incident Handling",
                "itsm_type": "incident",
                "nodes": [
                    {"type": "NORMAL", "name": "Report", "is_builtin": True},
                    {"type": "APPROVAL", "name": "Team Lead Approve",
                     "processors_type": "PERSON", "processors": str(self.admin_user.id) if self.admin_user else ""},
                    {"type": "TASK", "name": "Investigate & Fix"},
                    {"type": "NORMAL", "name": "Close", "is_builtin": True},
                ],
            },
            {
                "name": "Simple Request",
                "itsm_type": "request",
                "nodes": [
                    {"type": "NORMAL", "name": "Submit", "is_builtin": True},
                    {"type": "TASK", "name": "Fulfill"},
                    {"type": "APPROVAL", "name": "Confirm",
                     "processors_type": "PERSON", "processors": str(self.admin_user.id) if self.admin_user else ""},
                    {"type": "NORMAL", "name": "Done", "is_builtin": True},
                ],
            },
        ]

        for wd in wf_defs:
            wf, created = Workflow.objects.get_or_create(
                name=wd["name"],
                defaults={"itsm_type": wd["itsm_type"], "is_draft": True,
                          "project_id": self._pid, "description": wd["name"]},
            )
            if created:
                prev_id = None
                for i, nd in enumerate(wd["nodes"]):
                    s = State.objects.create(
                        workflow=wf, name=nd["name"], type=nd["type"],
                        processors_type=nd.get("processors_type", ""),
                        processors=nd.get("processors", ""),
                        is_builtin=nd.get("is_builtin", False),
                    )
                    if prev_id:
                        Transition.objects.create(
                            workflow=wf, name="",
                            from_state_id=prev_id, to_state_id=s.id,
                        )
                    prev_id = s.id
            self.wf_list.append(wf)
        self.stdout.write(f"  + {Workflow.objects.count()} workflows")

    # ── Escalation Levels ──
    def _create_escalation_levels(self):
        self.stdout.write(">>> Escalation Levels ...")
        from itsm.models.escalation import EscalationLevel

        for gcode, levels in [
            ("net-team", [("L1", 1, 15, "notify_only"),
                          ("L2", 2, 30, "transfer_to_leader"),
                          ("L3", 3, 60, "transfer_to_next_level")]),
            ("app-team", [("L1", 1, 20, "notify_only"),
                          ("L2", 2, 45, "transfer_to_leader")]),
            ("dba-team", [("L1", 1, 10, "notify_only"),
                          ("L2", 2, 30, "transfer_to_next_level")]),
        ]:
            grp = self.group_map.get(gcode)
            if not grp:
                continue
            for name, lvl, tmo, action in levels:
                EscalationLevel.objects.get_or_create(
                    group=grp, level=lvl,
                    defaults={"name": name, "timeout_minutes": tmo,
                              "action": action, "project_id": self._pid},
                )
        from itsm.models.escalation import EscalationLevel
        self.stdout.write(f"  + {EscalationLevel.objects.count()} escalation levels")

    # ── Assign Rules ──
    def _create_assign_rules(self):
        self.stdout.write(">>> Assign Rules ...")
        from itsm.models.assign_rule import AssignRule

        rules = [
            ("P1/P2 -> DBA", 10, "db-ops", "P1", None, "dba-team", "to_onduty"),
            ("P1/P2 -> App", 20, "app-support", "P1", None, "app-team", "to_onduty"),
            ("Network incidents", 30, "network-ops", None, "incident", "net-team", "to_group"),
            ("Default change", 50, None, None, "change", "platform-team", "to_onduty"),
            ("Fallback", 100, None, None, None, "app-team", "to_group"),
        ]
        for name, pri, cat, mpri, mtype, gcode, mode in rules:
            cat_obj = self.cat_map.get(cat) if cat else None
            target = self.group_map.get(gcode)
            if not target:
                continue
            AssignRule.objects.get_or_create(
                name=name,
                defaults={"priority": pri, "match_category": cat_obj,
                          "match_priority": mpri, "match_itsm_type": mtype,
                          "target_group": target, "assign_mode": mode,
                          "is_active": True, "project_id": self._pid},
            )
        self.stdout.write(f"  + {AssignRule.objects.count()} rules")

    # ── On-Duty Schedules ──
    def _create_on_duty_schedules(self):
        self.stdout.write(">>> On-Duty Schedules ...")
        from itsm.models.skill_group import OnDutySchedule

        if not self.admin_user:
            self.stdout.write("  (no admin user, skip)")
            return

        today = timezone.localdate()
        for offset, gcode in enumerate(["net-team", "app-team", "dba-team", "platform-team"]):
            grp = self.group_map.get(gcode)
            if not grp:
                continue
            dt = today + datetime.timedelta(days=offset)
            OnDutySchedule.objects.get_or_create(
                group=grp, duty_date=dt, duty_type="primary",
                defaults={"user": self.admin_user, "project_id": self._pid},
            )
            OnDutySchedule.objects.get_or_create(
                group=grp, duty_date=dt, duty_type="backup",
                defaults={"user": self.admin_user, "project_id": self._pid},
            )
        self.stdout.write(f"  + {OnDutySchedule.objects.count()} schedules")

    # ── Incidents & Legacy Records ──
    def _create_incidents_and_legacy(self):
        self.stdout.write(">>> Incidents / Changes / Requests / Problems ...")
        from itsm.models import Incident, Change, ServiceRequest, Problem
        pid = self._pid

        incidents = [
            ("INC000001", "Homepage loading timeout", "P1", "alert", "server-ops", "new"),
            ("INC000002", "Payment API 5xx spike", "P1", "alert", "app-support", "assigned"),
            ("INC000003", "DB connection pool exhausted", "P2", "alert", "db-ops", "in_progress"),
            ("INC000004", "Disk usage > 90% on /data", "P2", "alert", "server-ops", "resolved"),
            ("INC000005", "VPN connection failure", "P3", "user", "vpn-apply", "new"),
            ("INC000006", "Firewall rule change request", "P3", "user", "firewall-change", "new"),
            ("INC000007", "Nginx config syntax error", "P2", "alert", "app-support", "in_progress"),
            ("INC000008", "K8s node NotReady", "P1", "alert", "server-ops", "assigned"),
            ("INC000009", "Log collector agent offline", "P3", "alert", "log-query", "new"),
            ("INC000010", "SSL certificate expiring soon", "P3", "api", "config-change", "new"),
        ]
        for iid, title, pri, src, cat_code, st in incidents:
            Incident.objects.get_or_create(
                incident_id=iid,
                defaults={"title": title, "priority": pri, "source": src, "status": st,
                          "category": self.cat_map.get(cat_code),
                          "sla_policy": self.sla_map.get(pri),
                          "assignee": self.admin_user,
                          "project_id": pid},
            )

        changes = [
            ("CHG000001", "Nginx version upgrade to 1.26", "normal", "medium", "approved"),
            ("CHG000002", "MySQL master-slave switch drill", "standard", "low", "pending_approval"),
            ("CHG000003", "Redis cluster scale-out +3 nodes", "normal", "high", "draft"),
            ("CHG000004", "K8s cert renewal (expires in 48h)", "emergency", "high", "approved"),
            ("CHG000005", "Firewall policy allow new subnet", "standard", "low", "in_progress"),
            ("CHG000006", "/var/log volume expand 100G->200G", "normal", "low", "completed"),
        ]
        now = timezone.now()
        for cid, title, ctype, risk, st in changes:
            Change.objects.get_or_create(
                change_id=cid,
                defaults={"title": title, "change_type": ctype, "risk_level": risk,
                          "status": st, "applicant": self.admin_user,
                          "assignee": self.admin_user,
                          "planned_start": now + datetime.timedelta(days=1),
                          "planned_end": now + datetime.timedelta(days=2),
                          "project_id": pid},
            )

        requests = [
            ("REQ000001", "Apply VPN account", "vpn-apply", "in_progress"),
            ("REQ000002", "Disk expansion 50G for /data", "disk-expand", "pending"),
            ("REQ000003", "Query payment API logs yesterday", "log-query", "fulfilled"),
            ("REQ000004", "Apply server sudo access", "server-ops", "pending"),
            ("REQ000005", "Restore deleted table from backup", "db-backup", "in_progress"),
            ("REQ000006", "Firewall open port 443 for new app", "firewall-change", "pending"),
        ]
        for rid, title, cat_code, st in requests:
            ServiceRequest.objects.get_or_create(
                request_id=rid,
                defaults={"title": title, "status": st,
                          "category": self.cat_map.get(cat_code),
                          "requester": self.admin_user,
                          "assignee": self.admin_user,
                          "fulfilled_at": now if st == "fulfilled" else None,
                          "project_id": pid},
            )

        problems = [
            ("PRB000001", "Payment API intermittent timeout RCA", "P1", "investigating"),
            ("PRB000002", "Disk frequently full on /data", "P2", "root_cause_found"),
            ("PRB000003", "Nginx connections keep growing", "P3", "new"),
        ]
        for pid_str, title, pri, st in problems:
            Problem.objects.get_or_create(
                problem_id=pid_str,
                defaults={"title": title, "priority": pri, "status": st,
                          "assignee": self.admin_user, "project_id": pid},
            )

        self.stdout.write(f"  Incidents: {Incident.objects.count()}")
        self.stdout.write(f"  Changes: {Change.objects.count()}")
        self.stdout.write(f"  Requests: {ServiceRequest.objects.count()}")
        self.stdout.write(f"  Problems: {Problem.objects.count()}")

    # ── Service Items (Service Catalog) ──
    def _create_service_items(self):
        self.stdout.write(">>> Service Items ...")
        from itsm.models import ServiceItem

        items = [
            {"name": "申请服务器", "description": "申请一台新的云服务器或物理服务器，指定配置、操作系统和网络", "icon": "🖥️",
             "mode": "flow", "cat": "server-ops", "duration": "3-5 工作日", "sort": 10,
             "fields": [
                 {"key": "env", "name": "环境类型", "type": "SELECT", "required": True,
                  "choice": [{"value": "dev", "label": "开发"}, {"value": "staging", "label": "预发布"}, {"value": "prod", "label": "生产"}]},
                 {"key": "cpu", "name": "CPU 核数", "type": "STRING", "required": True, "placeholder": "例如: 4 Cores"},
                 {"key": "memory", "name": "内存", "type": "STRING", "required": True, "placeholder": "例如: 8 GB"},
             ]},
            {"name": "服务器重启", "description": "重启指定服务器，支持计划内重启和紧急重启，将通知关联人员", "icon": "🔄",
             "mode": "flow", "cat": "server-ops", "duration": "30 分钟", "sort": 20,
             "fields": [
                 {"key": "hostname", "name": "服务器主机名", "type": "STRING", "required": True, "placeholder": "例如: web-01"},
                 {"key": "reason", "name": "重启原因", "type": "TEXT", "required": True},
                 {"key": "reboot_type", "name": "重启类型", "type": "SELECT", "required": True,
                  "choice": [{"value": "planned", "label": "计划内"}, {"value": "emergency", "label": "紧急"}]},
             ]},
            {"name": "磁盘扩容", "description": "扩容服务器磁盘空间，支持系统盘和数据盘在线扩容", "icon": "💾",
             "mode": "flow", "cat": "server-ops", "duration": "1-2 工作日", "sort": 30,
             "fields": [
                 {"key": "hostname", "name": "服务器", "type": "STRING", "required": True},
                 {"key": "disk", "name": "目标磁盘", "type": "STRING", "required": True, "placeholder": "例如: /dev/sdb"},
                 {"key": "expand_gb", "name": "扩容大小 (GB)", "type": "INT", "required": True},
             ]},
            {"name": "应用发布", "description": "提交应用版本发布申请，经过审批后自动执行部署流程", "icon": "🚀",
             "mode": "flow", "cat": "app-support", "duration": "2-4 小时", "sort": 40,
             "fields": [
                 {"key": "app_name", "name": "应用名称", "type": "STRING", "required": True},
                 {"key": "version", "name": "版本号", "type": "STRING", "required": True, "placeholder": "v2.3.1"},
                 {"key": "env", "name": "部署环境", "type": "SELECT", "required": True,
                  "choice": [{"value": "staging", "label": "预发布"}, {"value": "prod", "label": "生产"}]},
                 {"key": "changelog", "name": "变更日志", "type": "TEXT", "required": True},
             ]},
            {"name": "配置变更", "description": "修改应用配置项，支持批量推送和灰度发布", "icon": "⚙️",
             "mode": "flow", "cat": "app-support", "duration": "1-2 小时", "sort": 50,
             "fields": [
                 {"key": "app_name", "name": "应用名称", "type": "STRING", "required": True},
                 {"key": "config_key", "name": "配置项", "type": "STRING", "required": True},
                 {"key": "config_value", "name": "新值", "type": "TEXT", "required": True},
             ]},
            {"name": "日志查询", "description": "查询应用服务器实时或历史日志，支持关键字过滤和时间范围", "icon": "📋",
             "mode": "lightweight", "cat": "app-support", "duration": "10 分钟", "sort": 60,
             "fields": [
                 {"key": "hostname", "name": "服务器", "type": "STRING", "required": True},
                 {"key": "keyword", "name": "关键字", "type": "STRING", "placeholder": "可选"},
                 {"key": "time_range", "name": "时间范围", "type": "SELECT",
                  "choice": [{"value": "1h", "label": "最近 1 小时"}, {"value": "6h", "label": "最近 6 小时"}, {"value": "24h", "label": "最近 24 小时"}]},
             ]},
            {"name": "申请数据库", "description": "申请 MySQL/Redis/MongoDB 实例，指定规格、存储和网络配置", "icon": "🗄️",
             "mode": "flow", "cat": "db-ops", "duration": "1-2 工作日", "sort": 70,
             "fields": [
                 {"key": "db_type", "name": "数据库类型", "type": "SELECT", "required": True,
                  "choice": [{"value": "mysql", "label": "MySQL"}, {"value": "redis", "label": "Redis"}, {"value": "mongo", "label": "MongoDB"}]},
                 {"key": "spec", "name": "规格", "type": "SELECT", "required": True,
                  "choice": [{"value": "2c4g", "label": "2C4G"}, {"value": "4c8g", "label": "4C8G"}, {"value": "8c16g", "label": "8C16G"}]},
                 {"key": "storage_gb", "name": "存储 (GB)", "type": "INT", "required": True},
             ]},
            {"name": "数据库备份", "description": "手动触发数据库备份，支持全量备份和增量备份", "icon": "💿",
             "mode": "lightweight", "cat": "db-ops", "duration": "按数据量", "sort": 80,
             "fields": [
                 {"key": "instance", "name": "实例", "type": "STRING", "required": True},
                 {"key": "backup_type", "name": "备份类型", "type": "SELECT",
                  "choice": [{"value": "full", "label": "全量备份"}, {"value": "incremental", "label": "增量备份"}]},
             ]},
            {"name": "VPN 申请", "description": "申请 VPN 账号用于远程接入内网，需审批并分配权限组", "icon": "🔒",
             "mode": "flow", "cat": "network-ops", "duration": "1 工作日", "sort": 90,
             "fields": [
                 {"key": "username", "name": "用户名", "type": "STRING", "required": True},
                 {"key": "group", "name": "权限组", "type": "SELECT", "required": True,
                  "choice": [{"value": "dev", "label": "开发组"}, {"value": "ops", "label": "运维组"}, {"value": "admin", "label": "管理员"}]},
                 {"key": "reason", "name": "申请理由", "type": "TEXT", "required": True},
             ]},
            {"name": "防火墙策略", "description": "申请新增或修改防火墙规则，指定源/目标 IP、端口和协议", "icon": "🛡️",
             "mode": "flow", "cat": "network-ops", "duration": "1-2 工作日", "sort": 100,
             "fields": [
                 {"key": "source_ip", "name": "源 IP", "type": "STRING", "required": True},
                 {"key": "dest_ip", "name": "目标 IP", "type": "STRING", "required": True},
                 {"key": "port", "name": "端口", "type": "STRING", "required": True, "placeholder": "例如: 80, 443"},
                 {"key": "protocol", "name": "协议", "type": "SELECT",
                  "choice": [{"value": "tcp", "label": "TCP"}, {"value": "udp", "label": "UDP"}, {"value": "icmp", "label": "ICMP"}]},
             ]},
            {"name": "重置密码", "description": "重置服务器或系统账号密码，需要申请人和审批人双方确认", "icon": "🔑",
             "mode": "lightweight", "cat": None, "duration": "30 分钟", "sort": 110,
             "fields": [
                 {"key": "account", "name": "账号", "type": "STRING", "required": True},
                 {"key": "system", "name": "所属系统", "type": "STRING", "required": True},
             ]},
            {"name": "软件授权申请", "description": "申请商业软件授权许可，需提供用途说明和使用期限", "icon": "📜",
             "mode": "flow", "cat": None, "duration": "3-5 工作日", "sort": 120,
             "fields": [
                 {"key": "software", "name": "软件名称", "type": "STRING", "required": True},
                 {"key": "license_type", "name": "授权类型", "type": "SELECT",
                  "choice": [{"value": "trial", "label": "试用"}, {"value": "annual", "label": "年度订阅"}, {"value": "perpetual", "label": "永久授权"}]},
                 {"key": "users", "name": "使用人数", "type": "INT", "required": True},
             ]},
        ]

        for item in items:
            cat_code = item.pop("cat", None)
            category = self.cat_map.get(cat_code) if cat_code else None
            fields = item.pop("fields", [])
            duration = item.pop("duration", "")
            sort = item.pop("sort", 0)

            wf = None
            if item["mode"] == "flow" and self.wf_list:
                if category:
                    for w in self.wf_list:
                        if category.name.lower() in w.name.lower() or w.name.lower() in category.name.lower():
                            wf = w
                            break
                if not wf:
                    wf = self.wf_list[0]

            obj, created = ServiceItem.objects.get_or_create(
                name=item["name"],
                defaults={
                    "description": item.get("description", ""),
                    "icon": item.get("icon", "📋"),
                    "mode": item["mode"],
                    "category": category,
                    "workflow": wf,
                    "form_fields": fields,
                    "expected_duration": duration,
                    "sort_order": sort,
                    "is_active": True,
                    "project_id": self._pid,
                },
            )
            if created:
                self.stdout.write(f"  + {item['name']}")
            elif self.force:
                obj.description = item.get("description", "")
                obj.icon = item.get("icon", "📋")
                obj.mode = item["mode"]
                obj.category = category
                obj.workflow = wf
                obj.form_fields = fields
                obj.expected_duration = duration
                obj.sort_order = sort
                obj.save(update_fields=[
                    "description", "icon", "mode", "category",
                    "workflow", "form_fields", "expected_duration", "sort_order",
                ])

        self.stdout.write(f"  + {ServiceItem.objects.count()} items total")
