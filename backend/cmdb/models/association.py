# -*- coding: utf-8 -*-
"""Association models — 关联类型 & 模型关联，对标 bk-cmdb AssociationKind & Association

三级关联体系：
  1. AssociationType — 定义关系语义（如 CONTAINS、RUNS、DEPENDS_ON）
  2. ModelAssociation — 定义哪些模型间可建立哪种关联
  3. 实例关联（Neo4j 中直接以 Relationship 存储，无 MySQL 表）
"""

from django.db import models
from dvadmin.utils.models import CoreModel, table_prefix


DIRECTION_CHOICES = (
    ('none', '无方向'),
    ('src_to_dest', '单向(源→目标)'),
    ('dest_to_src', '单向(目标→源)'),
    ('bidirectional', '双向'),
)

MAPPING_CHOICES = (
    ('1:1', '一对一'),
    ('1:n', '一对多'),
    ('n:n', '多对多'),
)

ON_DELETE_CHOICES = (
    ('none', '无操作'),
    ('delete_target', '删除目标'),
)


class AssociationType(CoreModel):
    """
    关联类型 (AssociationKind)
    对标 bk-cmdb AssociationKind。每个 asst_id 对应 Neo4j 一种 Relationship Type。
    """
    asst_id = models.CharField(
        max_length=128, unique=True,
        verbose_name="关联类型标识",
        help_text="如 CONTAINS、RUNS、DEPENDS_ON — 也是 Neo4j 关系类型",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="关联类型名称",
        help_text="如 包含、运行、依赖",
    )
    src_to_dest_note = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="源→目标说明",
        help_text="如 '主机运行进程'",
    )
    dest_to_src_note = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="目标→源说明",
        help_text="如 '进程运行在主机上'",
    )
    direction = models.CharField(
        max_length=32, choices=DIRECTION_CHOICES,
        default='src_to_dest',
        verbose_name="方向",
    )

    class Meta:
        db_table = table_prefix + "cmdb_association_type"
        verbose_name = "关联类型"
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.asst_id})"


class ModelAssociation(CoreModel):
    """
    模型关联 (Association)
    对标 bk-cmdb Association。定义哪些模型之间可以建立哪种关联。
    """
    source_model = models.ForeignKey(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        related_name='src_assocs',
        verbose_name="源模型",
    )
    target_model = models.ForeignKey(
        'cmdb.ModelDefinition', on_delete=models.CASCADE,
        related_name='tgt_assocs',
        verbose_name="目标模型",
    )
    association_type = models.ForeignKey(
        AssociationType, on_delete=models.CASCADE,
        verbose_name="关联类型",
    )
    mapping = models.CharField(
        max_length=16, choices=MAPPING_CHOICES,
        default='1:n',
        verbose_name="映射基数",
    )
    on_delete = models.CharField(
        max_length=32, choices=ON_DELETE_CHOICES,
        default='none',
        verbose_name="级联删除策略",
        help_text="删除源节点时对目标节点的操作",
    )
    alias_name = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="别名",
    )
    is_pre = models.BooleanField(
        default=False,
        verbose_name="是否预置",
    )

    class Meta:
        db_table = table_prefix + "cmdb_model_association"
        verbose_name = "模型关联"
        verbose_name_plural = verbose_name
        unique_together = [['source_model', 'target_model', 'association_type']]

    def __str__(self):
        return f"{self.source_model.code} -[{self.association_type.asst_id}]-> {self.target_model.code}"
