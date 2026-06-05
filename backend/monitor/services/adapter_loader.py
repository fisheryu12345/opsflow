# -*- coding: utf-8 -*-
"""SPI Adapter Loader — 从 settings 配置加载适配器实例

支持 data_source / notify / action / target_resolver 四类适配器
"""

import logging
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)
FSM = 'adapter_loader'


class AdapterLoader:
    """适配器加载器 — 根据 settings.MONITOR_ADAPTERS 加载适配器"""

    @classmethod
    def get_adapter(cls, category: str, key: str, instance_config: dict = None):
        """
        获取适配器实例

        Args:
            category: datasource / notify / action / target_resolver
            key: 适配器标识 (prometheus / wecom / opsflow / cmdb)
            instance_config: 适配器配置参数

        Returns:
            适配器实例 or None
        """
        adapters = getattr(settings, 'MONITOR_ADAPTERS', {}).get(category, {})
        class_path = adapters.get(key)
        if not class_path:
            logger.warning(f"Adapter not found: {category}/{key}")
            return None
        try:
            cls_obj = import_string(class_path)
            return cls_obj(instance_config or {})
        except (ImportError, AttributeError) as e:
            logger.error(f"Load adapter failed {class_path}: {e}")
            return None

    @classmethod
    def list_adapters(cls, category: str) -> list:
        """列出某类别的所有注册适配器"""
        adapters = getattr(settings, 'MONITOR_ADAPTERS', {}).get(category, {})
        return [{'key': k, 'class_path': v} for k, v in adapters.items()]
