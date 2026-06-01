import pytz

from rest_framework import serializers
from .models import FlowTemplate, TemplateVersion, FlowExecution, NodeExecutionTrace, OpsLog, OpsKnowledge, SchedulePlan, TemplateNode, ExecutionNode, ExecutionScheme, OperationRecord, TemplateCollect, OpsProject


class GlobalVariableField(serializers.Field):
    """全局变量字段 — 接受扁平或结构化格式，始终返回结构化格式"""

    def to_representation(self, value):
        from opsflow.core.variable_resolver import normalize_global_vars
        return normalize_global_vars(value)

    def to_internal_value(self, data):
        return data


class FlowTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    global_variable_list = serializers.SerializerMethodField()
    global_vars = GlobalVariableField(required=False, default=dict)

    class Meta:
        model = FlowTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'version', 'snapshot']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''

    def get_global_variable_list(self, obj):
        """返回展开为 array 格式的全局变量列表（含引用计数和引用明细）"""
        from opsflow.core.variable_resolver import normalize_global_vars, count_variable_references, get_variable_reference_details
        normalized = normalize_global_vars(obj.global_vars)
        tree = obj.pipeline_tree or {}
        result = []
        for key, entry in normalized.items():
            result.append({
                "key": key,
                "value": entry["value"],
                "type": entry["type"],
                "show_type": entry["show_type"],
                "description": entry.get("description", ""),
                "source_type": entry.get("source_type", "manual"),
                "source_info": entry.get("source_info"),
                "reference_count": count_variable_references(tree, key),
                "references": get_variable_reference_details(tree, key),
            })
        return result


class TemplateVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TemplateVersion
        fields = '__all__'
        read_only_fields = ['created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


class FlowExecutionSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FlowExecution
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'started_at', 'ended_at', 'template_snapshot']

    def get_template_name(self, obj):
        return obj.template.name if obj.template else ''

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


class TemplateNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateNode
        fields = '__all__'
        read_only_fields = ['created_at']


class ExecutionSchemeSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ExecutionScheme
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


class ExecutionNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutionNode
        fields = '__all__'
        read_only_fields = ['created_at']


class NodeExecutionTraceSerializer(serializers.ModelSerializer):
    """Node execution trace serializer"""

    class Meta:
        model = NodeExecutionTrace
        exclude = ['execution']
        read_only_fields = ['created_at', 'updated_at']


class FlowExecutionDetailSerializer(FlowExecutionSerializer):
    """Execution detail serializer (with status tree + trace summary)"""
    trace_summary = serializers.SerializerMethodField()

    class Meta(FlowExecutionSerializer.Meta):
        fields = '__all__'

    def get_trace_summary(self, obj):
        """Return trace summary without full outputs"""
        traces = NodeExecutionTrace.objects.filter(execution=obj).values(
            'node_id', 'node_label', 'status', 'retry_count',
            'duration_ms', 'entered_at', 'exited_at', 'error',
        ).order_by('entered_at')
        return list(traces)


class OpsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsLog
        fields = '__all__'
        read_only_fields = ['created_at']


class OperationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationRecord
        fields = '__all__'
        read_only_fields = ['created_at']


class TemplateCollectSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCollect
        fields = '__all__'
        read_only_fields = ['user', 'created_at']

    def get_template_name(self, obj):
        return obj.template.name if obj.template else ''


class OpsKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsKnowledge
        fields = '__all__'
        read_only_fields = ['created_at']


def _validate_cron_expr(value):
    """Validate cron expression with APScheduler"""
    from apscheduler.triggers.cron import CronTrigger
    try:
        CronTrigger.from_crontab(value)
    except (ValueError, TypeError) as e:
        raise serializers.ValidationError(f"Invalid cron expression: {e}")


class SchedulePlanSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SchedulePlan
        fields = '__all__'
        read_only_fields = [
            'created_by', 'created_at', 'updated_at',
            'last_run_at', 'next_run_at', 'total_run_count',
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else ''

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''

    def validate_timezone(self, value):
        if value and value not in pytz.all_timezones:
            raise serializers.ValidationError(f"Invalid timezone: {value}")
        return value

    def validate(self, attrs):
        # Only published templates can create scheduled tasks
        template = attrs.get('template') or getattr(getattr(self, 'instance', None), 'template', None)
        if template and template.is_draft:
            raise serializers.ValidationError(
                {'template': 'Only published templates can create scheduled tasks'}
            )

        if attrs.get('schedule_type') == SchedulePlan.ScheduleType.ONE_TIME:
            if not attrs.get('scheduled_at'):
                raise serializers.ValidationError(
                    {'scheduled_at': 'One-time schedule must specify execution time'}
                )
            from django.utils import timezone
            if attrs['scheduled_at'] <= timezone.now():
                raise serializers.ValidationError(
                    {'scheduled_at': 'Execution time must be in the future'}
                )
        elif attrs.get('schedule_type') == SchedulePlan.ScheduleType.CRON:
            if not attrs.get('cron_expr'):
                raise serializers.ValidationError(
                    {'cron_expr': 'Recurring schedule must specify a cron expression'}
                )
            _validate_cron_expr(attrs['cron_expr'])
        return attrs


class OpsProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsProject
        fields = ['id', 'name', 'description', 'is_active', 'owner', 'created_at']
        read_only_fields = ['id', 'created_at']
