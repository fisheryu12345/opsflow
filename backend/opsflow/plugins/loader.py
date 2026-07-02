"""Plugin 热加载器 — 文件快照 + 增量注册

通过文件系统的 mtime/size 快照检测新增 .py 文件，
动态 import 并注册 BasePlugin 子类到 PLUGIN_REGISTRY。
无后台轮询，仅显式触发（API / 管理命令）。

用法:
    from opsflow.plugins.loader import PluginLoader
    from opsflow.plugins.registry import PLUGIN_REGISTRY, PLUGIN_GROUP_MAP
    loader = PluginLoader(PLUGIN_REGISTRY, PLUGIN_GROUP_MAP)
    count = loader.scan()  # 增量注册新插件
"""

import importlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from opsflow.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class PluginLoader:
    """插件热加载器

    管理文件系统快照，支持增量发现和注册新增插件。
    不对已有模块做 reload，仅处理新增 .py 文件。

    维护 _revision 自增计数器，每次 scan() 发现新插件时 +1。
    """

    def __init__(self, registry: Dict, group_map: Dict):
        """
        Args:
            registry: 外部 dict 引用（registry.PLUGIN_REGISTRY），
                      扫描结果原地写入，调用方立即可见
            group_map: 外部 dict 引用（registry.PLUGIN_GROUP_MAP）
        """
        self._registry = registry
        self._group_map = group_map
        self._snapshots: Dict[str, Tuple[float, int]] = {}  # abs_path → (mtime, size)
        self._revision: int = 0

        # 扫描根目录 opsflow/plugins/
        import opsflow.plugins as plugins_pkg
        self.base_dir = Path(plugins_pkg.__file__).parent.resolve()
        logger.info("PluginLoader base_dir: %s", self.base_dir)

    # ── 公开 API ─────────────────────────────────────────────────

    def scan(self) -> int:
        """扫描插件目录，注册新插件

        Returns:
            int: 本次新增插件数量
        """
        if not self.base_dir.is_dir():
            logger.warning("PluginLoader: directory not found: %s", self.base_dir)
            return 0

        new_count = 0
        current_files: Dict[str, Tuple[float, int]] = {}

        for py_file in self.base_dir.rglob('*.py'):
            # 跳过 __init__.py 和 __pycache__ 下的文件
            if py_file.name == '__init__.py':
                continue
            if '__pycache__' in py_file.parts:
                continue

            abs_path = str(py_file.resolve())
            stat = self._get_stat(py_file)
            current_files[abs_path] = stat

            # 已在快照中 → 跳过（不支持更新已有插件）
            if abs_path in self._snapshots:
                continue

            # 新文件 → 尝试导入注册
            module_path = self._path_to_module(py_file)
            if not module_path:
                continue

            try:
                module = importlib.import_module(module_path)
            except Exception as e:
                logger.warning("PluginLoader import failed %s: %s", module_path, e)
                continue

            # 查找 BasePlugin 子类并注册
            count = self._register_from_module(module, module_path)
            new_count += count

        # 更新快照
        self._snapshots = current_files

        if new_count > 0:
            self._revision += 1
            logger.info("PluginLoader scan: %d new plugins, revision=%d",
                        new_count, self._revision)

        return new_count

    def get_revision(self) -> int:
        """获取当前 revision（每次 scan 新增时 +1）"""
        return self._revision

    # ── 内部方法 ─────────────────────────────────────────────────

    def _path_to_module(self, file_path: Path) -> Optional[str]:
        """将文件路径转为 Python 模块路径

        e.g. /path/to/opsflow/plugins/ansible/shell.py → opsflow.plugins.ansible.shell
        """
        try:
            rel = file_path.relative_to(self.base_dir)
        except ValueError:
            return None
        parts = rel.with_suffix('').parts
        return 'opsflow.plugins.' + '.'.join(parts)

    def _register_from_module(self, module, module_path: str) -> int:
        """扫描模块中的 BasePlugin 子类并注册到 PLUGIN_REGISTRY"""
        count = 0
        for attr_name in dir(module):
            cls = getattr(module, attr_name)
            if (isinstance(cls, type) and issubclass(cls, BasePlugin)
                    and cls is not BasePlugin):
                code = cls.code or cls.name
                if code.startswith('_'):
                    continue  # Skip internal/abstract base classes (e.g. _tower_base)
                version = cls.version or "v1.0"

                if code not in self._registry:
                    self._registry[code] = {}
                if version in self._registry.get(code, {}):
                    logger.warning("PluginLoader plugin code=%s version=%s duplicate, skip",
                                   code, version)
                    continue

                self._registry.setdefault(code, {})[version] = cls
                if code not in self._group_map.get(cls.group, []):
                    self._group_map.setdefault(cls.group, []).append(code)
                count += 1
                logger.info("PluginLoader register plugin: %s (%s)",
                            code, module_path)

        return count

    @staticmethod
    def _get_stat(path: Path) -> Tuple[float, int]:
        st = path.stat()
        return (st.st_mtime, st.st_size)
