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

# 全局注册表 — 多版本: code → {version: class}
PLUGIN_REGISTRY: Dict[str, Dict[str, Type[BasePlugin]]] = {}
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
                version = cls.version or "v1.0"
                if code not in PLUGIN_REGISTRY:
                    PLUGIN_REGISTRY[code] = {}
                if version in PLUGIN_REGISTRY.get(code, {}):
                    logger.warning("插件 code=%s version=%s 重复", code, version)
                PLUGIN_REGISTRY.setdefault(code, {})[version] = cls
                if code not in PLUGIN_GROUP_MAP.get(cls.group, []):
                    PLUGIN_GROUP_MAP.setdefault(cls.group, []).append(code)
                count += 1

    logger.info("插件注册完成: 共 %d 个, %d 个分组, %d 个 code",
                 count, len(PLUGIN_GROUP_MAP), len(PLUGIN_REGISTRY))


def get_plugin(code: str, version: str = None) -> Optional[Type[BasePlugin]]:
    """获取插件类，version=None 时返回最新版本"""
    versions = PLUGIN_REGISTRY.get(code)
    if not versions:
        return None
    if version and version in versions:
        return versions[version]
    # 无版本参数 → 返回最新版本
    sorted_versions = sorted(versions.keys())
    return versions[sorted_versions[-1]] if sorted_versions else None


def get_plugin_versions(code: str) -> List[str]:
    """返回指定 code 的所有版本列表"""
    versions = PLUGIN_REGISTRY.get(code)
    return sorted(versions.keys()) if versions else []


def get_all_plugins() -> Dict[str, Dict[str, Type[BasePlugin]]]:
    return {code: dict(vs) for code, vs in PLUGIN_REGISTRY.items()}


def get_plugins_by_group(group: str) -> List[Type[BasePlugin]]:
    """返回分组的所有插件（每个 code 的最新版本）"""
    result = []
    for c in PLUGIN_GROUP_MAP.get(group, []):
        versions = PLUGIN_REGISTRY.get(c, {})
        if versions:
            sorted_v = sorted(versions.keys())
            result.append(versions[sorted_v[-1]])
    return result


def get_all_groups() -> dict:
    """返回 {group_name: [{"code": ..., "name": ..., "versions": [...]}, ...]}"""
    result = {}
    for group, codes in PLUGIN_GROUP_MAP.items():
        result[group] = []
        for c in codes:
            versions = PLUGIN_REGISTRY.get(c, {})
            if versions:
                sorted_v = sorted(versions.keys())
                latest = versions[sorted_v[-1]]
                result[group].append({
                    "code": c,
                    "name": latest.name,
                    "version": latest.version,
                    "versions": sorted_v,
                })
    return result


def _form_config_to_list(form_config) -> list:
    """将 FormConfig（Pydantic 对象列表）转为纯 list/dict"""
    if not form_config:
        return []
    return [item.model_dump() for item in form_config]


def discover_variables():
    """导入 variables 包触发所有变量类注册到 VARIABLE_REGISTRY"""
    try:
        from opsflow.core import variables  # noqa: F401
    except Exception as e:
        logger.warning("加载变量类型失败: %s", e)


def _resolve_group_icon_color(cls) -> tuple:
    """返回插件级 icon/color（默认空，前端维护 Group→图标映射）"""
    return cls.icon or "", cls.color or ""


def sync_plugin_meta_to_db():
    """将 PLUGIN_REGISTRY 中的插件元数据同步到 PluginMeta 表（支持多版本）"""
    from opsflow.models import PluginMeta

    count = 0
    for code, versions in PLUGIN_REGISTRY.items():
        for version, cls in versions.items():
            if not isinstance(cls, type):
                logger.warning('sync_plugin_meta_to_db: skipping non-class item code=%s version=%s type=%s', code, version, type(cls).__name__)
                continue
            try:
                form_schema = _form_config_to_list(cls.get_form_config())
                output_schema = cls.get_output_schema()
            except Exception as e:
                logger.error('sync_plugin_meta_to_db: plugin %s v%s config failed: %s', code, version, e)
                continue

            icon, color = _resolve_group_icon_color(cls)

            # 同步时保留已有 phase（不重置），新建时默认 PHASE_AVAILABLE
            existing = PluginMeta.objects.filter(code=code, version=version).first()
            defaults = {
                "name": cls.name,
                "group": cls.group,
                "description": cls.description,
                "risk_level": cls.risk_level,
                "icon": icon,
                "color": color,
                "form_schema": form_schema,
                "output_schema": output_schema,
                "is_active": True,
            }
            if not existing:
                defaults["phase"] = PluginMeta.PHASE_AVAILABLE
            PluginMeta.objects.update_or_create(
                code=code,
                version=version,
                defaults=defaults,
            )
            count += 1
    logger.info("PluginMeta 同步完成: %d 条", count)
