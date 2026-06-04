"""Job platform views — Script, JobDefinition, JobExecution, DangerousCmdRule
"""

import uuid
from datetime import datetime

from rest_framework.decorators import action
from django.utils import timezone

from dvadmin.utils.viewset import CustomModelViewSet
from dvadmin.utils.json_response import DetailResponse, ErrorResponse

from ..models.models import Script, JobDefinition, JobExecution, DangerousCmdRule
from ..serializers import (
    ScriptSerializer, ScriptCreateUpdateSerializer,
    JobDefinitionSerializer, JobDefinitionCreateUpdateSerializer,
    JobExecutionSerializer, JobExecutionDetailSerializer,
    DangerousCmdRuleSerializer,
)
from ..services.executor import execute_job
from ..services.dangerous_cmd import check_dangerous_command

FSM = 'job_platform_views'


class ScriptViewSet(CustomModelViewSet):
    """脚本管理 CRUD"""
    model = Script
    queryset = Script.objects.all()
    serializer_class = ScriptSerializer
    create_serializer_class = ScriptCreateUpdateSerializer
    update_serializer_class = ScriptCreateUpdateSerializer
    filter_fields = ['script_type', 'is_public', 'is_builtin']
    search_fields = ['name', 'description']
    ordering = ['-create_datetime']


class JobDefinitionViewSet(CustomModelViewSet):
    """作业定义 CRUD"""
    model = JobDefinition
    queryset = JobDefinition.objects.all()
    serializer_class = JobDefinitionSerializer
    create_serializer_class = JobDefinitionCreateUpdateSerializer
    update_serializer_class = JobDefinitionCreateUpdateSerializer
    filter_fields = ['executor', 'need_approval']
    search_fields = ['name', 'description']
    ordering = ['-create_datetime']

    @action(methods=['POST'], detail=True)
    def run(self, request, pk=None):
        """执行作业"""
        job_def = self.get_object()
        target_hosts = request.data.get('target_hosts', [])
        params = request.data.get('params', {})

        if not target_hosts:
            return ErrorResponse(msg='请指定目标主机')

        # 检查高危命令
        command = job_def.command or (job_def.script.content if job_def.script else '')
        check_result = check_dangerous_command(command)
        if check_result.get('blocked'):
            return ErrorResponse(msg=f"命令被拦截: {check_result.get('reason', '')}")

        # 创建执行记录
        execution = JobExecution.objects.create(
            job=job_def,
            status='pending',
            target_hosts=target_hosts,
            params=params,
            executor=job_def.executor,
            run_as=job_def.run_as,
        )

        # 异步执行（Celery 或直接执行）
        from ..services.executor import async_execute_job
        async_execute_job(execution.id)

        return DetailResponse(
            data={'execution_id': execution.id, 'status': execution.status},
            msg='作业已提交执行'
        )


class JobExecutionViewSet(CustomModelViewSet):
    """作业执行记录 — 只读 + 取消"""
    model = JobExecution
    queryset = JobExecution.objects.all()
    serializer_class = JobExecutionSerializer
    filter_fields = ['status', 'executor', 'job']
    search_fields = ['result_summary', 'error_message']
    ordering = ['-create_datetime']

    def retrieve(self, request, *args, **kwargs):
        """详情包含完整结果"""
        instance = self.get_object()
        serializer = JobExecutionDetailSerializer(instance)
        return DetailResponse(data=serializer.data)

    @action(methods=['POST'], detail=True)
    def cancel(self, request, pk=None):
        """取消执行"""
        instance = self.get_object()
        if instance.status in ('running', 'pending'):
            instance.status = 'cancelled'
            instance.finished_at = timezone.now()
            instance.save(update_fields=['status', 'finished_at'])
            return DetailResponse(msg='已取消')
        return ErrorResponse(msg=f'当前状态({instance.status})不允许取消')

    @action(methods=['GET'], detail=True)
    def log(self, request, pk=None):
        """获取执行日志"""
        instance = self.get_object()
        return DetailResponse(data={
            'execution_id': instance.id,
            'status': instance.status,
            'log': instance.result_detail,
        })


class DangerousCmdRuleViewSet(CustomModelViewSet):
    """高危命令规则 CRUD"""
    model = DangerousCmdRule
    queryset = DangerousCmdRule.objects.all()
    serializer_class = DangerousCmdRuleSerializer
    filter_fields = ['action', 'severity', 'is_active']
    search_fields = ['name', 'pattern']
    ordering = ['-create_datetime']
