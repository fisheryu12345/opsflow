from django.db import models


class EnvironmentContext(models.Model):
    """Persisted OPS_CONTEXT.md equivalent — one row per managed environment."""
    name = models.CharField(max_length=128, unique=True, help_text="e.g. 'prod-k8s-cluster'")
    slug = models.SlugField(max_length=128, unique=True)
    env_type = models.CharField(
        max_length=16,
        choices=[('production', 'Production'), ('staging', 'Staging'),
                 ('canary', 'Canary'), ('development', 'Development')],
        default='development',
    )
    topology_json = models.JSONField(default=dict, help_text="CMDB-injected topology")
    constraints_md = models.TextField(blank=True, help_text="Markdown constraints (change windows, rules)")
    credential_ref = models.CharField(max_length=256, blank=True, help_text="Vault path or key reference")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_environment'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.env_type})"


class Session(models.Model):
    """One interactive session or one-shot run."""
    session_id = models.CharField(max_length=64, unique=True)
    operator = models.CharField(max_length=128, default='admin')
    environment = models.ForeignKey(EnvironmentContext, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    mode = models.CharField(max_length=16, choices=[('repl', 'REPL'), ('oneshot', 'One-shot')])
    status = models.CharField(
        max_length=16,
        choices=[('active', 'Active'), ('completed', 'Completed'), ('aborted', 'Aborted')],
        default='active',
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        db_table = 'ops_session'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.session_id} ({self.operator})"


class AuditRecord(models.Model):
    """Append-only audit log. No update/delete via application code."""
    RISK_OPERATIONS = [
        ('READ', 'Read'), ('LOW_WRITE', 'Low Write'), ('MEDIUM_WRITE', 'Medium Write'),
        ('HIGH_WRITE', 'High Write'), ('CRITICAL', 'Critical'),
    ]
    RISK_ENVIRONMENTS = [
        ('development', 'Development'), ('staging', 'Staging'),
        ('canary', 'Canary'), ('production', 'Production'),
    ]
    RISK_BLAST_RADII = [
        ('single', 'Single'), ('group', 'Group'), ('cluster-wide', 'Cluster-Wide'),
    ]
    SAFETY_DECISIONS = [
        ('AUTO', 'Auto'), ('AUTO_ECHO', 'Auto Echo'), ('ASK', 'Ask'),
        ('ASK_BLAST', 'Ask Blast'), ('DENY', 'Deny'),
    ]

    session = models.ForeignKey(Session, on_delete=models.PROTECT, related_name='audit_records')
    seq = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    target = models.CharField(max_length=256, blank=True, help_text="Target resource identifier")
    tool_name = models.CharField(max_length=128)
    parameters_json = models.JSONField(default=dict)
    risk_operation = models.CharField(max_length=16, choices=RISK_OPERATIONS)
    risk_environment = models.CharField(max_length=16, choices=RISK_ENVIRONMENTS)
    risk_blast_radius = models.CharField(max_length=32, choices=RISK_BLAST_RADII)
    risk_score = models.FloatField()
    safety_decision = models.CharField(max_length=16, choices=SAFETY_DECISIONS)
    approved_by = models.CharField(max_length=128, blank=True)
    approval_time_ms = models.PositiveIntegerField(null=True)
    execution_started = models.DateTimeField(null=True)
    execution_completed = models.DateTimeField(null=True)
    execution_duration_ms = models.PositiveIntegerField(null=True)
    execution_success = models.BooleanField(null=True)
    result_summary = models.TextField(blank=True)
    llm_reasoning = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64)

    class Meta:
        db_table = 'ops_audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['session', 'seq']),
            models.Index(fields=['target', 'timestamp']),
            models.Index(fields=['tool_name', 'timestamp']),
            models.Index(fields=['risk_score']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['session', 'seq'], name='uq_audit_session_seq'),
        ]

    def __str__(self):
        return f"[{self.seq}] {self.tool_name} → {self.safety_decision}"


class AgentMemory(models.Model):
    """Persistent memory entries (fault patterns, operational tips, preferences)."""
    MEMORY_TYPES = [
        ('fault_pattern', 'Fault Pattern'),
        ('ops_experience', 'Operations Experience'),
        ('team_preference', 'Team Preference'),
        ('temporary_constraint', 'Temporary Constraint'),
    ]
    memory_type = models.CharField(max_length=32, choices=MEMORY_TYPES)
    title = models.CharField(max_length=256)
    content = models.TextField()
    tags_json = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ops_memory'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.memory_type}] {self.title}"
