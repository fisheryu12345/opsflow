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

    def __str__(self):
        return self.name


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
    context = models.JSONField(default=dict, verbose_name="执行上下文")
    current_node = models.CharField(max_length=200, blank=True, verbose_name="当前执行节点")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name="执行者"
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
