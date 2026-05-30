"""bamboo-pipeline Component 注册 — 将 opsflow 原子注册为 pipeline Component

每个 ATOM_REGISTRY 中的原子会被动态创建为一个 Component 子类，
通过 ComponentMeta 元类自动注册到 ComponentLibrary 和 ComponentModel。
BambooDjangoRuntime 在运行时通过 get_service() 将 Component 解析为 Service 实例。
"""

import logging

from pipeline.core.flow.activity import Service
from pipeline.core.flow.io import InputItem, OutputItem
from pipeline.component_framework.component import Component

from .atom_registry import ATOM_REGISTRY
from .executors import AtomExecutorFactory, ExecuteResult

logger = logging.getLogger(__name__)


class AnsibleAtomService(Service):
    """bamboo-pipeline Service 基类 — 所有原子共享此实现，通过 _atom_name 区分类型"""

    def inputs_format(self):
        return [
            InputItem(name="原子类型", key="_atom_type", type="string", required=True,
                      schema=None),
            InputItem(name="目标主机", key="target_hosts", type="array", required=False,
                      schema=None),
        ]

    def outputs_format(self):
        return [
            OutputItem(name="标准输出", key="stdout", type="string", schema=None),
            OutputItem(name="错误输出", key="stderr", type="string", schema=None),
            OutputItem(name="返回码", key="returncode", type="int", schema=None),
            OutputItem(name="错误信息", key="_error", type="string", schema=None),
            OutputItem(name="执行器原始数据", key="executor_output", type="object", schema=None),
        ]

    def execute(self, data, parent_data):
        """执行原子操作

        :param data: DataObject — 节点输入输出数据（inputs 已由 Component.data_for_execution 解析）
        :param parent_data: DataObject — 根流程数据
        :return: bool
        """
        params = dict(data.inputs)
        target_hosts = list(parent_data.inputs.get('target_hosts', []))
        atom_name = getattr(self, '_atom_name', 'unknown')

        try:
            result: ExecuteResult = AtomExecutorFactory.execute_atom(
                atom_name=atom_name,
                inputs={**params, '_atom_type': atom_name},
                target_hosts=target_hosts,
            )
            data.outputs.update({
                'stdout': result.data.get('stdout', ''),
                'stderr': result.data.get('stderr', ''),
                'returncode': result.data.get('returncode', 0) if result.success else -1,
                '_result': result.success,
                'executor_output': result.data,
            })
            if not result.success:
                data.outputs['_error'] = result.error
            return result.success
        except Exception as e:
            logger.exception(f"原子 {atom_name} 执行失败: {e}")
            data.outputs['_result'] = False
            data.outputs['_error'] = str(e)
            return False


def register_atom_services():
    """遍历 ATOM_REGISTRY，为每个原子动态创建 Component + Service 子类

    Component 的元类 ComponentMeta 自动完成以下操作：
      1. 注册到 ComponentLibrary（全局组件库）
      2. 创建/更新 ComponentModel 数据库记录
    """
    count = 0
    for name, meta in ATOM_REGISTRY.items():
        code = meta.component_code or f"opsflow_{name}"

        # 为每个原子创建独立的 Service 子类（携带 _atom_name 供 execute 识别）
        service_cls = type(
            f"{name.title()}Service",
            (AnsibleAtomService,),
            {'_atom_name': name, '__module__': __name__},
        )

        # 创建 Component 子类，绑定专属 Service — ComponentMeta 自动注册
        type(f"{name.title()}Component", (Component,), {
            'name': name,
            'code': code,
            'bound_service': service_cls,
            '__module__': __name__,
        })
        count += 1

    logger.info(f"pipeline Component 注册完成: 共 {count} 个组件")
