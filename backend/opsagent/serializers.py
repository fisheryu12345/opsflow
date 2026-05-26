# backend/opsagent/serializers.py
from rest_framework import serializers
from .models import AuditRecord, Session, EnvironmentContext, AgentMemory


class EnvironmentContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentContext
        fields = '__all__'


class SessionSerializer(serializers.ModelSerializer):
    audit_count = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = '__all__'

    def get_audit_count(self, obj):
        return obj.audit_records.count()


class AuditRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRecord
        fields = '__all__'


class AgentMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentMemory
        fields = '__all__'
