"""bamboo-engine Service 实现 — 将原子注册为 bamboo-engine 组件"""

import json
import logging
from typing import Optional

from bamboo_engine.eri import ExecutionData, Schedule, CallbackData
from bamboo_engine.eri.interfaces import Service, ScheduleType
from bamboo_engine.eri import HookType

from .atom_registry import ATOM_REGISTRY, get_atom_meta
from . import ansible_trigger

logger = logging.getLogger(__name__)

# 全局 Service 注册表
SERVICE_REGISTRY: dict[str, type['AnsibleAtomService']] = {}


class AnsibleAtomService(Service):
    """bamboo-engine Service 基类 — 所有原子共享此基类，通过 component_code 区分"""

    def __init__(self, component_code: str):
        self._component_code = component_code
        self._atom_type = self._resolve_atom_type(component_code)
        self._meta = get_atom_meta(self._atom_type)

    @staticmethod
    def _resolve_atom_type(component_code: str) -> str:
        """从 component_code 反查 atom_type"""
        for name, meta in ATOM_REGISTRY.items():
            if meta.component_code == component_code:
                return name
        return component_code.replace('opsflow_', '')

    # ---- Service 接口实现 ----

    def execute(self, data: ExecutionData, root_pipeline_data: ExecutionData) -> bool:
        """执行原子操作，返回 True=成功 / False=失败"""
        params = dict(data.inputs)
        target_hosts = params.pop('target_hosts', [])
        node = {
            'id': params.pop('_node_id', ''),
            'atom_type': self._atom_type,
            'params': params,
        }
        try:
            result = ansible_trigger.execute_atom(node, target_hosts)
            data.outputs.update({
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
                'returncode': result.get('returncode', 0),
                '_result': result.get('returncode', 0) == 0,
            })
            return result.get('returncode', 0) == 0
        except Exception as e:
            logger.exception(f"原子 {self._atom_type} 执行失败: {e}")
            data.outputs['_result'] = False
            data.outputs['_error'] = str(e)
            return False

    def schedule(self, schedule: Schedule, data: ExecutionData,
                 root_pipeline_data: ExecutionData,
                 callback_data: Optional[CallbackData] = None) -> bool:
        """轮询/回调执行结果（仅在 need_schedule 返回 True 时被调用）"""
        try:
            job_id = data.outputs.get('job_id')
            if callback_data:
                result = json.loads(callback_data.data)
            else:
                result = ansible_trigger.poll_job(job_id)
            data.outputs.update({
                'stdout': result.get('stdout', ''),
                'stderr': result.get('stderr', ''),
                'returncode': result.get('returncode', 0),
                '_result': result.get('returncode', 0) == 0,
            })
            return result.get('returncode', 0) == 0
        except Exception as e:
            logger.exception(f"原子 {self._atom_type} 调度失败: {e}")
            data.outputs['_result'] = False
            return False

    def need_schedule(self) -> bool:
        """当前 mock 模式返回 False；生产（有 job_id）返回 True"""
        return False

    def schedule_type(self) -> Optional[ScheduleType]:
        return ScheduleType.POLL

    def is_schedule_done(self) -> bool:
        return True

    def schedule_after(self, schedule: Optional[Schedule], data: ExecutionData,
                       root_pipeline_data: ExecutionData) -> int:
        return 10

    def need_run_hook(self) -> bool:
        return False

    def hook_dispatch(self, hook: HookType, data: ExecutionData,
                      root_pipeline_data: ExecutionData,
                      callback_data: Optional[CallbackData] = None) -> bool:
        return True

    def setup_runtime_attributes(self, **attrs):
        pass


def create_service(component_code: str) -> AnsibleAtomService:
    """工厂方法 — 根据 component_code 创建对应的 AnsibleAtomService"""
    return SERVICE_REGISTRY.get(component_code, AnsibleAtomService)(component_code)


def register_atom_services():
    """遍历 ATOM_REGISTRY，将每个原子注册到全局 SERVICE_REGISTRY"""
    count = 0
    for name, meta in ATOM_REGISTRY.items():
        code = meta.component_code or f"opsflow_{name}"
        SERVICE_REGISTRY[code] = AnsibleAtomService
        count += 1
    logger.info(f"bamboo-engine Service 注册完成: 共 {count} 个组件")


def get_service(code: str, version: str | None = None, name: str | None = None) -> AnsibleAtomService | None:
    """供 bamboo-engine runtime 调用的 Service 查找接口"""
    service_cls = SERVICE_REGISTRY.get(code)
    if service_cls:
        return service_cls(code)
    return None
