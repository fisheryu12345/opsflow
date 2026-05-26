from django.contrib import admin
from .models import EnvironmentContext, Session, AuditRecord, AgentMemory


@admin.register(EnvironmentContext)
class EnvironmentContextAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'env_type', 'is_active', 'updated_at']
    list_filter = ['env_type', 'is_active']
    search_fields = ['name', 'slug']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'operator', 'environment', 'mode', 'status', 'started_at']
    list_filter = ['mode', 'status']
    search_fields = ['session_id', 'operator']
    readonly_fields = ['session_id', 'started_at']


@admin.register(AuditRecord)
class AuditRecordAdmin(admin.ModelAdmin):
    list_display = ['seq', 'tool_name', 'target', 'risk_score', 'safety_decision', 'execution_success', 'timestamp']
    list_filter = ['tool_name', 'safety_decision', 'risk_operation', 'execution_success']
    search_fields = ['target', 'result_summary', 'llm_reasoning']
    readonly_fields = [f.name for f in AuditRecord._meta.fields]


@admin.register(AgentMemory)
class AgentMemoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'memory_type', 'is_active', 'expires_at', 'created_at']
    list_filter = ['memory_type', 'is_active']
    search_fields = ['title', 'content']
