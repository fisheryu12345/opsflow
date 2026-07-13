"""bamboo-engine 适配层 — 通用 PluginService

替换旧的 atom_service.py（按原子类型动态创建 N 个 Component/Service），
改为一个统一的 PluginService，运行时从 PLUGIN_REGISTRY 查找并调用 execute()。

变量解析：由 bamboo-engine SPLICE 机制在构建时注入 runtime context，
PluginService 直接从 data.inputs 读取已解析的值。
"""

import logging

from pipeline.core.flow.activity import Service
from pipeline.component_framework.component import Component

from opsflow.plugins.registry import get_plugin

logger = logging.getLogger(__name__)


def _extract_params(data):
    """从 data.inputs 中提取 _atom_type/_plugin_version/_max_retries 和用户参数
    注意：_atom_type 实际存储的是插件 code（如 "manual_pause"、"approval"、"shell"）
    """
    inputs = dict(data.inputs)
    atom_type = inputs.pop('_atom_type', '')
    plugin_version = inputs.pop('_plugin_version', None)
    max_retries = inputs.pop('_max_retries', None)
    params = {k: v for k, v in inputs.items() if not k.startswith('_')}
    return atom_type, plugin_version, max_retries, params


def _promote_results(result_value: bool, output_fields: dict, execution_id: int = None, node_id: str = None) -> None:
    """将节点执行结果写入 execution.context._node_outputs（供 UI trace 展示）

    ContextValue 传播由 bamboo-engine NodeOutput 自动完成，不再重复写入。
    data.outputs 由引擎自动存储，可通过 api.get_execution_data_outputs() 查询。
    """
    try:
        if not execution_id:
            return

        from opsflow.models import FlowExecution
        execution = FlowExecution.objects.get(id=execution_id)

        _nid = node_id or 'unknown'
        ctx = dict(execution.context or {})
        node_outputs = dict(ctx.get('_node_outputs', {}) or {})
        node_outputs[_nid] = dict(output_fields)
        node_outputs[_nid]['_result'] = result_value
        ctx['_node_outputs'] = node_outputs
        execution.context = ctx
        execution.save(update_fields=['context'])

        logger.info("_promote_results: node %s, %d fields", node_id, len(output_fields) + 1)
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

        # ├─ Manual Pause — 直接在 execute 中暂停，不依赖信号 ────────────
        if atom_type == 'manual_pause':
            from opsflow.core.flow_engine import FlowEngine
            from opsflow.models import FlowExecution
            try:
                execution = FlowExecution.objects.get(id=_execution_id)
                execution.context['_pause_reason'] = 'manual_pause'
                execution.save(update_fields=['context'])
                FlowEngine(execution).pause()
                logger.info(
                    "[ManualPause] Node paused execution %s (manual_pause)",
                    _execution_id,
                )
            except Exception:
                logger.exception("[ManualPause] pause failed")
            data.outputs['_result'] = True
            return True

        plugin_cls = get_plugin(atom_type, version=plugin_version)
        if not plugin_cls:
            data.outputs['_result'] = False
            data.outputs['_error'] = f"未知插件: {atom_type}"
            logger.error("PluginService.execute: 未知插件 %s", atom_type)
            return False

        # === 变量解析：bamboo-engine SPLICE 运行时已自动完成 ===
        # 直接从 data.inputs 读取已解析的用户参数字段（跳过 _ 开头的内部字段）
        resolved_params = {k: v for k, v in inputs_dict.items()
                           if not k.startswith('_') and k in data.inputs}
        # split 类型字段补充分割（var_types 来自插件定义）
        var_types = plugin_cls.get_var_types() if hasattr(plugin_cls, 'get_var_types') else {}
        for k, v in resolved_params.items():
            if var_types.get(k) == 'split' and isinstance(v, str):
                resolved_params[k] = [s.strip() for s in v.split(',') if s.strip()]
        # === 二次解析：bamboo-engine SPLICE 无法解析 ${node_id.field} 引用（NodeOutput value=None） ===
        if _execution_id:
            try:
                from opsflow.models import FlowExecution
                from opsflow.core.variable_resolver import build_execution_context, resolve_variables
                execution = FlowExecution.objects.get(id=_execution_id)
                ctx = build_execution_context(execution)
                for k, v in list(resolved_params.items()):
                    if isinstance(v, str) and '${' in v:
                        resolved = resolve_variables(v, ctx)
                        if resolved != v:
                            resolved_params[k] = resolved
                # 合并全局变量：不在 data.inputs 中的全局变量（如用户通过全局变量传递的参数）
                for gk, gv in ctx.items():
                    if gk not in resolved_params and not gk.startswith('_') and not isinstance(gv, dict):
                        resolved_params[gk] = gv
            except Exception:
                logger.exception("二次变量解析失败")
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
            # 将执行结果写入 execution.context（供 UI trace 展示）
            # ContextValue 由 bamboo-engine NodeOutput 自动传播
            _promote_results(success, executor_data, _execution_id, node_id=getattr(self, 'id', '') or '')
            # ── 实时同步到 CMDB ──
            if success and atom_type and atom_type.startswith('aliyun_'):
                try:
                    from opsflow.core.cloud_sync import sync_after_execution
                    sync_after_execution(atom_type, inputs_dict, result, _execution_id)
                except Exception:
                    logger.exception("cloud_sync failed for %s", atom_type)
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



# 注册唯一的 Component — ComponentMeta 元类自动处理注册
class OpsflowPluginComponent(Component):
    name = "OpsFlow Plugin"
    code = "opsflow_plugin"
    bound_service = PluginService
