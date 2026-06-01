from django.db import models
from django.conf import settings


class OpsProject(models.Model):
    """OpsFlow 项目 — 数据隔离单元

    不同项目的数据互相不可见（模板/执行/调度/知识库等）。
    参考 bk_sops Project + Business 模型，此版本为轻量独立实现。
    """
    name = models.CharField(max_length=128, unique=True, verbose_name="Project Name")
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Owner"
    )
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    max_schedule_plans = models.IntegerField(
        default=20, verbose_name="Max Schedule Plans",
        help_text="项目最多可创建的定时任务数，0=不限制"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_project'
        ordering = ['name']
        verbose_name = "OpsFlow Project"

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    """项目成员 — 记录哪些用户属于哪些项目"""
    class Role(models.TextChoices):
        ADMIN = 'admin', '管理员'
        EDITOR = 'editor', '编辑者'
        VIEWER = 'viewer', '查看者'

    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, related_name='members',
        verbose_name="Project"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name="User"
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.EDITOR,
        verbose_name="Role"
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Joined At")

    class Meta:
        db_table = 'ops_project_member'
        unique_together = [('project', 'user')]
        verbose_name = "Project Member"

    def __str__(self):
        return f"{self.user} @ {self.project} ({self.role})"


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
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, null=True, blank=True,
        related_name='templates', verbose_name="Project"
    )
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
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, null=True, blank=True,
        related_name='executions', verbose_name="Project"
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
    excluded_nodes = models.JSONField(default=list, null=True, blank=True, verbose_name="Excluded Node IDs")
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
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, null=True, blank=True,
        related_name='schedule_plans', verbose_name="Project"
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
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, null=True, blank=True,
        related_name='knowledge_entries', verbose_name="Project"
    )
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


class OperationRecord(models.Model):
    """操作审计记录 — 记录所有重要用户操作"""
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        PUBLISH = 'publish', 'Publish'
        ROLLBACK = 'rollback', 'Rollback'
        EXECUTE = 'execute', 'Execute'
        APPROVE = 'approve', 'Approve'
        REJECT = 'reject', 'Reject'

    action = models.CharField(max_length=16, choices=Action.choices, verbose_name='Action')
    resource_type = models.CharField(max_length=32, verbose_name='Resource Type')
    resource_id = models.CharField(max_length=32, blank=True, verbose_name='Resource ID')
    resource_name = models.CharField(max_length=200, blank=True, verbose_name='Resource Name')
    detail = models.JSONField(default=dict, verbose_name='Detail')
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Operator'
    )
    ip_address = models.CharField(max_length=45, blank=True, verbose_name='IP Address')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_operation_record'
        ordering = ['-created_at']
        verbose_name = 'Operation Record'

    def __str__(self):
        return f'{self.action} {self.resource_type}[{self.resource_id}]'


class TemplateCollect(models.Model):
    """用户收藏的模板"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        verbose_name='User'
    )
    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='collected_by',
        verbose_name='Template'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_template_collect'
        unique_together = [('user', 'template')]
        ordering = ['-created_at']
        verbose_name = 'Template Collection'

    def __str__(self):
        return f'{self.user} -> {self.template}'



class ApiToken(models.Model):
    """外部 API Token — 用于第三方系统认证"""
    name = models.CharField(max_length=64, verbose_name='Token Name')
    token = models.CharField(max_length=64, unique=True, verbose_name='Token')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    allowed_actions = models.JSONField(default=list, blank=True, verbose_name='Allowed Actions')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name='Creator'
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expires At')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_api_token'
        verbose_name = 'API Token'

    def __str__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"


class PluginMeta(models.Model):
    """标准插件元数据 — 注册时自动同步（支持多版本）"""
    # 生命周期阶段（参考 bk_sops DeprecatedPlugin）
    PHASE_AVAILABLE = 0
    PHASE_WILL_BE_DEPRECATED = 1
    PHASE_DEPRECATED = 2
    PHASE_CHOICES = [
        (PHASE_AVAILABLE, '可用'),
        (PHASE_WILL_BE_DEPRECATED, '即将弃用'),
        (PHASE_DEPRECATED, '已弃用'),
    ]

    code = models.CharField(max_length=64, verbose_name="Plugin Code")
    name = models.CharField(max_length=128, verbose_name="Plugin Name")
    group = models.CharField(max_length=64, verbose_name="Group")
    version = models.CharField(max_length=16, default='v1.0', verbose_name="Version")
    description = models.TextField(blank=True, verbose_name="Description")
    risk_level = models.CharField(max_length=16, default='low', verbose_name="Risk Level")
    form_schema = models.JSONField(default=list, verbose_name="Form Schema")
    output_schema = models.JSONField(default=list, verbose_name="Output Schema")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    phase = models.IntegerField(choices=PHASE_CHOICES, default=PHASE_AVAILABLE,
                                 verbose_name="生命周期")
    allowed_projects = models.JSONField(
        default=list, blank=True, verbose_name="Allowed Project IDs",
        help_text="[] 表示所有项目可见；[1,2,3] 表示仅指定的项目 ID 可见"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_plugin_meta'
        ordering = ['group', 'name']
        unique_together = [('code', 'version')]
        verbose_name = "Plugin Metadata"

    def __str__(self):
        phase_label = dict(self.PHASE_CHOICES).get(self.phase, '')
        return f"{self.group}/{self.name} [{phase_label}]"


class ExecutionScheme(models.Model):
    """执行方案 — 预定义的节点排除集 + 变量覆盖"""
    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='schemes',
        verbose_name="Template"
    )
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, null=True, blank=True,
        related_name='schemes', verbose_name="Project"
    )
    name = models.CharField(max_length=128, verbose_name="Scheme Name")
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    excluded_nodes = models.JSONField(default=list, verbose_name="Excluded Node IDs")
    variable_overrides = models.JSONField(default=dict, blank=True, verbose_name="Variable Overrides")
    is_default = models.BooleanField(default=False, verbose_name="Is Default")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_execution_scheme'
        ordering = ['-is_default', 'name']
        verbose_name = "Execution Scheme"

    def __str__(self):
        return f"[{self.template.name}] {self.name}"


class TemplateNode(models.Model):
    """模板节点 — 从 pipeline_tree JSON 同步为独立行，支持 SQL 查询"""
    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='node_records',
        verbose_name="Template"
    )
    node_id = models.CharField(max_length=200, verbose_name="Node ID")
    node_type = models.CharField(max_length=32, verbose_name="Node Type")
    atom_type = models.CharField(max_length=64, blank=True, verbose_name="Atom Type")
    label = models.CharField(max_length=200, blank=True, verbose_name="Label")
    node_config = models.JSONField(default=dict, verbose_name="Node Config")
    position_x = models.FloatField(null=True, blank=True, verbose_name="Position X")
    position_y = models.FloatField(null=True, blank=True, verbose_name="Position Y")
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")
    timeout_seconds = models.IntegerField(null=True, blank=True, verbose_name="Timeout (s)")
    risk_level = models.CharField(max_length=16, default='low', verbose_name="Risk Level")
    is_subprocess = models.BooleanField(default=False, verbose_name="Is Subprocess")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_template_node'
        unique_together = [('template', 'node_id')]
        ordering = ['template', 'node_id']
        verbose_name = "Template Node"

    def __str__(self):
        return f"[{self.template_id}] {self.node_id} ({self.node_type})"


class ExecutionNode(models.Model):
    """执行节点 — 执行实例中的节点记录，从 TemplateNode 同步"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='node_records',
        verbose_name="Execution"
    )
    template_node = models.ForeignKey(
        TemplateNode, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Source Template Node"
    )
    node_id = models.CharField(max_length=200, verbose_name="Node ID")
    node_type = models.CharField(max_length=32, verbose_name="Node Type")
    atom_type = models.CharField(max_length=64, blank=True, verbose_name="Atom Type")
    label = models.CharField(max_length=200, blank=True, verbose_name="Label")
    status = models.CharField(max_length=16, default='pending', verbose_name="Status")
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")
    timeout_seconds = models.IntegerField(null=True, blank=True, verbose_name="Timeout (s)")
    position_x = models.FloatField(null=True, blank=True, verbose_name="Position X")
    position_y = models.FloatField(null=True, blank=True, verbose_name="Position Y")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_execution_node'
        unique_together = [('execution', 'node_id')]
        ordering = ['execution', 'node_id']
        verbose_name = "Execution Node"

    def __str__(self):
        return f"[{self.execution_id}] {self.node_id} ({self.status})"


class AutoRetryStrategy(models.Model):
    """节点自动重试策略 — 在信号拦截到 FAILED 时自动触发重试

    参考 bk_sops gcloud/taskflow3/models.py AutoRetryNodeStrategy
    """
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='auto_retry_strategies',
        verbose_name="Execution"
    )
    node_id = models.CharField(max_length=200, verbose_name="Node ID")
    max_retry_times = models.IntegerField(default=3, verbose_name="Max Retry Times")
    interval = models.IntegerField(default=0, verbose_name="Retry Interval (s)",
                                    help_text="重试前等待秒数")
    retry_times = models.IntegerField(default=0, verbose_name="Current Retry Count",
                                      help_text="当前已重试次数（计数器）")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_auto_retry_strategy'
        unique_together = [('execution', 'node_id')]
        verbose_name = "Auto Retry Strategy"

    def __str__(self):
        return f"[{self.execution_id}] {self.node_id} ({self.retry_times}/{self.max_retry_times})"


class NodeTimeoutConfig(models.Model):
    """节点超时配置 — 绑定到执行实例的节点超时策略

    参考 bk_sops gcloud/taskflow3/models.py TimeoutNodeConfig + TimeoutNodesRecord
    """
    class Action(models.TextChoices):
        FORCED_FAIL = 'forced_fail', '强制失败'
        FORCED_FAIL_AND_SKIP = 'forced_fail_and_skip', '强制失败并跳过'

    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='timeout_configs',
        verbose_name="Execution"
    )
    node_id = models.CharField(max_length=200, verbose_name="Node ID")
    timeout_seconds = models.IntegerField(verbose_name="Timeout (s)")
    action = models.CharField(
        max_length=32, choices=Action.choices, default=Action.FORCED_FAIL,
        verbose_name="Timeout Action"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_node_timeout_config'
        unique_together = [('execution', 'node_id')]
        verbose_name = "Node Timeout Config"

    def __str__(self):
        return f"[{self.execution_id}] {self.node_id} timeout={self.timeout_seconds}s action={self.action}"


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


class WebhookConfig(models.Model):
    """Webhook 回调配置 — 绑定到模板，执行完成后触发

    参考 bk_sops TaskCallBackRecord
    """
    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='webhooks',
        verbose_name="Template"
    )
    name = models.CharField(max_length=128, verbose_name="Webhook Name")
    url = models.URLField(max_length=1024, verbose_name="Callback URL")
    secret = models.CharField(max_length=256, blank=True, verbose_name="HMAC Secret",
                               help_text="HMAC 签名密钥（可选）")
    trigger_events = models.JSONField(
        default=list, blank=True, verbose_name="Trigger Events",
        help_text="['completed', 'failed'] 触发事件列表"
    )
    retry_count = models.IntegerField(default=3, verbose_name="Max Retries")
    retry_interval = models.IntegerField(default=10, verbose_name="Retry Interval (s)")
    enabled = models.BooleanField(default=True, verbose_name="Enabled")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Creator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_webhook_config'
        ordering = ['-created_at']
        verbose_name = "Webhook Config"

    def __str__(self):
        return f"{self.name} → {self.url}"


class WebhookLog(models.Model):
    """Webhook 投递日志"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    webhook = models.ForeignKey(
        WebhookConfig, on_delete=models.CASCADE, related_name='logs',
        verbose_name="Webhook Config"
    )
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='webhook_logs', verbose_name="Execution"
    )
    event = models.CharField(max_length=32, verbose_name="Event Type")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name="Status"
    )
    request_url = models.URLField(max_length=1024, verbose_name="Request URL")
    request_body = models.JSONField(default=dict, verbose_name="Request Body")
    response_status = models.IntegerField(null=True, blank=True, verbose_name="Response Status")
    response_body = models.TextField(blank=True, verbose_name="Response Body")
    retry_count = models.IntegerField(default=0, verbose_name="Retry Count")
    error_message = models.TextField(blank=True, verbose_name="Error Message")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_webhook_log'
        ordering = ['-created_at']
        verbose_name = "Webhook Log"

    def __str__(self):
        return f"[{self.webhook_id}] {self.event} → {self.status}"


class ProjectEnvironmentVariable(models.Model):
    """项目级环境变量 — 跨模板共享的配置值

    项目（而非模板）级别的键值对，可在模板变量中通过 ${env.key} 引用。
    用于存储 API Key、端点地址、共享密码等跨模板的公共配置。
    """
    project = models.ForeignKey(
        OpsProject, on_delete=models.CASCADE, related_name='env_vars',
        verbose_name="Project"
    )
    key = models.CharField(max_length=128, verbose_name="Variable Key")
    value = models.TextField(blank=True, verbose_name="Variable Value")
    var_type = models.CharField(
        max_length=16,
        choices=[
            ('input', 'Text'), ('textarea', 'Textarea'),
            ('password', 'Password'), ('int', 'Number'), ('float', 'Float'),
        ],
        default='input', verbose_name="Type"
    )
    description = models.CharField(max_length=255, blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_project_env_var'
        unique_together = [('project', 'key')]
        ordering = ['key']
        verbose_name = "Project Environment Variable"

    def __str__(self):
        return f"[{self.project_id}] {self.key} ({self.var_type})"
