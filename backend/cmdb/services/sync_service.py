# -*- coding: utf-8 -*-
from __future__ import annotations

"""CloudSyncService — 云厂商资产同步框架

提供从云厂商同步资产到 CMDB 的基础框架。
集成中心就绪后连接到具体云厂商 SDK。
"""

import logging
from abc import ABC, abstractmethod

from ..models.model_definition import ModelDefinition
from .import_service import ImportService

logger = logging.getLogger(__name__)


class BaseCloudSync(ABC):
    """云厂商资产同步基类"""

    def __init__(self, model_code: str = 'Host'):
        self.model_code = model_code
        self.model_def = ModelDefinition.objects.filter(code=model_code).first()
        self.import_service = ImportService()

    @abstractmethod
    def fetch_assets(self) -> list[dict]:
        """从云厂商获取资产列表（需子类实现）"""
        ...

    def sync(self, dry_run: bool = False) -> dict:
        """执行同步

        Args:
            dry_run: True 时只返回预览，不实际写入

        Returns:
            {total: N, created: N, updated: N, errors: [...]}
        """
        assets = self.fetch_assets()
        if not assets:
            logger.warning(f"云同步: 未获取到资产")
            return {'total': 0, 'created': 0, 'updated': 0, 'errors': []}

        # 字段映射
        mapped = [self._map_fields(asset) for asset in assets]

        if dry_run:
            return {'preview': mapped, 'total': len(mapped)}

        return self.import_service.import_instances(
            self.model_code, mapped, strategy='create_or_update'
        )

    def _map_fields(self, asset: dict) -> dict:
        """字段映射：云字段名 → CMDB ModelField.name（子类可重写）"""
        return asset


class AliyunSync(BaseCloudSync):
    """阿里云 ECS 同步"""

    def fetch_assets(self) -> list[dict]:
        """通过集成中心获取阿里云 ECS 列表"""
        # TODO: 通过集成中心 SDK 调用阿里云 API
        # from integration.services.aliyun import AliyunClient
        logger.info("阿里云同步: TODO — 待集成中心就绪")
        return []

    def _map_fields(self, asset: dict) -> dict:
        return {
            'ip': asset.get('VpcAttributes', {}).get('PrivateIpAddress', {}).get('IpAddress', [''])[0],
            'hostname': asset.get('HostName'),
            'os_type': 'linux',
            'region': asset.get('RegionId'),
            'cpu_cores': asset.get('Cpu'),
            'memory_mb': asset.get('Memory') * 1024 if asset.get('Memory') else 0,
            'cloud_instance_id': asset.get('InstanceId'),
        }


class TencentCloudSync(BaseCloudSync):
    """腾讯云 CVM 同步"""

    def fetch_assets(self) -> list[dict]:
        logger.info("腾讯云同步: TODO — 待集成中心就绪")
        return []
