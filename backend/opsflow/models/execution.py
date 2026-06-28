from django.db import models
from django.conf import settings


class FlowExecution(models.Model):
    """执行实例 — 一次流程运行记录"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        RUNNING = 'running', 'Running'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.PROTECT, related_name='executions',
        verbose_name="Template"
    )
    project = models.ForeignKey(
        'iam.Project', on_delete=models.CASCADE, null=True, blank=True,
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
    environment = models.ForeignKey(
        'iam.DeployEnvironment', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name="Deploy Environment",
        help_text="Target deploy environment for this execution / 本次执行的目标部署环境"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_flow_execution'
        ordering = ['-created_at']
        verbose_name = "Execution"

    def __str__(self):
        return f"{self.template.name} ({self.get_status_display()})"


class ExecutionNode(models.Model):
    """执行节点 — 执行实例中的节点记录，从 TemplateNode 同步"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='node_records',
        verbose_name="Execution"
    )
    template_node = models.ForeignKey(
        'TemplateNode', on_delete=models.SET_NULL, null=True, blank=True,
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


class ExecutionScheme(models.Model):
    """执行方案 — 预定义的节点排除集 + 变量覆盖"""
    template = models.ForeignKey(
        'FlowTemplate', on_delete=models.CASCADE, related_name='schemes',
        verbose_name="Template"
    )
    project = models.ForeignKey(
        'iam.Project', on_delete=models.CASCADE, null=True, blank=True,
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


class AutoRetryStrategy(models.Model):
    """节点自动重试策略 — 在信号拦截到 FAILED 时自动触发重试"""
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
    """节点超时配置 — 绑定到执行实例的节点超时策略"""
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

    status = models.CharField(max_length=16, default='pending', verbose_name="Status")
    status_history = models.JSONField(default=list, verbose_name="Status History")

    entered_at = models.DateTimeField(null=True, blank=True, verbose_name="Entered At")
    exited_at = models.DateTimeField(null=True, blank=True, verbose_name="Exited At")
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name="Duration (ms)")

    inputs = models.JSONField(default=dict, verbose_name="Inputs")
    outputs = models.JSONField(default=dict, verbose_name="Outputs")
    error = models.TextField(blank=True, verbose_name="Error")

    retry_count = models.IntegerField(default=0, verbose_name="Retry Count")
    max_retries = models.IntegerField(default=0, verbose_name="Max Retries")
    loop_iteration = models.IntegerField(
        default=0, verbose_name="Loop Iteration",
        help_text="Iteration index for loop/cycle scenarios. "
                  "0 = first execution, 1 = second, etc. "
                  "循环/回环场景的迭代序号 / 0=首次执行"
    )

    log_file_path = models.CharField(max_length=500, blank=True, verbose_name="Log File Path")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_node_trace'
        unique_together = [('execution', 'node_id', 'retry_count', 'loop_iteration')]
        ordering = ['execution', 'entered_at']
        verbose_name = "Node Execution Trace"
        verbose_name_plural = "Node Execution Traces"

    def __str__(self):
        extra = f" li#{self.loop_iteration}" if self.loop_iteration else ""
        return f"[{self.execution_id}] {self.node_id} (retry#{self.retry_count}{extra})"
