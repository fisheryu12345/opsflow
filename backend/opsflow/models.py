from django.db import models
from django.conf import settings


class FlowTemplate(models.Model):
    """编排模板 — AI 生成的或人工创建的流程定义"""
    name = models.CharField(max_length=200, verbose_name="流程名称")
    pipeline_tree = models.JSONField(default=dict, verbose_name="流程树JSON")
    target_hosts = models.JSONField(default=list, verbose_name="目标主机列表")
    global_vars = models.JSONField(default=dict, verbose_name="全局变量")
    is_draft = models.BooleanField(default=True, verbose_name="是否为草稿")
    ai_original_tree = models.JSONField(default=dict, verbose_name="AI原始流程树(用于diff)")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_flow_template'
        ordering = ['-created_at']
        verbose_name = "流程模板"

    version = models.IntegerField(default=1, null=True, blank=True, verbose_name="当前版本号")
    snapshot = models.JSONField(default=dict, null=True, blank=True, verbose_name="发布快照")

    def publish_snapshot(self, user=None, version_note=""):
        """发布新版本：冻结当前 pipeline_tree 到 snapshot 并创建版本记录"""
        from django.utils import timezone
        self.snapshot = {
            'pipeline_tree': self.pipeline_tree,
            'target_hosts': self.target_hosts,
            'global_vars': self.global_vars,
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
        verbose_name="关联模板"
    )
    version = models.IntegerField(verbose_name="版本号")
    pipeline_tree = models.JSONField(default=dict, verbose_name="流程树JSON")
    target_hosts = models.JSONField(default=list, verbose_name="目标主机列表")
    global_vars = models.JSONField(default=dict, verbose_name="全局变量")
    version_note = models.CharField(max_length=256, blank=True, default='', verbose_name="版本备注")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_template_version'
        ordering = ['-version']
        unique_together = [('template', 'version')]
        verbose_name = "模板版本"

    def __str__(self):
        return f"{self.template.name} v{self.version}"


class FlowExecution(models.Model):
    """执行实例 — 一次流程运行记录"""
    class Status(models.TextChoices):
        PENDING = 'pending', '待执行'
        RUNNING = 'running', '执行中'
        PAUSED = 'paused', '已暂停'
        COMPLETED = 'completed', '已完成'
        FAILED = 'failed', '失败'
        CANCELLED = 'cancelled', '已取消'

    template = models.ForeignKey(
        FlowTemplate, on_delete=models.PROTECT, related_name='executions',
        verbose_name="关联模板"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
        verbose_name="执行状态"
    )
    node_status = models.JSONField(default=dict, verbose_name="各节点状态")
    state_tree = models.JSONField(default=dict, blank=True, verbose_name="状态树快照")
    context = models.JSONField(default=dict, verbose_name="执行上下文")
    template_snapshot = models.JSONField(default=dict, null=True, blank=True, verbose_name="创建时模板快照(冻结)")
    current_node = models.CharField(max_length=200, blank=True, verbose_name="当前执行节点")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="执行者"
    )
    schedule_plan = models.ForeignKey(
        'SchedulePlan', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='executions',
        verbose_name="来源调度计划"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_flow_execution'
        ordering = ['-created_at']
        verbose_name = "执行实例"

    def __str__(self):
        return f"{self.template.name} ({self.get_status_display()})"


class OpsLog(models.Model):
    """审计日志 — 每一步的详细执行记录"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='logs',
        verbose_name="关联执行"
    )
    step = models.CharField(max_length=200, blank=True, verbose_name="步骤ID")
    command = models.TextField(blank=True, verbose_name="执行命令")
    stdout = models.TextField(blank=True, verbose_name="标准输出")
    stderr = models.TextField(blank=True, verbose_name="错误输出")
    returncode = models.IntegerField(null=True, blank=True, verbose_name="返回码")
    risk_level = models.CharField(
        max_length=16,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='low', verbose_name="风险等级"
    )
    approved_by = models.CharField(max_length=128, blank=True, verbose_name="审批人")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_log'
        ordering = ['created_at']
        verbose_name = "审计日志"

    def __str__(self):
        return f"[{self.step}] rc={self.returncode}"


class SchedulePlan(models.Model):
    """调度计划 — 一次性或周期性自动执行"""
    class ScheduleType(models.TextChoices):
        ONE_TIME = 'one_time', '一次性'
        CRON = 'cron', '周期性'

    class Status(models.TextChoices):
        ACTIVE = 'active', '运行中'
        PAUSED = 'paused', '已暂停'
        COMPLETED = 'completed', '已完成'
        EXPIRED = 'expired', '已过期'

    template = models.ForeignKey(
        FlowTemplate, on_delete=models.CASCADE, related_name='schedule_plans',
        verbose_name="关联模板"
    )
    name = models.CharField(max_length=128, verbose_name="调度名称")
    description = models.CharField(max_length=255, blank=True, verbose_name="调度描述")
    schedule_type = models.CharField(
        max_length=16, choices=ScheduleType.choices, verbose_name="调度类型"
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="一次性定时时间")
    cron_expr = models.CharField(max_length=64, blank=True, verbose_name="Cron表达式")
    cron_description = models.CharField(max_length=128, blank=True, verbose_name="Cron可读描述")
    timezone = models.CharField(max_length=32, default='Asia/Shanghai', verbose_name="时区")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, verbose_name="状态"
    )
    max_retries = models.IntegerField(default=0, verbose_name="最大重试次数")
    retry_delay = models.IntegerField(default=300, verbose_name="重试间隔(秒)")
    template_snapshot = models.JSONField(null=True, blank=True, verbose_name="创建时模板快照")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="上次执行时间")
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name="下次执行时间")
    total_run_count = models.IntegerField(default=0, verbose_name="总执行次数")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'opsflow_schedule_plan'
        ordering = ['-created_at']
        verbose_name = "调度计划"
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

    title = models.CharField(max_length=300, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    tags = models.JSONField(default=list, verbose_name="标签")
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.DOC,
        verbose_name="来源"
    )
    embedding = models.JSONField(null=True, blank=True, verbose_name="向量嵌入")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_knowledge'
        ordering = ['-created_at']
        verbose_name = "知识条目"

    def __str__(self):
        return self.title


class PluginMeta(models.Model):
    """标准插件元数据 — 注册时自动同步"""
    code = models.CharField(max_length=64, unique=True, verbose_name="插件编码")
    name = models.CharField(max_length=128, verbose_name="插件名称")
    group = models.CharField(max_length=64, verbose_name="分组")
    version = models.CharField(max_length=16, default='v1.0', verbose_name="版本")
    description = models.TextField(blank=True, verbose_name="描述")
    risk_level = models.CharField(max_length=16, default='low', verbose_name="风险等级")
    form_schema = models.JSONField(default=list, verbose_name="表单配置")
    output_schema = models.JSONField(default=list, verbose_name="输出格式")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_plugin_meta'
        ordering = ['group', 'name']
        verbose_name = "插件元数据"

    def __str__(self):
        return f"{self.group}/{self.name}"


class NodeExecutionTrace(models.Model):
    """节点执行轨迹 — 每个节点每次执行的完整记录"""
    execution = models.ForeignKey(
        FlowExecution, on_delete=models.CASCADE, related_name='traces',
        verbose_name="关联执行"
    )
    node_id = models.CharField(max_length=200, verbose_name="节点ID")
    node_label = models.CharField(max_length=200, blank=True, verbose_name="节点名称")
    atom_type = models.CharField(max_length=64, blank=True, verbose_name="原子类型")
    node_type = models.CharField(max_length=64, blank=True, verbose_name="节点类型")

    # 状态轨迹：记录每次状态变更
    status = models.CharField(max_length=16, default='pending', verbose_name="当前状态")
    status_history = models.JSONField(default=list, verbose_name="状态变更历史")

    # 时间轨迹
    entered_at = models.DateTimeField(null=True, blank=True, verbose_name="进入时间")
    exited_at = models.DateTimeField(null=True, blank=True, verbose_name="退出时间")
    duration_ms = models.IntegerField(null=True, blank=True, verbose_name="执行耗时(ms)")

    # 执行数据
    inputs = models.JSONField(default=dict, verbose_name="输入参数")
    outputs = models.JSONField(default=dict, verbose_name="输出结果")
    error = models.TextField(blank=True, verbose_name="错误信息")

    # 重试信息
    retry_count = models.IntegerField(default=0, verbose_name="已重试次数")
    max_retries = models.IntegerField(default=0, verbose_name="最大重试次数")

    # 日志文件引用
    log_file_path = models.CharField(max_length=500, blank=True, verbose_name="日志文件路径")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_node_trace'
        unique_together = [('execution', 'node_id', 'retry_count')]
        ordering = ['execution', 'entered_at']
        verbose_name = "节点执行轨迹"
        verbose_name_plural = "节点执行轨迹"

    def __str__(self):
        return f"[{self.execution_id}] {self.node_id} (retry#{self.retry_count})"
