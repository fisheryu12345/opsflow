# -*- coding: utf-8 -*-
"""ValidationService — 字段类型校验 + 唯一约束检查

在创建/更新实例时校验字段值是否符合 ModelField 定义。
"""

import json
import logging
from datetime import datetime, date

from django.core.exceptions import ValidationError

from ..models.model_definition import ModelField
from ..models.object_unique import ObjectUnique
from .neo4j_client import graph_driver

logger = logging.getLogger(__name__)


class ValidationService:
    """字段校验服务

    根据 ModelDefinition 的 ModelField 定义校验输入数据：
    - 必填检查
    - 字段类型转换
    - enum 选项校验
    - 唯一约束检查
    """

    def __init__(self, model_def):
        self.model_def = model_def
        self.fields = {
            f.name: f for f in
            model_def.fields.all().select_related('group')
        }
        self.uniques = list(
            ObjectUnique.objects.filter(model_definition=model_def)
        )

    def validate(self, data: dict) -> dict:
        """校验并转换数据，返回清理后的数据字典"""
        validated = {}

        # 遍历所有字段定义
        for name, field_def in self.fields.items():
            raw_value = data.get(name)

            if raw_value is None and field_def.required:
                raise ValidationError(
                    f"'{field_def.label}' ({name}) 为必填字段"
                )

            if raw_value is None:
                validated[name] = field_def.default_value
                continue

            try:
                validated[name] = self._cast(raw_value, field_def)
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"字段 '{field_def.label}' 类型错误: {e}"
                )

        # 检查唯一约束
        self._check_uniques(validated)

        return validated

    def validate_update(self, data: dict) -> dict:
        """更新时的校验（部分字段可为空）"""
        validated = {}
        for name, field_def in self.fields.items():
            if name not in data:
                continue
            raw_value = data[name]
            if raw_value is None:
                validated[name] = None
                continue
            try:
                validated[name] = self._cast(raw_value, field_def)
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"字段 '{field_def.label}' 类型错误: {e}"
                )
        return validated

    def _cast(self, value, field_def: ModelField):
        """按 field_type 转换值"""
        ft = field_def.field_type

        if ft == 'string' or ft == 'ip':
            return str(value)

        elif ft == 'integer':
            return int(value)

        elif ft == 'float':
            return float(value)

        elif ft == 'boolean':
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)

        elif ft == 'date':
            if isinstance(value, date):
                return value.isoformat()
            return datetime.strptime(str(value)[:10], '%Y-%m-%d').date().isoformat()

        elif ft == 'datetime':
            if isinstance(value, datetime):
                return value.isoformat()
            return str(value)

        elif ft == 'enum':
            options = field_def.options or []
            if value not in options:
                raise ValueError(
                    f"'{value}' 不在可选范围内: {options}"
                )
            return value

        elif ft == 'json':
            if isinstance(value, (dict, list)):
                return value
            return json.loads(value)

        else:
            return str(value)

    def _check_uniques(self, validated: dict):
        """检查唯一约束：在 Neo4j 中查询是否已有相同值"""
        for unique in self.uniques:
            keys = unique.keys or []
            conditions = {}
            for k in keys:
                if k in validated:
                    conditions[k] = validated[k]

            if not conditions:
                continue

            # 构建 Neo4j 查询
            where_clauses = [
                f"n.{k} = ${k}" for k in conditions
            ]
            cypher = (
                f"MATCH (n:{self.model_def.code}) "
                f"WHERE {' AND '.join(where_clauses)} "
                f"RETURN count(n) as cnt"
            )
            with graph_driver.session() as session:
                result = session.run(cypher, **conditions)
                record = result.single()
                if record and record['cnt'] > 0:
                    field_names = ', '.join(
                        self.fields.get(k, k).label for k in keys
                    )
                    raise ValidationError(
                        f"唯一约束冲突: {field_names} 的组合值已存在"
                    )
