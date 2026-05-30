"""原子执行器工厂 — 根据 executor_type 动态加载对应执行器

设计思路:
  bamboo-engine 的 Service 层不需要知道底层是 Ansible、ESXi 还是 NetApp。
  只需传入 atom_name, executor_type, inputs，工厂自动路由到正确的执行器。
"""

import importlib
import logging
from typing import Optional

from .base import BaseExecutor, ExecuteResult
from ..atom_registry import get_atom_meta

logger = logging.getLogger(__name__)

# 执行器类注册表: executor_type → "module.path.ClassName"
EXECUTOR_CLASSES: dict[str, str] = {
    "ansible": "opsflow.core.executors.ansible_executor.AnsibleExecutor",
    "esxi": "opsflow.core.executors.esxi_executor.EsxiExecutor",
    "netapp": "opsflow.core.executors.netapp_executor.NetAppExecutor",
    "servicenow": "opsflow.core.executors.servicenow_executor.ServiceNowExecutor",
    "redfish": "opsflow.core.executors.redfish_executor.RedfishExecutor",
    "http": "opsflow.core.executors.http_executor.HttpExecutor",
    "test": "opsflow.core.executors.test_executor.TestExecutor",
}


class AtomExecutorFactory:
    """原子执行器工厂 — 缓存已加载的执行器实例"""

    _instances: dict[str, BaseExecutor] = {}

    @classmethod
    def get_executor(cls, executor_type: str) -> Optional[BaseExecutor]:
        """获取执行器实例（惰性加载 + 缓存）"""
        if executor_type in cls._instances:
            return cls._instances[executor_type]

        class_path = EXECUTOR_CLASSES.get(executor_type)
        if not class_path:
            logger.error("未知 executor_type: %s", executor_type)
            return None

        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            executor_cls = getattr(module, class_name)
            instance = executor_cls()
            cls._instances[executor_type] = instance
            return instance
        except (ImportError, AttributeError) as e:
            logger.exception("加载执行器 %s 失败: %s", executor_type, e)
            return None

    @classmethod
    def execute_atom(cls, atom_name: str, inputs: dict,
                     target_hosts: Optional[list] = None) -> ExecuteResult:
        """统一执行入口 — 被 bamboo-engine Service 调用

        流程:
          1. 从 atom_registry 读取 meta
          2. 根据 executor_type 获取执行器
          3. 校验输入
          4. 执行
          5. 校验输出
        """
        meta = get_atom_meta(atom_name)
        if not meta:
            return ExecuteResult(False, {}, f"未知原子: {atom_name}")

        executor_type = meta.executor_type or "ansible"
        executor = cls.get_executor(executor_type)
        if not executor:
            return ExecuteResult(False, {},
                                 f"无法加载执行器: {executor_type} (原子 {atom_name})")

        # 注入 target_hosts 到 inputs
        merged = dict(inputs)
        if target_hosts:
            merged["_target_hosts"] = target_hosts

        # 输入校验
        errors = executor.validate_inputs(meta.inputs, merged)
        if errors:
            return ExecuteResult(False, {}, "; ".join(errors))

        # 执行
        try:
            result = executor.execute(merged)
            return result
        except Exception as e:
            logger.exception("原子 %s 执行异常", atom_name)
            return ExecuteResult(False, {}, str(e))

    @classmethod
    def rollback_atom(cls, atom_name: str, inputs: dict,
                      context: dict) -> ExecuteResult:
        """统一回滚入口"""
        meta = get_atom_meta(atom_name)
        if not meta:
            return ExecuteResult(False, {}, f"未知原子: {atom_name}")

        executor_type = meta.executor_type or "ansible"
        executor = cls.get_executor(executor_type)
        if not executor:
            return ExecuteResult(False, {},
                                 f"无法加载回滚执行器: {executor_type}")

        try:
            result = executor.rollback(inputs, context)
            return result
        except Exception as e:
            logger.exception("原子 %s 回滚异常", atom_name)
            return ExecuteResult(False, {}, str(e))
