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
