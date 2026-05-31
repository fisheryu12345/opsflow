"""插件注册中心 — 自动扫描 plugins/ 下所有 BasePlugin 子类

用法:
    from opsflow.plugins.registry import discover_plugins, get_plugin
    discover_plugins()           # 启动时调用
    plugin_cls = get_plugin(code)  # 运行时查找
"""

import importlib
import logging
import pkgutil
from typing import Dict, List, Optional, Type

from opsflow.plugins.base import BasePlugin

logger = logging.getLogger(__name__)

# 全局注册表
PLUGIN_REGISTRY: Dict[str, Type[BasePlugin]] = {}   # code → class
PLUGIN_GROUP_MAP: Dict[str, List[str]] = {}          # group → [code, ...]


def discover_plugins():
    """扫描 opsflow/plugins/ 下所有模块，自动注册 BasePlugin 子类"""
    import opsflow.plugins as plugins_pkg

    count = 0
    for importer, modname, ispkg in pkgutil.walk_packages(
        plugins_pkg.__path__, plugins_pkg.__name__ + "."
    ):
        if ispkg:
            continue
        try:
            module = importlib.import_module(modname)
        except Exception as e:
            logger.warning("加载插件模块 %s 失败: %s", modname, e)
            continue

        for attr_name in dir(module):
            cls = getattr(module, attr_name)
            if (isinstance(cls, type) and issubclass(cls, BasePlugin)
                    and cls is not BasePlugin):
                code = cls.code or cls.name
                if code in PLUGIN_REGISTRY:
                    logger.warning("插件 code 重复: %s", code)
                PLUGIN_REGISTRY[code] = cls
                PLUGIN_GROUP_MAP.setdefault(cls.group, []).append(code)
                count += 1

    logger.info("插件注册完成: 共 %d 个, %d 个分组", count, len(PLUGIN_GROUP_MAP))


def get_plugin(code: str) -> Optional[Type[BasePlugin]]:
    return PLUGIN_REGISTRY.get(code)


def get_all_plugins() -> Dict[str, Type[BasePlugin]]:
    return dict(PLUGIN_REGISTRY)


def get_plugins_by_group(group: str) -> List[Type[BasePlugin]]:
    return [PLUGIN_REGISTRY[c] for c in PLUGIN_GROUP_MAP.get(group, []) if c in PLUGIN_REGISTRY]


def get_all_groups() -> dict:
    """返回 {group_name: [{"code": ..., "name": ...}, ...]}"""
    result = {}
    for group, codes in PLUGIN_GROUP_MAP.items():
        result[group] = [
            {"code": c, "name": PLUGIN_REGISTRY[c].name}
            for c in codes if c in PLUGIN_REGISTRY
        ]
    return result


def _form_config_to_list(form_config) -> list:
    """将 FormConfig（Pydantic 对象列表）转为纯 list/dict"""
    if not form_config:
        return []
    return [item.model_dump() for item in form_config]


def sync_plugin_meta_to_db():
    """将 PLUGIN_REGISTRY 中的插件元数据同步到 PluginMeta 表"""
    from opsflow.models import PluginMeta

    for code, cls in PLUGIN_REGISTRY.items():
        form_schema = _form_config_to_list(cls.get_form_config())
        output_schema = cls.get_output_schema()

        PluginMeta.objects.update_or_create(
            code=code,
            defaults={
                "name": cls.name,
                "group": cls.group,
                "version": cls.version,
                "description": cls.description,
                "risk_level": cls.risk_level,
                "form_schema": form_schema,
                "output_schema": output_schema,
                "is_active": True,
            },
        )
    logger.info("PluginMeta 同步完成: %d 条", len(PLUGIN_REGISTRY))
