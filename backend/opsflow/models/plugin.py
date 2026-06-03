from django.db import models


class PluginMeta(models.Model):
    """标准插件元数据 — 注册时自动同步（支持多版本）"""
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
    icon = models.CharField(max_length=32, default='', blank=True, verbose_name="Plugin Icon")
    color = models.CharField(max_length=16, default='', blank=True, verbose_name="Plugin Theme Color")
    form_schema = models.JSONField(default=list, verbose_name="Form Schema")
    output_schema = models.JSONField(default=list, verbose_name="Output Schema")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    phase = models.IntegerField(choices=PHASE_CHOICES, default=PHASE_AVAILABLE,
                                 verbose_name="生命周期")
    allowed_projects = models.JSONField(
        default=list, blank=True, verbose_name="Allowed Project IDs",
        help_text="[]表示所有项目可见；[1,2,3]表示仅指定的项目ID可见"
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
