"""bamboo-engine 适配层 — 通用 PluginService

替换旧的 atom_service.py（按原子类型动态创建 N 个 Component/Service），
改为一个统一的 PluginService，运行时从 PLUGIN_REGISTRY 查找并调用 execute()。

变量解析：PluginService 读取 parent_data 中的 global_vars / target_hosts，
并利用 variable_resolver 在节点参数中完成 ${key} 替换。
"""

import logging

from pipeline.core.flow.activity import Service
from pipeline.component_framework.component import Component

from opsflow.plugins.registry import get_plugin
from opsflow.core.variable_resolver import resolve_params

logger = logging.getLogger(__name__)


class PluginService(Service):
    """通用 Service — 所有原子通过这一个类路由到 BasePlugin.execute()"""

    def inputs_format(self):
        return []

    def outputs_format(self):
        return []

    def execute(self, data, parent_data):
        """执行插件 — 从 data.inputs 中提取 _atom_type 和参数

        支持:
          - 读取 parent_data 中的 global_vars / target_hosts
          - 在节点参数中解析 ${key} 变量引用
          - 设置 _result 及各项标准输出字段
        """
        inputs = dict(data.inputs)
        atom_type = inputs.pop('_atom_type', '')
        max_retries = inputs.pop('_max_retries', None)

        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            data.outputs['_result'] = False
            data.outputs['_error'] = f"未知插件: {atom_type}"
            logger.error("PluginService.execute: 未知插件 %s", atom_type)
            return False

        # 过滤内部字段（以 _ 开头的）
        params = {k: v for k, v in inputs.items() if not k.startswith('_')}

        # === 变量解析 ===
        pd = dict(parent_data.inputs) if parent_data else {}
        global_vars = pd.get('global_vars', {}) or {}
        target_hosts = pd.get('target_hosts', []) or []
        resolve_ctx = {}
        if isinstance(global_vars, dict):
            resolve_ctx.update(global_vars)
        resolve_ctx['target_hosts'] = target_hosts
        # 获取插件定义的变量类型映射
        var_types = plugin_cls.get_var_types() if hasattr(plugin_cls, 'get_var_types') else {}
        resolved_params = resolve_params(params, resolve_ctx, var_types=var_types)
        # === 变量解析结束 ===

        try:
            instance = plugin_cls()
            result = instance.execute(**resolved_params)
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

    @classmethod
    def need_schedule(cls) -> bool:
        """启用异步调度模式 — 允许 schedule() 回调

        始终返回 True，在 schedule() 中动态决定是否实际需要调度。
        同步插件在 schedule() 中直接返回 True（立即完成），
        异步插件在 schedule() 中轮询外部任务状态。
        """
        return True

    def schedule(self, data, parent_data, callback_data=None):
        """异步调度回调 — 长任务轮询/完成检查

        适用于 need_schedule=True 的异步插件（如 Tower 作业、K8s 部署）。
        同步插件直接返回 True。

        Args:
            callback_data: webhook 回调数据（未实现，预留）
        """
        inputs = dict(data.inputs)
        atom_type = inputs.get('_atom_type', '')

        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            return True  # 未知插件，直接结束

        # 同步插件 → 直接完成
        if not plugin_cls.need_schedule():
            return True

        params = {k: v for k, v in inputs.items() if not k.startswith('_')}
        context = dict(data.outputs)

        try:
            instance = plugin_cls()
            result = instance.schedule(context=context, **params)
            if result is None:
                return None   # 继续等待
            return bool(result)
        except Exception:
            logger.exception("插件 %s schedule 异常", atom_type)
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
