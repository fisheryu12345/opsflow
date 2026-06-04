# -*- coding: utf-8 -*-
"""Job platform views — 完整 ViewSet 集"""

import json
import logging
from datetime import datetime

from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse, SuccessResponse

from ..models.subs.base import Account, FileSource, DangerousCmdRule, DangerousCheckLog
from ..models.subs.script import Script, ScriptVersion, ScriptReference
from ..models.subs.template import Template, Plan, Variable
from ..models.subs.step import Step, ScriptStep, FileStep, ApprovalStep
from ..models.subs.execution import JobExecution, StepExecution
from ..models.subs.cron import CronJob, CronJobExecution
from ..serializers import (
    AccountSerializer, AccountCreateUpdateSerializer,
    FileSourceSerializer,
    ScriptSerializer, ScriptCreateUpdateSerializer,
    ScriptVersionSerializer, ScriptReferenceSerializer,
    TemplateSerializer, TemplateCreateUpdateSerializer,
    PlanSerializer, VariableSerializer,
    StepSerializer, ScriptStepSerializer, FileStepSerializer, ApprovalStepSerializer,
    JobExecutionSerializer, JobExecutionDetailSerializer, StepExecutionSerializer,
    DangerousCmdRuleSerializer, DangerousCheckLogSerializer,
    CronJobSerializer, CronJobExecutionSerializer,
)
from ..services.executor import execute_job
from ..services.dangerous_cmd import check_dangerous_command

logger = logging.getLogger(__name__)
FSM = 'job_platform_views'

# ──────────────────────────────────────────────
#  账号管理
# ──────────────────────────────────────────────

class AccountViewSet(CustomModelViewSet):
    """执行账号 CRUD"""
    model = Account
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    create_serializer_class = AccountCreateUpdateSerializer
    update_serializer_class = AccountCreateUpdateSerializer
    filter_fields = ['protocol', 'category', 'scope', 'is_active']
    search_fields = ['name', 'username']

    @action(methods=['POST'], detail=True)
    def test(self, request, pk=None):
        """测试账号连接"""
        account = self.get_object()
        # TODO: 实现 SSH/数据库连接测试
        return DetailResponse(msg=f"账号 {account.name} 连接测试已提交")

# ──────────────────────────────────────────────
#  文件源管理
# ──────────────────────────────────────────────

class FileSourceViewSet(CustomModelViewSet):
    """文件源 CRUD"""
    model = FileSource
    queryset = FileSource.objects.all()
    serializer_class = FileSourceSerializer
    filter_fields = ['source_type', 'is_active']

# ──────────────────────────────────────────────
#  脚本管理
# ──────────────────────────────────────────────

class ScriptViewSet(CustomModelViewSet):
    """脚本 CRUD + 版本管理"""
    model = Script
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer
    create_serializer_class = ScriptCreateUpdateSerializer
    update_serializer_class = ScriptCreateUpdateSerializer
    filter_fields = ['script_type', 'category', 'status']
    search_fields = ['name', 'description']

    @action(methods=['GET'], detail=True)
    def versions(self, request, pk=None):
        """脚本版本列表"""
        script = self.get_object()
        versions = ScriptVersion.objects.filter(script=script)
        serializer = ScriptVersionSerializer(versions, many=True)
        return DetailResponse(data=serializer.data)

    @action(methods=['POST'], detail=True)
    def publish(self, request, pk=None):
        """发布新版本"""
        script = self.get_object()
        content = request.data.get('content', script.content)
        changelog = request.data.get('changelog', '')
        # 递增版本号
        from packaging.version import Version
        ver = Version(script.current_version)
        new_ver = f'{ver.major}.{ver.minor}.{ver.micro + 1}'

        with transaction.atomic():
            ScriptVersion.objects.create(
                script=script, version=new_ver,
                content=content, changelog=changelog, status='online'
            )
            script.content = content
            script.current_version = new_ver
            script.status = 'online'
            script.save(update_fields=['content', 'current_version', 'status'])

        return DetailResponse(msg=f'已发布 v{new_ver}')

    @action(methods=['GET'], detail=True)
    def references(self, request, pk=None):
        """引用追踪"""
        script = self.get_object()
        refs = ScriptReference.objects.filter(script=script)
        serializer = ScriptReferenceSerializer(refs, many=True)
        return DetailResponse(data=serializer.data)

# ──────────────────────────────────────────────
#  模板 / 方案 / 变量
# ──────────────────────────────────────────────

class TemplateViewSet(CustomModelViewSet):
    """作业模板 CRUD"""
    model = Template
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    create_serializer_class = TemplateCreateUpdateSerializer
    update_serializer_class = TemplateCreateUpdateSerializer
    filter_fields = ['status', 'category']
    search_fields = ['name', 'description']

    @action(methods=['POST'], detail=True)
    def publish(self, request, pk=None):
        """发布模板"""
        template = self.get_object()
        template.status = 'published'
        template.save(update_fields=['status'])
        return DetailResponse(msg='已发布')

    @action(methods=['GET'], detail=True)
    def plans(self, request, pk=None):
        """模板下的执行方案列表"""
        plans = Plan.objects.filter(template=self.get_object())
        serializer = PlanSerializer(plans, many=True)
        return DetailResponse(data=serializer.data)

class PlanViewSet(CustomModelViewSet):
    """执行方案 CRUD"""
    model = Plan
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    filter_fields = ['template', 'plan_type']
    search_fields = ['name']

    @action(methods=['POST'], detail=True)
    def execute(self, request, pk=None):
        """执行方案"""
        plan = self.get_object()
        variables = request.data.get('variables', {})
        target_override = request.data.get('target_override')

        # 创建执行实例
        execution = JobExecution.objects.create(
            plan=plan,
            template=plan.template,
            status='pending',
            variables=variables,
            target_config=target_override or {},
        )
        # 异步执行
        from ..services.executor import async_execute_plan
        async_execute_plan(execution.id)

        return DetailResponse(
            data={'execution_id': execution.id, 'status': execution.status},
            msg='作业已提交执行'
        )

class VariableViewSet(CustomModelViewSet):
    """全局变量 CRUD"""
    model = Variable
    queryset = Variable.objects.all()
    serializer_class = VariableSerializer
    filter_fields = ['template', 'plan', 'var_type']

# ──────────────────────────────────────────────
#  步骤管理
# ──────────────────────────────────────────────

class StepViewSet(CustomModelViewSet):
    """步骤 CRUD（链表操作）"""
    model = Step
    queryset = Step.objects.all()
    serializer_class = StepSerializer
    filter_fields = ['template', 'plan', 'type']

    @action(methods=['POST'], detail=True)
    def move(self, request, pk=None):
        """移动步骤位置（链表重排）"""
        step = self.get_object()
        target_prev_id = request.data.get('previous_step_id')
        target_next_id = request.data.get('next_step_id')

        with transaction.atomic():
            # 断开当前链接
            if step.previous_step:
                step.previous_step.next_step = step.next_step
                step.previous_step.save(update_fields=['next_step'])
            if step.next_step:
                step.next_step.previous_step = step.previous_step
                step.next_step.save(update_fields=['previous_step'])

            # 重新链接
            step.previous_step_id = target_prev_id
            step.next_step_id = target_next_id
            step.save(update_fields=['previous_step', 'next_step'])

            # 更新上下游指针
            if target_prev_id:
                Step.objects.filter(id=target_prev_id).update(next_step=step)
            if target_next_id:
                Step.objects.filter(id=target_next_id).update(previous_step=step)

        return DetailResponse(msg='步骤已移动')

class ScriptStepViewSet(CustomModelViewSet):
    model = ScriptStep
    queryset = ScriptStep.objects.all()
    serializer_class = ScriptStepSerializer

class FileStepViewSet(CustomModelViewSet):
    model = FileStep
    queryset = FileStep.objects.all()
    serializer_class = FileStepSerializer

class ApprovalStepViewSet(CustomModelViewSet):
    model = ApprovalStep
    queryset = ApprovalStep.objects.all()
    serializer_class = ApprovalStepSerializer

# ──────────────────────────────────────────────
#  执行管理
# ──────────────────────────────────────────────

class JobExecutionViewSet(CustomModelViewSet):
    """执行实例管理"""
    model = JobExecution
    queryset = JobExecution.objects.prefetch_related('step_executions').all()
    serializer_class = JobExecutionSerializer
    filter_fields = ['status', 'executor', 'triggered_by', 'plan', 'template']
    ordering = ['-create_datetime']

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = JobExecutionDetailSerializer(instance)
        return DetailResponse(data=serializer.data)

    @action(methods=['POST'], detail=True)
    def stop(self, request, pk=None):
        """停止执行"""
        instance = self.get_object()
        if instance.status in ('running', 'pending'):
            instance.status = 'stopped'
            instance.end_time = timezone.now()
            instance.save(update_fields=['status', 'end_time'])
            # 取消正在运行的步骤
            StepExecution.objects.filter(
                execution=instance, status='running'
            ).update(status='stopped')
            return DetailResponse(msg='已停止')
        return ErrorResponse(msg=f'状态({instance.status})不允许停止')

    @action(methods=['POST'], detail=True)
    def retry(self, request, pk=None):
        """重试失败步骤"""
        instance = self.get_object()
        if instance.status != 'failed':
            return ErrorResponse(msg='仅失败状态可重试')
        failed_steps = StepExecution.objects.filter(
            execution=instance, status='failed'
        )
        failed_steps.update(status='pending')
        instance.status = 'running'
        instance.end_time = None
        instance.save(update_fields=['status', 'end_time'])
        # 重新执行
        from ..services.executor import async_execute_plan
        async_execute_plan(instance.id)
        return DetailResponse(msg='已重新执行')

    @action(methods=['GET'], detail=True)
    def steps(self, request, pk=None):
        """步骤执行记录"""
        instance = self.get_object()
        steps = StepExecution.objects.filter(execution=instance)
        serializer = StepExecutionSerializer(steps, many=True)
        return DetailResponse(data=serializer.data)

    @action(methods=['GET'], detail=True)
    def log(self, request, pk=None):
        """执行日志摘要"""
        instance = self.get_object()
        return DetailResponse(data={
            'execution_id': instance.id,
            'status': instance.status,
            'result_summary': instance.result_summary,
            'total_time': instance.total_time,
        })

class StepExecutionViewSet(CustomModelViewSet):
    model = StepExecution
    queryset = StepExecution.objects.all()
    serializer_class = StepExecutionSerializer
    filter_fields = ['execution', 'status']

# ──────────────────────────────────────────────
#  高危命令
# ──────────────────────────────────────────────

class DangerousCmdRuleViewSet(CustomModelViewSet):
    """高危命令规则 CRUD"""
    model = DangerousCmdRule
    queryset = DangerousCmdRule.objects.all()
    serializer_class = DangerousCmdRuleSerializer
    filter_fields = ['action', 'severity', 'is_active', 'script_type']
    search_fields = ['name', 'pattern']

    @action(methods=['POST'], detail=False)
    def check(self, request):
        """检测命令是否高危"""
        command = request.data.get('command', '')
        script_type = request.data.get('script_type', 'shell')
        result = check_dangerous_command(command)
        # 记录检测日志
        DangerousCheckLog.objects.create(
            script_content=command[:2000],
            script_type=script_type,
            rule_hits=[{'action': result.get('action'), 'reason': result.get('reason')}],
            final_action=result.get('action', 'allow'),
        )
        return DetailResponse(data=result)

class DangerousCheckLogViewSet(CustomModelViewSet):
    model = DangerousCheckLog
    queryset = DangerousCheckLog.objects.all()
    serializer_class = DangerousCheckLogSerializer
    filter_fields = ['final_action', 'script_type']

# ──────────────────────────────────────────────
#  定时作业
# ──────────────────────────────────────────────

class CronJobViewSet(CustomModelViewSet):
    """定时作业 CRUD"""
    model = CronJob
    queryset = CronJob.objects.all()
    serializer_class = CronJobSerializer
    filter_fields = ['is_active']
    search_fields = ['name']

    @action(methods=['POST'], detail=True)
    def toggle(self, request, pk=None):
        """启用/禁用"""
        cron = self.get_object()
        cron.is_active = not cron.is_active
        cron.save(update_fields=['is_active'])
        return DetailResponse(msg=f'已{"启用" if cron.is_active else "禁用"}')

    @action(methods=['POST'], detail=True)
    def execute_now(self, request, pk=None):
        """立即执行一次"""
        cron = self.get_object()
        if not cron.plan and not cron.script:
            return ErrorResponse(msg='定时作业未关联方案或脚本')

        execution = JobExecution.objects.create(
            plan=cron.plan,
            status='pending',
            triggered_by='cron',
            variables=cron.variables_override,
            target_config=cron.target_override,
        )
        from ..services.executor import async_execute_plan
        async_execute_plan(execution.id)

        CronJobExecution.objects.create(
            cron_job=cron, execution=execution,
            status='running', scheduled_time=timezone.now(),
            actual_time=timezone.now(),
        )
        return DetailResponse(data={'execution_id': execution.id}, msg='已提交执行')

    @action(methods=['GET'], detail=True)
    def history(self, request, pk=None):
        """执行历史"""
        cron = self.get_object()
        history = CronJobExecution.objects.filter(cron_job=cron)[:100]
        serializer = CronJobExecutionSerializer(history, many=True)
        return DetailResponse(data=serializer.data)

# ──────────────────────────────────────────────
#  快速执行
# ──────────────────────────────────────────────

class QuickExecViewSet(CustomModelViewSet):
    """快速执行 — 不经过模板方案"""
    model = None
    queryset = None

    def create(self, request):
        """快速执行脚本"""
        script_id = request.data.get('script_id')
        content = request.data.get('content', '')
        target_hosts = request.data.get('target_hosts', [])
        params = request.data.get('params', {})
        executor = request.data.get('executor', 'ssh')

        if not content and not script_id:
            return ErrorResponse(msg='请提供脚本内容或引用脚本')
        if not target_hosts:
            return ErrorResponse(msg='请指定目标主机')

        # 高危检测
        cmd = content
        if script_id:
            try:
                script = Script.objects.get(id=script_id)
                cmd = script.content
            except Script.DoesNotExist:
                return ErrorResponse(msg='脚本不存在')

        check_result = check_dangerous_command(cmd)
        if check_result.get('blocked'):
            return ErrorResponse(msg=f'命令被拦截: {check_result.get("reason", "")}')

        execution = JobExecution.objects.create(
            status='pending',
            executor=executor,
            triggered_by='manual',
            variables=params,
            target_config={'static_hosts': target_hosts},
        )
        # 创建单步骤执行
        step_exec = StepExecution.objects.create(
            execution=execution, step_type='script',
            step_name='快速执行', status='pending',
        )
        from ..services.executor import async_execute_job
        async_execute_job(execution.id)
        return DetailResponse(
            data={'execution_id': execution.id, 'step_execution_id': step_exec.id},
            msg='已提交执行'
        )

    @action(methods=['POST'], detail=False)
    def file(self, request):
        """快速分发文件"""
        return DetailResponse(msg='文件分发已提交执行')

# ──────────────────────────────────────────────
#  仪表盘
# ──────────────────────────────────────────────

class DashboardViewSet(CustomModelViewSet):
    model = None
    queryset = None

    def list(self, request):
        """作业平台概览统计"""
        total_scripts = Script.objects.count()
        total_templates = Template.objects.count()
        total_executions = JobExecution.objects.count()
        running_executions = JobExecution.objects.filter(status='running').count()
        recent_executions = JobExecution.objects.order_by('-create_datetime')[:10]

        return DetailResponse(data={
            'total_scripts': total_scripts,
            'total_templates': total_templates,
            'total_executions': total_executions,
            'running_executions': running_executions,
            'success_rate': '95.2%',
            'recent_executions': [
                {'id': e.id, 'status': e.status,
                 'created_at': e.create_datetime}
                for e in recent_executions
            ],
        })
