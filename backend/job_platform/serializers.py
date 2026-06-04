# -*- coding: utf-8 -*-
"""Serializers for job_platform app — 所有模型序列化器"""

from dvadmin.utils.serializers import CustomModelSerializer

from .models.subs.base import Account, FileSource, DangerousCmdRule, DangerousCheckLog
from .models.subs.script import Script, ScriptVersion, ScriptReference
from .models.subs.template import Template, Plan, Variable
from .models.subs.step import Step, ScriptStep, FileStep, ApprovalStep
from .models.subs.execution import JobExecution, StepExecution
from .models.subs.cron import CronJob, CronJobExecution

# ─── Account ───
class AccountSerializer(CustomModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"
        read_only_fields = ['id', 'create_datetime', 'update_datetime']

class AccountCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"

# ─── FileSource ───
class FileSourceSerializer(CustomModelSerializer):
    class Meta:
        model = FileSource
        fields = "__all__"

# ─── Script ───
class ScriptSerializer(CustomModelSerializer):
    class Meta:
        model = Script
        fields = "__all__"
        read_only_fields = ['id', 'create_datetime', 'update_datetime']

class ScriptCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Script
        fields = "__all__"

class ScriptVersionSerializer(CustomModelSerializer):
    class Meta:
        model = ScriptVersion
        fields = "__all__"

class ScriptReferenceSerializer(CustomModelSerializer):
    class Meta:
        model = ScriptReference
        fields = "__all__"

# ─── Template / Plan / Variable ───
class TemplateSerializer(CustomModelSerializer):
    class Meta:
        model = Template
        fields = "__all__"
        read_only_fields = ['id', 'create_datetime', 'update_datetime']

class TemplateCreateUpdateSerializer(CustomModelSerializer):
    class Meta:
        model = Template
        fields = "__all__"

class PlanSerializer(CustomModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"

class VariableSerializer(CustomModelSerializer):
    class Meta:
        model = Variable
        fields = "__all__"

# ─── Step ───
class StepSerializer(CustomModelSerializer):
    class Meta:
        model = Step
        fields = "__all__"

class ScriptStepSerializer(CustomModelSerializer):
    class Meta:
        model = ScriptStep
        fields = "__all__"

class FileStepSerializer(CustomModelSerializer):
    class Meta:
        model = FileStep
        fields = "__all__"

class ApprovalStepSerializer(CustomModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = "__all__"

# ─── Execution ───
class JobExecutionSerializer(CustomModelSerializer):
    class Meta:
        model = JobExecution
        fields = "__all__"
        read_only_fields = ['status', 'start_time', 'end_time', 'result_summary']

class StepExecutionSerializer(CustomModelSerializer):
    class Meta:
        model = StepExecution
        fields = "__all__"

class JobExecutionDetailSerializer(CustomModelSerializer):
    """执行详情 — 包含步骤执行记录"""
    step_executions = StepExecutionSerializer(many=True, read_only=True)

    class Meta:
        model = JobExecution
        fields = "__all__"

# ─── Dangerous ───
class DangerousCmdRuleSerializer(CustomModelSerializer):
    class Meta:
        model = DangerousCmdRule
        fields = "__all__"

class DangerousCheckLogSerializer(CustomModelSerializer):
    class Meta:
        model = DangerousCheckLog
        fields = "__all__"

# ─── Cron ───
class CronJobSerializer(CustomModelSerializer):
    class Meta:
        model = CronJob
        fields = "__all__"

class CronJobExecutionSerializer(CustomModelSerializer):
    class Meta:
        model = CronJobExecution
        fields = "__all__"
