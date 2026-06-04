"""ITSM piplework workflow engine mock data generator

Usage:
    python manage.py add_itsm_mock_data              # Add mock data (idempotent)
    python manage.py add_itsm_mock_data --force       # Force update
"""

import datetime
import json

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

SAMPLE_WORKFLOWS = [
    {
        "name": "服务器采购审批流程",
        "itsm_type": "change",
        "description": "服务器采购需经主管→财务→总监三级审批",
        "states": [
            {"name": "填写采购申请", "type": "NORMAL", "is_builtin": True, "processors_type": "STARTER",
             "fields": [
                {"key": "server_model", "name": "服务器型号", "type": "STRING", "required": True},
                {"key": "quantity", "name": "采购数量", "type": "INT", "required": True},
                {"key": "budget", "name": "预算(元)", "type": "INT", "required": True},
                {"key": "purpose", "name": "采购用途", "type": "TEXT", "required": True},
            ]},
            {"name": "主管审批", "type": "APPROVAL", "processors_type": "STARTER_LEADER",
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "通过", "value": "true"}, {"label": "拒绝", "value": "false"}]},
                        {"key": "approve_comment", "name": "审批意见", "type": "TEXT"}]},
            {"name": "财务审批", "type": "APPROVAL", "processors_type": "ROLE", "processors": json.dumps(["财务主管"]),
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "通过", "value": "true"}, {"label": "拒绝", "value": "false"}]},
                        {"key": "approve_comment", "name": "审批意见", "type": "TEXT"}]},
            {"name": "总监审批", "type": "APPROVAL", "processors_type": "ROLE", "processors": json.dumps(["技术总监"]),
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "通过", "value": "true"}, {"label": "拒绝", "value": "false"}]}]},
            {"name": "自动采购执行", "type": "TASK"},
            {"name": "开始", "type": "START", "is_builtin": True},
            {"name": "结束", "type": "END", "is_builtin": True},
        ],
        "transitions": [
            ("开始", "填写采购申请"), ("填写采购申请", "主管审批"),
            ("主管审批", "财务审批", {"approve_result": {"eq": "true"}}), ("主管审批", "结束", {"approve_result": {"eq": "false"}}),
            ("财务审批", "总监审批", {"approve_result": {"eq": "true"}}), ("财务审批", "结束", {"approve_result": {"eq": "false"}}),
            ("总监审批", "自动采购执行", {"approve_result": {"eq": "true"}}), ("总监审批", "结束", {"approve_result": {"eq": "false"}}),
            ("自动采购执行", "结束"),
        ],
    },
    {
        "name": "线上紧急变更流程",
        "itsm_type": "change",
        "description": "紧急变更需值班主管审批→自动执行→测试验证",
        "states": [
            {"name": "填写紧急变更单", "type": "NORMAL", "is_builtin": True, "processors_type": "STARTER",
             "fields": [
                {"key": "title", "name": "变更标题", "type": "STRING", "required": True},
                {"key": "reason", "name": "变更原因", "type": "TEXT", "required": True},
                {"key": "risk_level", "name": "风险等级", "type": "SELECT", "required": True,
                 "choice": [{"label": "低", "value": "low"}, {"label": "中", "value": "medium"}, {"label": "高", "value": "high"}]},
                {"key": "change_plan", "name": "变更方案", "type": "RICHTEXT", "required": True},
            ]},
            {"name": "值班主管审批", "type": "APPROVAL", "processors_type": "ROLE", "processors": json.dumps(["值班主管"]),
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "紧急批准", "value": "true"}, {"label": "驳回", "value": "false"}]}]},
            {"name": "自动执行变更", "type": "TASK"},
            {"name": "测试验证", "type": "NORMAL", "processors_type": "PERSON", "processors": json.dumps(["tester"]),
             "fields": [{"key": "test_result", "name": "验证结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "通过", "value": "passed"}, {"label": "失败", "value": "failed"}]}]},
            {"name": "开始", "type": "START", "is_builtin": True},
            {"name": "结束", "type": "END", "is_builtin": True},
        ],
        "transitions": [
            ("开始", "填写紧急变更单"), ("填写紧急变更单", "值班主管审批"),
            ("值班主管审批", "自动执行变更", {"approve_result": {"eq": "true"}}),
            ("值班主管审批", "结束", {"approve_result": {"eq": "false"}}),
            ("自动执行变更", "测试验证"), ("测试验证", "结束"),
        ],
    },
    {
        "name": "事件处理流程",
        "itsm_type": "incident",
        "description": "事件工单处理流程：上报→分派→处理→验证关闭",
        "states": [
            {"name": "上报事件", "type": "NORMAL", "is_builtin": True, "processors_type": "STARTER",
             "fields": [
                {"key": "event_title", "name": "事件标题", "type": "STRING", "required": True},
                {"key": "severity", "name": "严重级别", "type": "SELECT", "required": True,
                 "choice": [{"label": "严重", "value": "critical"}, {"label": "高", "value": "high"},
                            {"label": "中", "value": "medium"}, {"label": "低", "value": "low"}]},
                {"key": "event_desc", "name": "事件描述", "type": "TEXT", "required": True},
            ]},
            {"name": "值班分派", "type": "NORMAL", "processors_type": "ROLE", "processors": json.dumps(["值班主管"]),
             "fields": [{"key": "assignee", "name": "指派处理人", "type": "STRING", "required": True},
                        {"key": "priority", "name": "优先级", "type": "SELECT", "required": True,
                         "choice": [{"label": "P1", "value": "P1"}, {"label": "P2", "value": "P2"},
                                    {"label": "P3", "value": "P3"}, {"label": "P4", "value": "P4"}]}]},
            {"name": "事件处理", "type": "NORMAL", "processors_type": "VARIABLE", "processors": "assignee",
             "fields": [{"key": "root_cause", "name": "根因分析", "type": "TEXT", "required": True},
                        {"key": "resolution", "name": "解决方案", "type": "TEXT", "required": True}]},
            {"name": "验证关闭", "type": "NORMAL", "processors_type": "STARTER",
             "fields": [{"key": "confirm", "name": "确认关闭", "type": "RADIO", "required": True,
                         "choice": [{"label": "确认关闭", "value": "closed"}, {"label": "仍需处理", "value": "reopen"}]}]},
            {"name": "开始", "type": "START", "is_builtin": True},
            {"name": "结束", "type": "END", "is_builtin": True},
        ],
        "transitions": [
            ("开始", "上报事件"), ("上报事件", "值班分派"), ("值班分派", "事件处理"),
            ("事件处理", "验证关闭"),
            ("验证关闭", "结束", {"confirm": {"eq": "closed"}}),
            ("验证关闭", "事件处理", {"confirm": {"eq": "reopen"}}),
        ],
    },
    {
        "name": "数据库变更审批流程",
        "itsm_type": "change",
        "description": "数据库结构变更需 DBA 审批",
        "states": [
            {"name": "提交 SQL 变更", "type": "NORMAL", "is_builtin": True, "processors_type": "STARTER",
             "fields": [
                {"key": "db_name", "name": "数据库名", "type": "STRING", "required": True},
                {"key": "sql_content", "name": "SQL 内容", "type": "TEXT", "required": True},
                {"key": "rollback_sql", "name": "回滚 SQL", "type": "TEXT"},
            ]},
            {"name": "DBA 审批", "type": "APPROVAL", "processors_type": "ROLE", "processors": json.dumps(["DBA"]),
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "批准执行", "value": "true"}, {"label": "驳回", "value": "false"}]}]},
            {"name": "自动执行 SQL", "type": "TASK"},
            {"name": "开始", "type": "START", "is_builtin": True},
            {"name": "结束", "type": "END", "is_builtin": True},
        ],
        "transitions": [
            ("开始", "提交 SQL 变更"), ("提交 SQL 变更", "DBA 审批"),
            ("DBA 审批", "自动执行 SQL", {"approve_result": {"eq": "true"}}),
            ("DBA 审批", "结束", {"approve_result": {"eq": "false"}}),
            ("自动执行 SQL", "结束"),
        ],
    },
    {
        "name": "权限申请审批流程",
        "itsm_type": "request",
        "description": "服务器权限申请需主管审批",
        "states": [
            {"name": "填写权限申请", "type": "NORMAL", "is_builtin": True, "processors_type": "STARTER",
             "fields": [
                {"key": "app_name", "name": "应用名称", "type": "STRING", "required": True},
                {"key": "server_ip", "name": "服务器 IP", "type": "STRING", "required": True},
                {"key": "permission_type", "name": "权限类型", "type": "SELECT", "required": True,
                 "choice": [{"label": "sudo", "value": "sudo"}, {"label": "readonly", "value": "readonly"},
                            {"label": "admin", "value": "admin"}]},
                {"key": "reason", "name": "申请原因", "type": "TEXT", "required": True},
            ]},
            {"name": "主管审批", "type": "APPROVAL", "processors_type": "STARTER_LEADER",
             "fields": [{"key": "approve_result", "name": "审批结果", "type": "RADIO", "required": True,
                         "choice": [{"label": "批准", "value": "true"}, {"label": "拒绝", "value": "false"}]}]},
            {"name": "自动授权", "type": "TASK"},
            {"name": "开始", "type": "START", "is_builtin": True},
            {"name": "结束", "type": "END", "is_builtin": True},
        ],
        "transitions": [
            ("开始", "填写权限申请"), ("填写权限申请", "主管审批"),
            ("主管审批", "自动授权", {"approve_result": {"eq": "true"}}),
            ("主管审批", "结束", {"approve_result": {"eq": "false"}}),
            ("自动授权", "结束"),
        ],
    },
]

TICKET_SAMPLES = [
    {"title": "采购 2 台 PowerEdge R750 服务器", "wf_name": "服务器采购审批流程", "priority": "P3"},
    {"title": "紧急修复支付网关连接超时", "wf_name": "线上紧急变更流程", "priority": "P1"},
    {"title": "数据库索引优化变更", "wf_name": "数据库变更审批流程", "priority": "P3"},
    {"title": "申请生产环境 sudo 权限", "wf_name": "权限申请审批流程", "priority": "P3"},
    {"title": "磁盘容量告警处理", "wf_name": "事件处理流程", "priority": "P2"},
]


class Command(BaseCommand):
    help = "Generate ITSM pipeline workflow engine mock data"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update')

    def handle(self, *args, **options):
        force = options.get('force', False)
        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin:
            self.stderr.write("No users found")
            return

        self._create_priority_matrix()
        self._create_workflows(admin, force)
        self._create_tickets(admin)

    def _create_priority_matrix(self):
        from itsm.models import PriorityMatrix
        matrix_defs = [
            ("change", "高", "大", "P1"), ("change", "高", "中", "P1"), ("change", "高", "小", "P2"),
            ("change", "中", "大", "P1"), ("change", "中", "中", "P2"), ("change", "中", "小", "P3"),
            ("change", "低", "大", "P2"), ("change", "低", "中", "P3"), ("change", "低", "小", "P4"),
            ("incident", "高", "大", "P1"), ("incident", "高", "中", "P1"), ("incident", "高", "小", "P2"),
            ("incident", "中", "大", "P1"), ("incident", "中", "中", "P2"), ("incident", "中", "小", "P3"),
            ("incident", "低", "大", "P2"), ("incident", "低", "中", "P3"), ("incident", "低", "小", "P4"),
        ]
        count = 0
        for itsm_type, urgency, impact, priority in matrix_defs:
            _, created = PriorityMatrix.objects.get_or_create(
                itsm_type=itsm_type, urgency=urgency, impact=impact, defaults={"priority": priority},
            )
            if created:
                count += 1
        self.stdout.write(f"  + {count} PriorityMatrix entries")

    def _create_workflows(self, admin, force):
        from itsm.models import Workflow, WorkflowVersion, State, Transition, Field

        wf_count = st_count = tr_count = fi_count = vr_count = 0

        for wf_def in SAMPLE_WORKFLOWS:
            wf, created = Workflow.objects.get_or_create(
                name=wf_def["name"],
                defaults={
                    "itsm_type": wf_def["itsm_type"],
                    "description": wf_def.get("description", ""),
                    "is_draft": False, "is_enabled": True,
                    "created_by": admin.username,
                },
            )
            if created or force:
                wf_count += 1

            state_map = {}
            for sdef in wf_def["states"]:
                state, sc = State.objects.get_or_create(
                    workflow=wf,
                    name=sdef["name"],
                    defaults={
                        "type": sdef["type"],
                        "is_builtin": sdef.get("is_builtin", False),
                        "processors_type": sdef.get("processors_type", "PERSON"),
                        "processors": sdef.get("processors", ""),
                        "fields": sdef.get("fields", []),
                    },
                )
                state_map[sdef["name"]] = state
                if sc:
                    st_count += 1

                for fdef in sdef.get("fields", []):
                    _, fc = Field.objects.get_or_create(
                        state=state,
                        key=fdef["key"],
                        defaults={
                            "name": fdef["name"], "type": fdef["type"],
                            "required": fdef.get("required", False),
                            "choice": fdef.get("choice", []),
                        },
                    )
                    if fc:
                        fi_count += 1

            for tdef in wf_def["transitions"]:
                from_s = state_map.get(tdef[0])
                to_s = state_map.get(tdef[1])
                if from_s and to_s:
                    condition = tdef[2] if len(tdef) > 2 else {}
                    _, tc = Transition.objects.get_or_create(
                        workflow=wf,
                        from_state=from_s,
                        to_state=to_s,
                        defaults={
                            "condition": condition,
                            "condition_type": "branch" if condition else "default",
                        },
                    )
                    if tc:
                        tr_count += 1

            if created or force:
                wf.create_version(operator=admin.username, message="Mock deploy")
                vr_count += 1

        self.stdout.write(f"  + {wf_count} Workflows + {st_count} States + {tr_count} Transitions")
        self.stdout.write(f"  + {fi_count} Fields + {vr_count} Versions")

    def _create_tickets(self, admin):
        from itsm.models import Workflow, WorkflowVersion, Ticket

        count = 0
        for ts in TICKET_SAMPLES:
            wf = Workflow.objects.filter(name=ts["wf_name"]).first()
            if not wf:
                self.stdout.write(f"    Workflow not found: {ts['wf_name']}")
                continue
            wv = WorkflowVersion.objects.filter(workflow=wf).first()
            if not wv:
                continue
            ticket, created = Ticket.objects.get_or_create(
                title=ts["title"],
                workflow_version=wv,
                defaults={
                    "itsm_type": wf.itsm_type,
                    "priority": ts["priority"],
                    "current_status": "draft",
                    "creator": admin.username,
                    "meta": {"source": "mock_data"},
                },
            )
            if created:
                count += 1
                ticket.do_after_create()

        self.stdout.write(f"  + {count} Tickets (draft, ready to submit)")
