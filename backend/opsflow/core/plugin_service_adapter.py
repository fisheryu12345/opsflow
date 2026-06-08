"""bamboo-engine 适配层 — 通用 PluginService

替换旧的 atom_service.py（按原子类型动态创建 N 个 Component/Service），
改为一个统一的 PluginService，运行时从 PLUGIN_REGISTRY 查找并调用 execute()。

变量解析：PluginService 读取 parent_data 中的 global_vars / target_hosts，
并利用 variable_resolver 在节点参数中完成 ${key} 替换。
"""

import json
import logging

from pipeline.core.flow.activity import Service
from pipeline.component_framework.component import Component

from opsflow.plugins.registry import get_plugin
from opsflow.core.variable_resolver import resolve_params

logger = logging.getLogger(__name__)


def _extract_params(data):
    """从 data.inputs 中提取 _atom_type/_plugin_version/_max_retries 和用户参数"""
    inputs = dict(data.inputs)
    atom_type = inputs.pop('_atom_type', '')
    plugin_version = inputs.pop('_plugin_version', None)
    max_retries = inputs.pop('_max_retries', None)
    params = {k: v for k, v in inputs.items() if not k.startswith('_')}
    return atom_type, plugin_version, max_retries, params


def _promote_results(result_value: bool, output_fields: dict, execution_id: int = None, node_id: str = None) -> None:
    """将节点执行结果提升到 pipeline 上下文，供排他网关条件评估和 trace output 展示

    1. ContextValue 表 — 排他网关条件评估
    2. execution.context['_node_outputs'] — trace output 展示
    """
    try:
        from pipeline.eri.runtime import BambooDjangoRuntime
        from bamboo_engine.eri import ContextValue, ContextValueType

        if not execution_id:
            return

        from opsflow.models import FlowExecution
        execution = FlowExecution.objects.get(id=execution_id)
        bamboo_pipeline_id = execution.context.get("bamboo_pipeline_id")
        if not bamboo_pipeline_id:
            return

        auto_vars = execution.context.get("auto_vars", {}) or {}

        # 1. 写入 ContextValue（供排他网关条件评估）
        runtime = BambooDjangoRuntime()
        cv_map = {}
        # _gwcond_* 别名（带 ${}）
        for var_name, spec in auto_vars.items():
            source_key = spec.get('source_key', '')
            if spec.get('source_act') == node_id and source_key in output_fields:
                ref_key = "${%s}" % var_name
                cv_map[ref_key] = ContextValue(key=ref_key, type=ContextValueType.PLAIN, value=output_fields[source_key])

        if cv_map:
            runtime.upsert_plain_context_values(bamboo_pipeline_id, cv_map)

        # 2. 写入 execution.context['_node_outputs'][node_id]（供 trace output 展示）
        _nid = node_id or 'unknown'
        ctx = dict(execution.context or {})
        node_outputs = dict(ctx.get('_node_outputs', {}) or {})
        node_outputs[_nid] = dict(output_fields)
        node_outputs[_nid]['_result'] = result_value
        ctx['_node_outputs'] = node_outputs
        execution.context = ctx
        execution.save(update_fields=['context'])

        logger.info("_promote_results: node %s, %d fields promoted", node_id, len(cv_map) + len(output_fields) + 1)
    except Exception:
        logger.exception("_promote_results failed")


class PluginService(Service):
    """通用 Service — 所有原子通过这一个类路由到 BasePlugin.execute()"""

    def inputs_format(self):
        return []

    def outputs_format(self):
        return []

    def execute(self, data, parent_data):
        """执行插件 — 从 data.inputs 中提取 _atom_type 和参数"""
        atom_type, plugin_version, max_retries, params = _extract_params(data)
        # 从节点 inputs 中获取执行 ID（由 pipeline builder 注入）
        inputs_dict = dict(data.inputs) if hasattr(data, 'inputs') else {}
        _execution_id = inputs_dict.get('_execution_id', None)
        if hasattr(_execution_id, 'value'):
            _execution_id = _execution_id.value

        # ├─ Independent Subprocess (Phase 5) ────────────────────────────
        if atom_type == 'subprocess_independent':
            return self._execute_independent_subprocess(data, parent_data, params, _execution_id)

        plugin_cls = get_plugin(atom_type, version=plugin_version)
        if not plugin_cls:
            data.outputs['_result'] = False
            data.outputs['_error'] = f"未知插件: {atom_type}"
            logger.error("PluginService.execute: 未知插件 %s", atom_type)
            return False

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
            # 将 executor_output 中的字段提升到 data.outputs 顶层
            # 使条件表达式 ${node_id.field_name} 能直接引用
            executor_data = result.get('data', {})
            for k, v in executor_data.items():
                if k not in ('stdout', 'stderr'):
                    data.outputs[k] = v
            if not success:
                data.outputs['_error'] = result.get('error', '执行失败')
            # 立即将执行结果提升到 pipeline 上下文（供排他网关条件评估 + trace output）
            _promote_results(success, executor_data, _execution_id, node_id=getattr(self, 'id', '') or '')
            return success
        except Exception as e:
            logger.exception("插件 %s 执行异常", atom_type)
            data.outputs['_result'] = False
            data.outputs['_error'] = str(e)
            _promote_results(False, {}, _execution_id, node_id=getattr(self, 'id', '') or '')
            return False

    def _execute_independent_subprocess(self, data, parent_data, inputs, _execution_id=None):
        """执行独立子流程调度"""
        target_template_id = inputs.get('_target_template_id')
        variable_mapping = inputs.get('_variable_mapping', [])
        output_mapping = inputs.get('_output_mapping', [])

        if not target_template_id:
            data.outputs['_result'] = False
            data.outputs['_error'] = '独立子流程缺少 target_template_id'
            return False

        execution_id = _execution_id

        try:
            from opsflow.models import FlowExecution
            from opsflow.core.subprocess_dispatcher import SubprocessDispatcher

            execution = FlowExecution.objects.get(id=execution_id)
            dispatcher = SubprocessDispatcher(execution)
            child_id = dispatcher.start_subprocess(
                node_id=data.node_id,
                target_template_id=target_template_id,
                variable_mapping=variable_mapping,
                output_mapping=output_mapping,
            )

            if child_id:
                data.outputs['_result'] = True
                data.outputs['child_execution_id'] = child_id
                return True
            else:
                data.outputs['_result'] = False
                data.outputs['_error'] = '独立子流程启动失败'
                return False
        except Exception as e:
            logger.exception("独立子流程执行异常")
            data.outputs['_result'] = False
            data.outputs['_error'] = str(e)
            return False

    @classmethod
    def need_schedule(cls) -> bool:
        """默认不同步调度，仅明确设置的异步插件启用

        同步插件 execute() 完成后直接进入下一节点。
        异步插件（_need_schedule=True）通过 schedule() 轮询/回调完成。
        """
        return False

    def schedule(self, data, parent_data, callback_data=None):
        """异步调度回调 — 长任务轮询/完成检查"""
        atom_type, plugin_version, max_retries, params = _extract_params(data)

        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            return True  # 未知插件，直接结束

        # 同步插件 → 直接完成
        if not plugin_cls.need_schedule():
            return True
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
        atom_type, _, _, params = _extract_params(data)
        plugin_cls = get_plugin(atom_type)
        if not plugin_cls:
            return False

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
