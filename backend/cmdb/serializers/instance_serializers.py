# -*- coding: utf-8 -*-
"""Serializers for Neo4j dynamic instances

Neo4j 节点不是 Django ORM 模型，所以使用标准 DRF Serializer。
DynamicInstanceSerializer 根据 ModelDefinition 的字段动态生成序列化字段。
"""

from rest_framework import serializers


class DynamicInstanceSerializer(serializers.Serializer):
    """动态实例序列化器

    根据 ModelDefinition 的 ModelField 定义动态生成字段。
    使用方式：在 ViewSet 中调用 get_serializer() 前设置 fields 参数。
    """
    instance_id = serializers.CharField(read_only=True)
    __model_code = serializers.CharField(read_only=True)
    __created_at = serializers.CharField(read_only=True)
    __updated_at = serializers.CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        # 允许传入 field_defs 动态生成字段
        field_defs = kwargs.pop('field_defs', None)
        super().__init__(*args, **kwargs)

        if field_defs:
            for fd in field_defs:
                field_name = fd['name']
                required = fd.get('required', False)
                field_type = fd.get('field_type', 'string')

                if field_name in self.fields:
                    continue  # 不覆盖系统字段

                if field_type == 'integer':
                    self.fields[field_name] = serializers.IntegerField(
                        required=required, allow_null=True
                    )
                elif field_type == 'float':
                    self.fields[field_name] = serializers.FloatField(
                        required=required, allow_null=True
                    )
                elif field_type == 'boolean':
                    self.fields[field_name] = serializers.BooleanField(
                        required=required, allow_null=True
                    )
                elif field_type == 'enum':
                    options = fd.get('options', [])
                    self.fields[field_name] = serializers.ChoiceField(
                        choices=[(o, o) for o in options],
                        required=required, allow_null=True,
                    )
                elif field_type == 'json':
                    self.fields[field_name] = serializers.JSONField(
                        required=required, allow_null=True
                    )
                else:
                    self.fields[field_name] = serializers.CharField(
                        required=required, allow_null=True,
                        max_length=512,
                    )


class InstanceRelationSerializer(serializers.Serializer):
    """实例关联序列化器"""
    rel_id = serializers.CharField(read_only=True)
    asst_type = serializers.CharField()
    src_id = serializers.CharField()
    dst_id = serializers.CharField()
    src_model = serializers.CharField(read_only=True)
    dst_model = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
