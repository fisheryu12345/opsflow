# -*- coding: utf-8 -*-
"""Admin registration for integration models"""

from django.contrib import admin

from .models.connector import ConnectorDefinition, ConnectorInstance
from .models.credential import ConnectorCredential
from .models.integration_log import IntegrationLog


@admin.register(ConnectorDefinition)
class ConnectorDefinitionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'version', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name']


@admin.register(ConnectorInstance)
class ConnectorInstanceAdmin(admin.ModelAdmin):
    list_display = ['name', 'definition', 'status', 'is_active', 'last_health_check']
    list_filter = ['status', 'is_active']
    search_fields = ['name']


@admin.register(ConnectorCredential)
class ConnectorCredentialAdmin(admin.ModelAdmin):
    list_display = ['name', 'instance', 'cred_type', 'expire_at']
    list_filter = ['cred_type']


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ['instance', 'action', 'status', 'duration_ms', 'create_datetime']
    list_filter = ['status', 'action']
    date_hierarchy = 'create_datetime'
