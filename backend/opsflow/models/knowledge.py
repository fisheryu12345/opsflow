from django.db import models


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
        'OpsProject', on_delete=models.CASCADE, null=True, blank=True,
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
