# -*- coding: utf-8 -*-
from __future__ import annotations

"""CloudSyncService — 云厂商资产同步框架"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from ..models.model_definition import ModelDefinition
from ..models.cloud_sync_log import CloudSyncLog
from .import_service import ImportService

logger = logging.getLogger(__name__)


def _get_connector_region() -> str:
    """返回一个任意可用地域（仅用于 DescribeRegions 引导调用）"""
    return 'cn-hangzhou'


class BaseCloudSync(ABC):
    """云厂商资产同步基类"""

    def __init__(self, model_code: str = 'Host'):
        self.model_code = model_code
        self.model_def = ModelDefinition.objects.filter(code=model_code).first()
        self.import_service = ImportService()
        self._provider = 'unknown'

    @abstractmethod
    def fetch_assets(self) -> list[dict]:
        ...

    def sync(self, dry_run: bool = False, triggered_by: str = 'schedule') -> dict:
        """执行同步并记录日志

        Args:
            dry_run: True 时只返回预览，不实际写入
            triggered_by: schedule / manual / pipeline

        Returns:
            {total: N, created: N, updated: N, errors: [...]}
        """
        # 创建同步日志
        log_entry = CloudSyncLog.objects.create(
            provider=self._provider,
            status='running',
            triggered_by=triggered_by,
        )

        try:
            assets = self.fetch_assets()
            if not assets:
                logger.warning(f"云同步({self._provider}): 未获取到资产")
                log_entry.status = 'success'
                log_entry.finished_at = datetime.now()
                log_entry.save(update_fields=['status', 'finished_at'])
                return {'total': 0, 'created': 0, 'updated': 0, 'errors': []}

            mapped = [self._map_fields(asset) for asset in assets]

            if dry_run:
                log_entry.status = 'success'
                log_entry.finished_at = datetime.now()
                log_entry.total = len(mapped)
                log_entry.save(update_fields=['status', 'finished_at', 'total'])
                return {'preview': mapped, 'total': len(mapped)}

            result = self.import_service.import_instances(
                self.model_code, mapped, strategy='create_or_update'
            )

            # 更新日志
            log_entry.status = 'failed' if result.get('errors') else 'success'
            log_entry.finished_at = datetime.now()
            log_entry.total = result.get('total', 0)
            log_entry.error_count = len(result.get('errors', []))
            log_entry.errors = result.get('errors', [])
            log_entry.save(update_fields=[
                'status', 'finished_at', 'total', 'error_count', 'errors',
            ])

            return result

        except Exception as e:
            logger.exception(f"云同步({self._provider})异常")
            log_entry.status = 'failed'
            log_entry.finished_at = datetime.now()
            log_entry.errors = [{'error': str(e)}]
            log_entry.error_count = 1
            log_entry.save(update_fields=['status', 'finished_at', 'errors', 'error_count'])
            return {'total': 0, 'created': 0, 'updated': 0, 'errors': [str(e)]}

    def _map_fields(self, asset: dict) -> dict:
        return asset


class AliyunSync(BaseCloudSync):
    """阿里云 ECS 同步 — 全地域"""

    def __init__(self):
        super().__init__()
        self._provider = 'aliyun'

    def fetch_assets(self) -> list[dict]:
        from opsflow.plugins.aliyun_ecs._client import get_ecs_client
        from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
        from aliyunsdkecs.request.v20140526.DescribeRegionsRequest import DescribeRegionsRequest

        region = _get_connector_region()
        client = get_ecs_client(region)

        regions_req = DescribeRegionsRequest()
        regions_resp = client.do_action_with_exception(regions_req)
        regions_data = json.loads(regions_resp)
        all_regions = [r['RegionId'] for r in regions_data.get('Regions', {}).get('Region', []) if r.get('RegionId')]
        logger.info("阿里云同步: 发现 %d 个可用地域", len(all_regions))

        instances = []
        for reg in all_regions:
            reg_client = get_ecs_client(reg)
            page_number = 1
            page_size = 100
            while True:
                req = DescribeInstancesRequest()
                req.set_PageSize(page_size)
                req.set_PageNumber(page_number)
                resp = reg_client.do_action_with_exception(req)
                data = json.loads(resp)
                page_instances = data.get('Instances', {}).get('Instance', [])
                if not page_instances:
                    break
                instances.extend(page_instances)
                total = int(data.get('TotalCount', 0))
                if page_number * page_size >= total:
                    break
                page_number += 1

        logger.info("阿里云同步: 全地域共 %d 台 ECS 实例", len(instances))
        return instances

    def _map_fields(self, asset: dict) -> dict:
        vpc = asset.get('VpcAttributes', {}) or {}
        ips = vpc.get('PrivateIpAddress', {}).get('IpAddress', [])
        cloud_id = asset.get('InstanceId', '')
        aliyun_status = asset.get('Status', '')
        status_map = {
            'Running': 'normal', 'Starting': 'normal',
            'Stopped': 'offline', 'Stopping': 'maintenance',
            'Deleted': 'offline',
        }
        return {
            'instance_id': cloud_id,
            'cloud_instance_id': cloud_id,
            'cloud_type': 'aliyun',
            'instance_type': asset.get('InstanceType', ''),
            'ip': ips[0] if ips else '',
            'hostname': asset.get('InstanceName', '') or asset.get('HostName', '') or '',
            'region': asset.get('RegionId', ''),
            'status': status_map.get(aliyun_status, 'unknown'),
            'os_type': 'linux',
            'cpu_cores': asset.get('Cpu', 0),
            'memory_mb': (asset.get('Memory', 0) or 0) * 1024,
        }


class TencentCloudSync(BaseCloudSync):
    """腾讯云 CVM 同步"""

    def __init__(self):
        super().__init__()
        self._provider = 'tencent'

    def fetch_assets(self) -> list[dict]:
        logger.info("腾讯云同步: TODO — 待集成中心就绪")
        return []
