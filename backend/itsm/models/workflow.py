# -*- coding: utf-8 -*-
"""ITSM Workflow model — 流程模板定义与版本管理

Workflow: 设计时模板，包含 States/Transitions/Fields 关联
WorkflowVersion: 部署快照，工单运行依赖的冻结数据
"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


class Workflow(CoreModel):
    """ITSM 流程模板 — 设计时定义"""
    itsm_type_choices = (
        ('change', '变更申请'),
        ('incident', '事件工单'),
        ('request', '服务请求'),
        ('problem', '问题管理'),
    )
    name = models.CharField(max_length=128, verbose_name="流程名称")
    itsm_type = models.CharField(max_length=32, choices=itsm_type_choices, verbose_name="服务类型")
    is_enabled = models.BooleanField(default=False, verbose_name="是否启用")
    is_draft = models.BooleanField(default=True, verbose_name="草稿状态")
    is_revocable = models.BooleanField(default=True, verbose_name="是否可撤销")
    notify_rule = models.CharField(max_length=64, default='', blank=True, verbose_name="通知规则")
    description = models.TextField(blank=True, default='', verbose_name="流程描述")

    class Meta:
        db_table = table_prefix + "itsm_workflow"
        verbose_name = "流程模板"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"[{self.get_itsm_type_display()}] {self.name}"

    @property
    def first_state(self):
        """获取提单节点 (第一个 NORMAL 节点)"""
        return self.states.filter(type='NORMAL', is_builtin=True).first()

    @property
    def start_state(self):
        return self.states.filter(type='START').first()

    @property
    def end_state(self):
        return self.states.filter(type='END').first()

    def create_version(self, operator, message=''):
        """部署 -> 创建 WorkflowVersion 快照"""
        states_data = {}
        for s in self.states.all():
            states_data[s.id] = {
                'id': s.id, 'name': s.name, 'type': s.type,
                'processors_type': s.processors_type,
                'processors': s.processors,
                'distribute_type': s.distribute_type,
                'is_multi': s.is_multi,
                'is_sequential': s.is_sequential,
                'finish_condition': s.finish_condition,
                'is_allow_skip': s.is_allow_skip,
                'fields': s.fields,
                'extras': s.extras,
                'is_builtin': s.is_builtin,
                'api_instance_id': s.api_instance_id,
            }
        transitions_data = {}
        for t in self.transitions.all():
            transitions_data[t.id] = {
                'id': t.id, 'name': t.name,
                'from_state_id': t.from_state_id,
                'to_state_id': t.to_state_id,
                'condition': t.condition,
                'condition_type': t.condition_type,
                'direction': t.direction,
            }
        fields_data = {}
        for f in self.fields.all():
            fields_data[f.id] = {
                'id': f.id, 'state_id': f.state_id,
                'key': f.key, 'name': f.name, 'type': f.type,
                'required': f.required, 'layout': f.layout,
                'choice': f.choice, 'default': f.default,
                'validate_type': f.validate_type,
                'show_conditions': f.show_conditions,
                'source_type': f.source_type,
                'meta': f.meta, 'sort_order': f.sort_order,
            }
        return WorkflowVersion.objects.create(
            workflow=self,
            version=self.updated_at.strftime('%Y%m%d%H%M%S') if self.updated_at else '',
            version_message=message,
            states=states_data,
            transitions=transitions_data,
            fields=fields_data,
            created_by=operator,
        )


class WorkflowVersion(CoreModel):
    """流程版本 — 部署快照，工单运行的依据"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='versions',
                                 verbose_name="关联模板")
    version = models.CharField(max_length=32, verbose_name="版本号")
    version_message = models.TextField(blank=True, default='', verbose_name="版本说明")
    # 运行时快照 (JSON)
    states = models.JSONField(default=dict, verbose_name="节点快照")
    transitions = models.JSONField(default=dict, verbose_name="连线快照")
    fields = models.JSONField(default=dict, verbose_name="字段快照")
    pipeline_data = models.JSONField(default=dict, verbose_name="Pipeline 数据缓存")

    class Meta:
        db_table = table_prefix + "itsm_workflow_version"
        verbose_name = "流程版本"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.workflow.name} v{self.version}"
