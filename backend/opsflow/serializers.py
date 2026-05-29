from rest_framework import serializers
from .models import FlowTemplate, FlowExecution, OpsLog, OpsKnowledge


class FlowTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FlowTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


class FlowExecutionSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FlowExecution
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'started_at', 'ended_at']

    def get_template_name(self, obj):
        return obj.template.name if obj.template else ''

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


class OpsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsLog
        fields = '__all__'
        read_only_fields = ['created_at']


class OpsKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsKnowledge
        fields = '__all__'
        read_only_fields = ['created_at']
