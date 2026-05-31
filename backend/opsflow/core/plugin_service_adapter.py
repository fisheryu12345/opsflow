"""bamboo-engine 适配层 — 通用 PluginService

替换旧的 atom_service.py（按原子类型动态创建 N 个 Component/Service），
改为一个统一的 PluginService，运行时从 PLUGIN_REGISTRY 查找并调用 execute()。
"""

import logging

from pipeline.core.flow.activity import Service
from pipeline.component_framework.component import Component

from opsflow.plugins.registry import get_plugin

logger = logging.getLogger(__name__)


class PluginService(Service):
    """通用 Service — 所有原子通过这一个类路由到 BasePlugin.execute()"""

    def inputs_format(self):
        return []

    def outputs_format(self):
        return []

    def execute(self, data, parent_data):
        """执行插件 — 从 data.inputs 中提取 _atom_type 和参数"""
        inputs = dict(data.inputs)
        atom_type = inputs.pop('_atom_type', '')

        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            data.outputs['_result'] = False
            data.outputs['_error'] = f"未知插件: {atom_type}"
            logger.error("PluginService.execute: 未知插件 %s", atom_type)
            return False

        # 过滤内部字段
        params = {k: v for k, v in inputs.items() if not k.startswith('_')}

        try:
            instance = plugin_cls()
            result = instance.execute(**params)
            success = result.get('success', True)
            data.outputs.update({
                '_result': success,
                'stdout': result.get('data', {}).get('stdout', ''),
                'stderr': result.get('data', {}).get('stderr', ''),
                'executor_output': result.get('data', {}),
            })
            if not success:
                data.outputs['_error'] = result.get('error', '执行失败')
            return success
        except Exception as e:
            logger.exception("插件 %s 执行异常", atom_type)
            data.outputs['_result'] = False
            data.outputs['_error'] = str(e)
            return False

    def rollback(self, data, parent_data):
        inputs = dict(data.inputs)
        atom_type = inputs.pop('_atom_type', '')
        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            return False

        params = {k: v for k, v in inputs.items() if not k.startswith('_')}
        context = dict(data.outputs)
        try:
            instance = plugin_cls()
            result = instance.rollback(context=context, **params)
            return result.get('success', False)
        except Exception:
            logger.exception("插件 %s 回滚异常", atom_type)
            return False


# 注册唯一的 Component — ComponentMeta 元类自动处理注册
class OpsflowPluginComponent(Component):
    name = "OpsFlow Plugin"
    code = "opsflow_plugin"
    bound_service = PluginService
