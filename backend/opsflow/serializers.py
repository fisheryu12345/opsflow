import pytz

from rest_framework import serializers
from .models import FlowTemplate, TemplateVersion, FlowExecution, NodeExecutionTrace, OpsLog, OpsKnowledge, SchedulePlan


class FlowTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FlowTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'version', 'snapshot']

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by else ''


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


class NodeExecutionTraceSerializer(serializers.ModelSerializer):
    """节点执行轨迹序列化器"""

    class Meta:
        model = NodeExecutionTrace
        exclude = ['execution']
        read_only_fields = ['created_at', 'updated_at']


class FlowExecutionDetailSerializer(FlowExecutionSerializer):
    """执行详情序列化器（含状态树 + 轨迹摘要）"""
    trace_summary = serializers.SerializerMethodField()

    class Meta(FlowExecutionSerializer.Meta):
        fields = FlowExecutionSerializer.Meta.fields + ['state_tree', 'trace_summary']

    def get_trace_summary(self, obj):
        """返回不含完整 outputs 的轨迹摘要"""
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


class OpsKnowledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsKnowledge
        fields = '__all__'
        read_only_fields = ['created_at']


def _validate_cron_expr(value):
    """用 APScheduler 验证 cron 表达式"""
    from apscheduler.triggers.cron import CronTrigger
    try:
        CronTrigger.from_crontab(value)
    except (ValueError, TypeError) as e:
        raise serializers.ValidationError(f"Cron表达式无效: {e}")


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
            raise serializers.ValidationError(f"无效的时区: {value}")
        return value

    def validate(self, attrs):
        # 仅已发布的模板可创建定时任务
        template = attrs.get('template') or getattr(getattr(self, 'instance', None), 'template', None)
        if template and template.is_draft:
            raise serializers.ValidationError(
                {'template': '仅已发布的模板可创建定时任务'}
            )

        if attrs.get('schedule_type') == SchedulePlan.ScheduleType.ONE_TIME:
            if not attrs.get('scheduled_at'):
                raise serializers.ValidationError(
                    {'scheduled_at': '一次性调度必须指定执行时间'}
                )
            from django.utils import timezone
            if attrs['scheduled_at'] <= timezone.now():
                raise serializers.ValidationError(
                    {'scheduled_at': '执行时间必须在未来'}
                )
        elif attrs.get('schedule_type') == SchedulePlan.ScheduleType.CRON:
            if not attrs.get('cron_expr'):
                raise serializers.ValidationError(
                    {'cron_expr': '周期性调度必须指定Cron表达式'}
                )
            _validate_cron_expr(attrs['cron_expr'])
        return attrs
