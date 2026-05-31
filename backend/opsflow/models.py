from django.db import models
from django.conf import settings


class FlowTemplate(models.Model):
    """编排模板 — AI 生成的或人工创建的流程定义"""
    name = models.CharField(max_length=200, verbose_name="Name")
    pipeline_tree = models.JSONField(default=dict, verbose_name="Pipeline Tree")
    target_hosts = models.JSONField(default=list, verbose_name="Target Hosts")
    global_vars = models.JSONField(default=dict, verbose_name="Global Variables")
    is_draft = models.BooleanField(default=True, verbose_name="Is Draft")
    ai_original_tree = models.JSONField(default=dict, verbose_name="AI Original Tree")
    category = models.CharField(max_length=64, blank=True, default='', verbose_name="Category")
    tags = models.JSONField(default=list, blank=True, verbose_name="Tags")
    description = models.CharField(max_length=500, blank=True, default='', verbose_name="Description")
    hook_variables = models.JSONField(default=dict, blank=True, verbose_name="Hook Variable Config")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_flow_template'
        ordering = ['-created_at']
        verbose_name = "Template"

    version = models.IntegerField(default=1, null=True, blank=True, verbose_name="Current Version")
    snapshot = models.JSONField(default=dict, null=True, blank=True, verbose_name="Published Snapshot")

    def publish_snapshot(self, user=None, version_note=""):
        """发布新版本：冻结当前 pipeline_tree 到 snapshot 并创建版本记录"""
        from django.utils import timezone
        # 处理旧模板 version 为 NULL 的情况
        if self.version is None:
            self.version = 1

        # 提取子流程引用信息（用于版本追踪）
        subprocess_refs = {}
        tree = self.pipeline_tree or {}
        for node in tree.get('nodes', []):
            if node.get('node_type') == 'subprocess':
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    try:
                        target = FlowTemplate.objects.get(id=target_id)
                        subprocess_refs[node['id']] = {
                            'target_template_id': target_id,
                            'target_version': target.version or 1,
                            'target_name': target.name,
                            'variable_mapping': params.get('variable_mapping', {}),
                            'output_mapping': params.get('output_mapping', {}),
                        }
                    except FlowTemplate.DoesNotExist:
                        subprocess_refs[node['id']] = {
                            'target_template_id': target_id,
                            'target_version': None,
                            'target_name': 'Unknown',
                        }

        self.snapshot = {
            'pipeline_tree': self.pipeline_tree,
            'target_hosts': self.target_hosts,
            'global_vars': self.global_vars,
            'subprocess_refs': subprocess_refs,
            'snapshot_at': timezone.now().isoformat(),
        }
        TemplateVersion.objects.create(
            template=self,
            version=self.version,
            pipeline_tree=self.pipeline_tree,
            target_hosts=self.target_hosts,
            global_vars=self.global_vars,
            version_note=version_note,
            created_by=self.created_by if user is None else user,
        )
        self.version += 1
        self.save()

    def __str__(self):
        return self.name


class TemplateVersion(models.Model):
    """模板版本历史 — 每次发布时创建"""
    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.CASCADE, related_name='versions',
        verbose_name="Template"
    )
    version = models.IntegerField(verbose_name="Version")
    pipeline_tree = models.JSONField(default=dict, verbose_name="Pipeline Tree")
    target_hosts = models.JSONField(default=list, verbose_name="Target Hosts")
    global_vars = models.JSONField(default=dict, verbose_name="Global Variables")
    version_note = models.CharField(max_length=256, blank=True, default='', verbose_name="Version Note")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_template_version'
        ordering = ['-version']
        unique_together = [('template', 'version')]
        verbose_name = "Template Version"

    def __str__(self):
        return f"{self.template.name} v{self.version}"


class FlowExecution(models.Model):
    """执行实例 — 一次流程运行记录"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    template = models.ForeignKey(
        FlowTemplate, on_delete=models.PROTECT, related_name='executions',
        verbose_name="Template"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name="Status"
    )
    node_status = models.JSONField(default=dict, verbose_name="Node Status")
    state_tree = models.JSONField(default=dict, null=True, blank=True, verbose_name="State Tree Snapshot")
    context = models.JSONField(default=dict, verbose_name="Context")
    template_snapshot = models.JSONField(default=dict, null=True, blank=True, verbose_name="Template Snapshot (Frozen)")
    current_node = models.CharField(max_length=200, blank=True, verbose_name="Current Node")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Started At")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="Ended At")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Executed By"
    )
    schedule_plan = models.ForeignKey(
        'SchedulePlan', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='executions',
        verbose_name="Source Schedule"
    )
    parent_execution = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_executions', verbose_name="Parent Execution"
    )
    is_subprocess = models.BooleanField(default=False, verbose_name="Is Independent Subprocess")
    excluded_nodes = models.JSONField(default=list, blank=True, verbose_name="Excluded Node IDs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_flow_execution'
        ordering = ['-created_at']
        verbose_name = "Execution"

    def __str__(self):
        return f"{self.template.name} ({self.get_status_display()})"


class OpsLog(models.Model):
    """审计日志 — 每一步的详细执行记录"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='logs',
        verbose_name="Execution"
    )
    step = models.CharField(max_length=200, blank=True, verbose_name="Step ID")
    command = models.TextField(blank=True, verbose_name="Command")
    stdout = models.TextField(blank=True, verbose_name="Stdout")
    stderr = models.TextField(blank=True, verbose_name="Stderr")
    returncode = models.IntegerField(null=True, blank=True, verbose_name="Return Code")
    risk_level = models.CharField(
        max_length=16,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='low', verbose_name="Risk Level"
    )
    approved_by = models.CharField(max_length=128, blank=True, verbose_name="Approved By")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_log'
        ordering = ['created_at']
        verbose_name = "Audit Log"

    def __str__(self):
        return f"[{self.step}] rc={self.returncode}"


class SchedulePlan(models.Model):
    """调度计划 — 一次性或周期性自动执行"""
    class ScheduleType(models.TextChoices):
        ONE_TIME = 'one_time', 'One-time'
        CRON = 'cron', 'Periodic'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'

    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='schedule_plans',
        verbose_name="Template"
    )
    name = models.CharField(max_length=128, verbose_name="Schedule Name")
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    schedule_type = models.CharField(
        max_length=16, choices=ScheduleType.choices, verbose_name="Schedule Type"
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Scheduled At")
    cron_expr = models.CharField(max_length=64, blank=True, verbose_name="Cron Expression")
    cron_description = models.CharField(max_length=128, blank=True, verbose_name="Cron Description")
    timezone = models.CharField(max_length=32, default='Asia/Shanghai', verbose_name="Timezone")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, verbose_name="Status"
    )
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")
    retry_delay = models.IntegerField(default=300, verbose_name="Retry Delay (s)")
    template_snapshot = models.JSONField(null=True, blank=True, verbose_name="Template Snapshot")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Last Run At")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Next Run At")
    total_run_count = models.IntegerField(default=0, verbose_name="Total Run Count")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'opsflow_schedule_plan'
        ordering = ['-created_at']
        verbose_name = "Schedule Plan"
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'name'],
                name='uq_schedule_plan_template_name'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_schedule_type_display()})"


class OpsKnowledge(models.Model):
    """RAG 知识库 — 历史案例/故障/文档"""
    class Source(models.TextChoices):
        RUNBOOK = 'runbook', 'Runbook'
        INCIDENT = 'incident', 'Incident'
        DOC = 'doc', 'Documentation'

    title = models.CharField(max_length=300, verbose_name="Title")
    content = models.TextField(verbose_name="Content")
    tags = models.JSONField(default=list, verbose_name="Tags")
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.DOC,
        verbose_name="Source"
    )
    embedding = models.JSONField(null=True, blank=True, verbose_name="Embedding")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_knowledge'
        ordering = ['-created_at']
        verbose_name = "Knowledge Entry"

    def __str__(self):
        return self.title


class PluginMeta(models.Model):
    """标准插件元数据 — 注册时自动同步（支持多版本）"""
    code = models.CharField(max_length=64, verbose_name="Plugin Code")
    name = models.CharField(max_length=128, verbose_name="Plugin Name")
    group = models.CharField(max_length=64, verbose_name="Group")
    version = models.CharField(max_length=16, default='v1.0', verbose_name="Version")
    description = models.TextField(blank=True, verbose_name="Description")
    risk_level = models.CharField(max_length=16, default='low', verbose_name="Risk Level")
    form_schema = models.JSONField(default=list, verbose_name="Form Schema")
    output_schema = models.JSONField(default=list, verbose_name="Output Schema")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_plugin_meta'
        ordering = ['group', 'name']
        unique_together = [('code', 'version')]
        verbose_name = "Plugin Metadata"

    def __str__(self):
        return f"{self.group}/{self.name}"


class NodeExecutionTrace(models.Model):
    """节点执行轨迹 — 每个节点每次执行的完整记录"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='traces',
        verbose_name="Execution"
    )
    node_id = models.CharField(max_length=200, verbose_name="Node ID")
    node_label = models.CharField(max_length=200, blank=True, verbose_name="Node Label")
    atom_type = models.CharField(max_length=64, blank=True, verbose_name="Atom Type")
    node_type = models.CharField(max_length=64, blank=True, verbose_name="Node Type")

    # 状态轨迹：记录每次状态变更
    status = models.CharField(max_length=16, default='pending', verbose_name="Status")
    status_history = models.JSONField(default=list, verbose_name="Status History")

    # 时间轨迹
    entered_at = models.DateTimeField(null=True, blank=True, verbose_name="Entered At")
    exited_at = models.DateTimeField(null=True, blank=True, verbose_name="Exited At")
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name="Duration (ms)")

    # 执行数据
    inputs = models.JSONField(default=dict, verbose_name="Inputs")
    outputs = models.JSONField(default=dict, verbose_name="Outputs")
    error = models.TextField(blank=True, verbose_name="Error")

    # 重试信息
    retry_count = models.IntegerField(default=0, verbose_name="Retry Count")
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")

    # 日志文件引用
    log_file_path = models.CharField(max_length=500, blank=True, verbose_name="Log File Path")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_node_trace'
        unique_together = [('execution', 'node_id', 'retry_count')]
        ordering = ['execution', 'entered_at']
        verbose_name = "Node Execution Trace"
        verbose_name_plural = "Node Execution Traces"

    def __str__(self):
        return f"[{self.execution_id}] {self.node_id} (retry#{self.retry_count})"
