# -*- coding: utf-8 -*-
from __future__ import annotations

"""ImportService — 批量导入（CSV / JSON）

利用 Neo4j UNWIND + MERGE 实现高效的批量写入。
支持增量更新和批量关系创建。
"""

import csv
import io
import json
import logging
from uuid import uuid4
from datetime import datetime

from django.core.exceptions import ValidationError

from ..models.model_definition import ModelDefinition
from .neo4j_client import graph_driver
from .validation_service import ValidationService

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


class ImportService:
    """批量导入服务"""

    def import_instances(self, model_code: str,
                         records: list[dict],
                         strategy: str = 'create_or_update') -> dict:
        """批量导入实例

        Args:
            model_code: 目标模型 code
            records: 实例数据列表
            strategy: create_only / create_or_update

        Returns:
            {total: N, created: N, updated: N, errors: [...]}
        """
        model_def = ModelDefinition.objects.get(code=model_code)
        validator = ValidationService(model_def)

        validated_records = []
        errors = []
        now = _now_iso()

        for idx, record in enumerate(records):
            try:
                validated = validator.validate(record)
                validated['__updated_at'] = now
                if strategy == 'create_only':
                    # 为新记录生成 instance_id
                    validated['instance_id'] = str(uuid4())
                    validated['__model_code'] = model_code
                    validated['__created_at'] = now
                validated_records.append(validated)
            except ValidationError as e:
                errors.append({'index': idx, 'error': str(e)})

        if not validated_records:
            return {'total': 0, 'created': 0, 'updated': 0, 'errors': errors}

        if strategy == 'create_or_update':
            # 使用 MERGE 按 instance_id 或 唯一约束 更新
            cypher = (
                f"UNWIND $records AS rec "
                f"MERGE (n:{model_code} {{instance_id: rec.instance_id}}) "
                f"SET n += rec "
                f"RETURN count(n) as total"
            )
        else:
            # create_only: 直接 CREATE
            cypher = (
                f"UNWIND $records AS rec "
                f"CREATE (n:{model_code}) "
                f"SET n = rec "
                f"RETURN count(n) as total"
            )

        with graph_driver.session() as session:
            result = session.run(cypher, records=validated_records)
            total = result.single()['total'] if result else 0

        logger.info(f"批量导入 {model_code}: {total} 条记录, {len(errors)} 条错误")
        return {
            'total': total,
            'errors': errors,
        }

    def import_relations(self, relations: list[dict]) -> dict:
        """批量导入关联

        relations: [{src_id, dst_id, type}, ...]
        """
        if not relations:
            return {'total': 0, 'errors': []}

        now = _now_iso()
        for r in relations:
            r.setdefault('rel_id', str(uuid4()))
            r.setdefault('__created_at', now)

        cypher = (
            "UNWIND $rels AS r "
            "MATCH (src {instance_id: r.src_id}) "
            "MATCH (dst {instance_id: r.dst_id}) "
            "CALL apoc.merge.relationship("
            "  src, r.type, {}, {rel_id: r.rel_id}, dst"
            ") YIELD rel "
            "RETURN count(rel) as total"
        )

        try:
            with graph_driver.session() as session:
                result = session.run(cypher, rels=relations)
                total = result.single()['total'] if result else 0
            return {'total': total, 'errors': []}
        except Exception as e:
            logger.error(f"批量导入关联失败: {e}")
            return {'total': 0, 'errors': [str(e)]}

    def parse_csv(self, csv_content: str) -> list[dict]:
        """解析 CSV 内容为记录列表"""
        reader = csv.DictReader(io.StringIO(csv_content))
        return [dict(row) for row in reader]

    def parse_json(self, json_content: str) -> list[dict]:
        """解析 JSON 内容为记录列表"""
        data = json.loads(json_content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and 'records' in data:
            return data['records']
        raise ValidationError("JSON 格式无效：应为数组或 {records: [...]}")
