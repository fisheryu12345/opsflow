from django.db import models


class ProjectEnvironmentVariable(models.Model):
    """项目级环境变量 — 跨模板共享的配置值"""
    project = models.ForeignKey(
        'iam.Project', on_delete=models.CASCADE, related_name='env_vars',
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
