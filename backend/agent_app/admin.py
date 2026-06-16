# -*- coding: utf-8 -*-
"""Admin registration for agent models"""

from django.contrib import admin
from .models import AgentInstance, AgentTaskExecution, AgentFileTask, AgentCollect, AgentUpgrade


@admin.register(AgentInstance)
class AgentInstanceAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'ip', 'os_type', 'agent_version', 'status', 'last_heartbeat']
    list_filter = ['status', 'os_type']
    search_fields = ['hostname', 'ip', 'agent_id']


@admin.register(AgentTaskExecution)
class AgentTaskExecutionAdmin(admin.ModelAdmin):
    list_display = ['exec_id', 'task_source', 'script_type', 'status', 'start_time']
    list_filter = ['status', 'task_source']


@admin.register(AgentFileTask)
class AgentFileTaskAdmin(admin.ModelAdmin):
    list_display = ['file_task_id', 'file_name', 'direction', 'file_size', 'status', 'progress']
    list_filter = ['status', 'direction']


@admin.register(AgentCollect)
class AgentCollectAdmin(admin.ModelAdmin):
    list_display = ['agent', 'collect_type', 'collect_interval', 'last_collect', 'status']


@admin.register(AgentUpgrade)
class AgentUpgradeAdmin(admin.ModelAdmin):
    list_display = ['upgrade_id', 'agent', 'from_version', 'to_version', 'status']
    list_filter = ['status']
