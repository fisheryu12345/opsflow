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
    project = models.ForeignKey(
        'OpsProject', on_delete=models.CASCADE, null=True, blank=True,
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
    is_public = models.BooleanField(default=False, verbose_name="Is Public Template")
    project_scope = models.JSONField(default=list, blank=True, verbose_name="Visible Project Scope")

    def clean(self):
        """Public templates should not be bound to a specific project"""
        if self.is_public:
            self.project = None

    def publish_snapshot(self, user=None, version_note=""):
        """发布新版本：冻结当前 pipeline_tree 到 snapshot 并创建版本记录"""
        from django.utils import timezone
        if self.version is None:
            self.version = 1

        # 提取子流程引用信息
        subprocess_refs = {}
        tree = self.pipeline_tree or {}
        # Batch query: collect all target_template_ids first
        target_ids = set()
        for node in tree.get('nodes', []):
            if node.get('node_type') == 'subprocess':
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    target_ids.add(target_id)
        # Single batch query, index by id
        template_map = {}
        if target_ids:
            for t in FlowTemplate.objects.filter(id__in=target_ids):
                template_map[str(t.id)] = t
        # Build subprocess refs using pre-loaded templates
        for node in tree.get('nodes', []):
            if node.get('node_type') == 'subprocess':
                params = node.get('params', {}) or {}
                target_id = params.get('target_template_id')
                if target_id:
                    target = template_map.get(target_id)
                    if target:
                        subprocess_refs[node['id']] = {
                            'target_template_id': target_id,
                            'target_version': target.version or 1,
                            'target_name': target.name,
                            'variable_mapping': params.get('variable_mapping', {}),
                            'output_mapping': params.get('output_mapping', {}),
                        }
                    else:
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
        FlowTemplate, on_delete=models.CASCADE, related_name='versions',
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

class TemplateCategory(models.Model):
    """模板分类 — 可管理配置，管理员可增删"""
    name = models.CharField(max_length=64, unique=True, verbose_name="Category Name")
    code = models.CharField(max_length=64, unique=True, verbose_name="Code")
    icon = models.CharField(max_length=64, blank=True, default='', verbose_name="Icon")
    sort_order = models.IntegerField(default=0, verbose_name="Sort Order")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ops_template_category'
        ordering = ['sort_order', 'name']
        verbose_name = "Template Category"

    def __str__(self):
        return self.name
