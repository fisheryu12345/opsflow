"""Flow Execution Engine — walks bamboo-engine Pipeline Tree with full gateway support

Replaces the old sequential _execute_nodes() with a proper engine that handles:
  - ServiceActivity       → AnsibleAtomService.execute()
  - ExclusiveGateway      → condition evaluation, single branch
  - ParallelGateway       → Celery group, parallel branches
  - ConvergeGateway       → Redis-counter await (last branch continues)
  - ConditionalParallelGateway → condition + parallel
"""

import datetime
import json
import logging
from collections import deque

from django.conf import settings
from django_redis import get_redis_connection

from opsflow.core.atom_service import AnsibleAtomService, get_service
from opsflow.core.bamboo_builder import build_bamboo_pipeline
from bamboo_engine.eri import ExecutionData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis helpers for converge counting
# ---------------------------------------------------------------------------

CONVERGE_PREFIX = "opsflow:converge"


def _converge_key(execution_id, gateway_id):
    return f"{CONVERGE_PREFIX}:{execution_id}:{gateway_id}"


def _set_converge_count(execution_id, gateway_id, n):
    r = get_redis_connection("default")
    r.set(_converge_key(execution_id, gateway_id), n)


def _decr_converge_count(execution_id, gateway_id):
    """原子减一并返回剩余值"""
    r = get_redis_connection("default")
    return r.decr(_converge_key(execution_id, gateway_id))


def _get_converge_count(execution_id, gateway_id):
    r = get_redis_connection("default")
    return int(r.get(_converge_key(execution_id, gateway_id)) or 0)


def _del_converge_count(execution_id, gateway_id):
    r = get_redis_connection("default")
    r.delete(_converge_key(execution_id, gateway_id))


def _find_converge_target(pipeline, gw_id):
    """BFS 从 ParallelGateway 向下游查找第一个 ConvergeGateway ID"""
    flows = pipeline.get("flows", {})
    gateways = pipeline.get("gateways", {})
    activities = pipeline.get("activities", {})

    gw = gateways.get(gw_id)
    if not gw:
        return None
    outgoing = gw.get("outgoing", [])
    if isinstance(outgoing, str):
        outgoing = [outgoing]

    visited = {gw_id}
    q = deque()
    for fid in outgoing:
        flow = flows.get(fid)
        if flow and flow["target"] not in visited:
            q.append(flow["target"])

    while q:
        nid = q.popleft()
        if nid in visited:
            continue
        visited.add(nid)

        if nid in gateways and gateways[nid]["type"] == "ConvergeGateway":
            return nid

        # 遍历该节点的所有出边
        node = gateways.get(nid) or activities.get(nid) or {}
        out = node.get("outgoing", [])
        if isinstance(out, str):
            out = [out]
        for fid in out:
            flow = flows.get(fid)
            if flow and flow["target"] not in visited:
                q.append(flow["target"])

    return None


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


class FlowEngine:
    """流程执行引擎 — 驱动 bamboo-engine 标准 Pipeline Tree 执行"""

    def __init__(self, execution):
        self.execution = execution
        self.template = execution.template

    # -- External API (unchanged) -------------------------------------------

    def start(self):
        """启动执行，创建 Celery 任务"""
        self.execution.status = "running"
        self.execution.started_at = datetime.datetime.now()
        self.execution.node_status = {}
        self.execution.context = {}
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task

        execute_pipeline_task.delay(self.execution.id)

    def resume(self):
        """恢复暂停的执行"""
        self.execution.status = "running"
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task

        execute_pipeline_task.delay(self.execution.id)

    def retry(self, node_id):
        """重试指定失败节点"""
        node_status = self.execution.node_status or {}
        node_status[node_id] = "pending"
        self.execution.node_status = node_status
        self.execution.current_node = node_id
        self.execution.status = "running"
        self.execution.save()
        from opsflow.tasks import execute_pipeline_task

        execute_pipeline_task.delay(self.execution.id)

    def skip(self, node_id):
        """跳过指定节点"""
        node_status = self.execution.node_status or {}
        node_status[node_id] = "skipped"
        self.execution.node_status = node_status
        self.execution.save()

    # -- Run ----------------------------------------------------------------

    def run(self):
        """执行 Pipeline（由 Celery worker 调用）"""
        try:
            pipeline = build_bamboo_pipeline(self.template)
            self.execution.context["bamboo_pipeline"] = pipeline
            self.execution.save()
            self._execute_bamboo(pipeline)
        except Exception as e:
            logger.exception("Pipeline 执行失败")
            self.execution.status = "failed"
            self.execution.ended_at = datetime.datetime.now()
            self.execution.save()
            self._notify_completed()

    def _execute_bamboo(self, pipeline):
        """从 start_event 开始遍历执行"""
        start = pipeline.get("start_event", {})
        start_id = start.get("id", "")
        logger.info("[FlowEngine] start pipeline %s", pipeline.get("id", ""))

        # 沿着 start_event → outgoing → 第一个活动节点
        outgoing = start.get("outgoing", "")
        if not outgoing:
            logger.warning("[FlowEngine] start_event has no outgoing")
            self._complete()
            return

        flows = pipeline.get("flows", {})
        next_flow = flows.get(outgoing)
        if not next_flow:
            logger.warning("[FlowEngine] start_event outgoing flow %s not found", outgoing)
            self._complete()
            return

        self._process_node(next_flow["target"], pipeline)

    # -- Node dispatch ------------------------------------------------------

    def _process_node(self, node_id, pipeline, converge_key=None):
        """根据节点类型分发到对应的处理方法"""
        # 检查是否已跳过或已完成
        current_status = (self.execution.node_status or {}).get(node_id)
        if current_status in ("completed", "skipped"):
            # 跳过已完成节点，继续往下
            self._skip_to_next(node_id, pipeline, converge_key)
            return

        activities = pipeline.get("activities", {})
        gateways = pipeline.get("gateways", {})

        if node_id in activities:
            self._execute_activity(node_id, pipeline, converge_key)
        elif node_id in gateways:
            self._execute_gateway(node_id, pipeline, converge_key)
        elif node_id == pipeline.get("end_event", {}).get("id", ""):
            self._complete()
        else:
            logger.warning("[FlowEngine] unknown node %s, skipping", node_id)
            self._skip_to_next(node_id, pipeline, converge_key)

    # -- Activity execution -------------------------------------------------

    def _execute_activity(self, node_id, pipeline, converge_key=None):
        activity = pipeline["activities"][node_id]
        code = activity["component"]["code"]
        inputs = activity["component"]["inputs"]

        # 构造 ExecutionData — 注入 execution_id/node_id 供 Tower 轮询推送
        plain_inputs = {
            k: v.get("value") if isinstance(v, dict) else v
            for k, v in inputs.items()
        }
        plain_inputs["_execution_id"] = str(self.execution.id)
        plain_inputs["_node_id"] = node_id

        data = ExecutionData(inputs=plain_inputs, outputs={})
        root_data = ExecutionData(
            inputs={
                "target_hosts": self.template.target_hosts or [],
                "global_vars": self.template.global_vars or {},
            },
            outputs={},
        )

        self.execution.current_node = node_id
        self._set_node_status(node_id, "running")
        self._notify_node(node_id, "running")

        try:
            service = get_service(code)
            success = service.execute(data, root_data)
            outputs = dict(data.outputs) if data.outputs else {}

            # ---- 上下文注入 ----
            # 1. 常规结果
            self.execution.context["_last_outputs"] = outputs
            self.execution.context["_last_result"] = outputs.get("_result", success)

            # 2. Tower artifacts 注入（便于下游网关条件引用）
            executor_output = outputs.get("executor_output", {})
            artifacts = executor_output.get("artifacts", {}) if isinstance(executor_output, dict) else {}
            if artifacts:
                self.execution.context[node_id] = {
                    "status": "success" if success else "failed",
                    "artifacts": artifacts,
                    "structured": executor_output.get("structured", {}),
                    "summary": executor_output.get("summary", {}),
                    "elapsed": executor_output.get("elapsed", 0),
                }
                # 将 artifacts 的每个字段提升到 context 顶层（便于条件表达式引用）
                for k, v in artifacts.items():
                    self.execution.context[f"{node_id}.{k}"] = v

            self.execution.context["_artifacts"] = artifacts

            if success:
                self._set_node_status(node_id, "completed")
                self._notify_node(node_id, "completed")
                self._log_result(node_id, outputs)
            else:
                self._set_node_status(node_id, "failed")
                self._notify_node(node_id, "failed")
                self._log_error(node_id, outputs.get("_error", "execution returned False"))

            # 检查是否被暂停
            self._refresh_execution()
            if self.execution.status == "paused":
                return

            # 走 success / failure 出边
            flows = pipeline.get("flows", {})
            outgoing = activity.get("outgoing", "")
            if outgoing:
                flow = flows.get(outgoing)
                if flow:
                    self._process_node(flow["target"], pipeline, converge_key)
                else:
                    # 没有后续节点，完成
                    self._complete()
            else:
                self._complete()
        except Exception as e:
            logger.exception("[FlowEngine] activity %s failed", node_id)
            self._set_node_status(node_id, "failed")
            self._notify_node(node_id, "failed")
            self._log_error(node_id, str(e))

    # -- Gateway execution --------------------------------------------------

    def _execute_gateway(self, node_id, pipeline, converge_key=None):
        gateway = pipeline["gateways"][node_id]
        gw_type = gateway.get("type", "")

        if gw_type == "ExclusiveGateway":
            self._execute_exclusive_gateway(node_id, pipeline, converge_key)
        elif gw_type == "ParallelGateway":
            self._execute_parallel_gateway(node_id, pipeline)
        elif gw_type == "ConditionalParallelGateway":
            self._execute_conditional_parallel_gateway(node_id, pipeline)
        elif gw_type == "ConvergeGateway":
            self._execute_converge_gateway(node_id, pipeline, converge_key)
        else:
            logger.warning("[FlowEngine] unknown gateway type: %s", gw_type)
            self._skip_to_next(node_id, pipeline, converge_key)

    def _execute_exclusive_gateway(self, node_id, pipeline, converge_key=None):
        """条件分支：根据 _result 选择一条出边"""
        gateway = pipeline["gateways"][node_id]
        outgoing = gateway.get("outgoing", [])
        if isinstance(outgoing, str):
            outgoing = [outgoing]

        if not outgoing:
            self._complete()
            return

        flows = pipeline.get("flows", {})

        if len(outgoing) == 1:
            target = flows.get(outgoing[0], {}).get("target", "")
            self._process_node(target, pipeline, converge_key)
            return

        # 多条出边：检查 conditions
        conditions = gateway.get("conditions", {})
        default_flow_id = None
        last_result = self.execution.context.get("_last_result", True)

        for fid in outgoing:
            flow = flows.get(fid)
            if not flow:
                continue
            if flow.get("is_default"):
                default_flow_id = fid
            cond = conditions.get(fid, {}).get("evaluate", "")
            if cond and self._evaluate_condition(cond, last_result):
                # 命中条件
                self._notify_node(node_id, "completed")
                self._process_node(flow["target"], pipeline, converge_key)
                return

        # 没有命中条件，走默认分支
        if default_flow_id:
            target = flows.get(default_flow_id, {}).get("target", "")
            self._notify_node(node_id, "completed")
            self._process_node(target, pipeline, converge_key)
            return

        # 都没有，走第一条
        target = flows.get(outgoing[0], {}).get("target", "")
        self._notify_node(node_id, "completed")
        self._process_node(target, pipeline, converge_key)

    def _execute_parallel_gateway(self, node_id, pipeline):
        """并行分支：Celery group 并行执行所有分支"""
        gateway = pipeline["gateways"][node_id]
        outgoing = gateway.get("outgoing", [])
        if isinstance(outgoing, str):
            outgoing = [outgoing]

        if not outgoing:
            self._complete()
            return

        # 查找汇聚网关
        converge_id = _find_converge_target(pipeline, node_id)
        if not converge_id:
            logger.error("[FlowEngine] no converge gateway found for parallel %s", node_id)
            self.execution.status = "failed"
            self.execution.save()
            return

        # 设置汇聚计数 = 分支数
        _set_converge_count(self.execution.id, converge_id, len(outgoing))
        self.execution.context["_active_converge"] = converge_id
        self.execution.save()

        self._set_node_status(node_id, "completed")

        # 启动并行分支任务
        flows = pipeline.get("flows", {})
        from celery import group

        jobs = []
        for fid in outgoing:
            flow = flows.get(fid)
            if not flow:
                continue
            target_id = flow["target"]
            jobs.append(
                _execute_branch_task.s(self.execution.id, target_id, converge_id)
            )

        if jobs:
            group(jobs).apply_async()

    def _execute_conditional_parallel_gateway(self, node_id, pipeline):
        """条件并行：按条件选择分支并行执行"""
        gateway = pipeline["gateways"][node_id]
        outgoing = gateway.get("outgoing", [])
        if isinstance(outgoing, str):
            outgoing = [outgoing]

        if not outgoing:
            self._complete()
            return

        conditions = gateway.get("conditions", {})
        flows = pipeline.get("flows", {})
        last_result = self.execution.context.get("_last_result", True)

        # 筛选符合条件的出边
        matched_flows = []
        for fid in outgoing:
            flow = flows.get(fid)
            if not flow:
                continue
            cond = conditions.get(fid, {}).get("evaluate", "")
            if not cond or self._evaluate_condition(cond, last_result):
                matched_flows.append(fid)

        if not matched_flows:
            self._complete()
            return

        converge_id = _find_converge_target(pipeline, node_id)
        if not converge_id:
            logger.error("[FlowEngine] no converge gateway found for conditional parallel %s", node_id)
            self.execution.status = "failed"
            self.execution.save()
            return

        _set_converge_count(self.execution.id, converge_id, len(matched_flows))
        self.execution.context["_active_converge"] = converge_id
        self.execution.save()

        self._set_node_status(node_id, "completed")

        from celery import group

        jobs = []
        for fid in matched_flows:
            flow = flows.get(fid)
            target_id = flow["target"]
            jobs.append(
                _execute_branch_task.s(self.execution.id, target_id, converge_id)
            )

        if jobs:
            group(jobs).apply_async()

    def _execute_converge_gateway(self, node_id, pipeline, converge_key=None):
        """汇聚网关：递减计数，仅最后一个分支继续执行"""
        remaining = _decr_converge_count(self.execution.id, node_id)

        self._set_node_status(node_id, "running")
        self._notify_node(node_id, "running")

        if remaining > 0:
            # 还有分支未到达，当前分支结束
            self._set_node_status(node_id, "completed")
            self._notify_node(node_id, "completed")
            return

        # 最后一个分支：清理计数，继续执行
        _del_converge_count(self.execution.id, node_id)
        self._set_node_status(node_id, "completed")
        self._notify_node(node_id, "completed")

        # 继续
        gateway = pipeline["gateways"][node_id]
        outgoing = gateway.get("outgoing", "")
        if isinstance(outgoing, str) and outgoing:
            flows = pipeline.get("flows", {})
            flow = flows.get(outgoing)
            if flow:
                self._process_node(flow["target"], pipeline)

    # -- Helpers ------------------------------------------------------------

    def _evaluate_condition(self, expr: str, last_result) -> bool:
        """评估网关条件表达式

        支持语法:
          - ${_result == True} / ${_result == False}     — 基础成功/失败
          - ${_result}                                     — 布尔值
          - ${check_space.artifacts.available_gb >= 2}     — 引用前序节点 artifacts
          - ${health_check.artifacts.health_status == 200} — 数值比较
          - ${node_id.artifacts.key}                       — 取 artifacts 中的值
          - ${node_id.summary.failed > 0}                  — 事件统计比较

        所有变量引用都从 execution.context 中查找。
        """
        # 提取 ${...} 表达式
        import re
        match = re.search(r'\$\{(.+)\}', expr)
        if not match:
            return True

        inner = match.group(1).strip()

        # 1. 简单 _result 判断
        if inner == "_result":
            return bool(last_result)
        if inner == "_result == True":
            return bool(last_result) is True
        if inner == "_result == False":
            return bool(last_result) is False

        # 2. 复杂表达式：提取变量路径并替换为 context 中的值
        #    例如: ${check_space.artifacts.available_gb >= 2}
        #    → 替换 check_space.artifacts.available_gb 为实际值 → eval
        #
        #    支持的比较运算符: >=, <=, ==, !=, >, <
        operators = [">=", "<=", "==", "!=", ">", "<"]

        # 查找运算符位置
        op_pos = -1
        op_used = ""
        for op in operators:
            pos = inner.find(op)
            if pos > 0:  # 不在开头
                op_pos = pos
                op_used = op
                break

        if op_used:
            var_path = inner[:op_pos].strip()
            right = inner[op_pos + len(op_used):].strip()
        else:
            var_path = inner
            right = ""

        # 替换变量路径为 context 中的实际值
        ctx = self.execution.context or {}

        # 尝试直接取 context[var_path]（注入时按 "node_id.key" 展平过）
        var_value = None
        if var_path in ctx:
            var_value = ctx[var_path]
        else:
            # 尝试嵌套路径查找：split by "." and traverse
            parts = var_path.split(".")
            current = ctx
            found = True
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    found = False
                    break
            if found:
                var_value = current

        if var_value is None:
            logger.warning("[FlowEngine] 条件变量 %s 未在 context 中找到", var_path)
            return False

        if not op_used:
            # 无运算符：直接做布尔判断
            return bool(var_value)

        # 构造求值表达式
        try:
            # 数值比较
            if isinstance(var_value, (int, float)):
                right_val = float(right) if "." in right else int(right)
                safe_vars = {"__builtins__": {}}
                result = eval(f"{var_value} {op_used} {right_val}", safe_vars, {})
                return bool(result)
            else:
                # 字符串比较
                import json
                right_val = json.loads(right) if right.startswith(('"', "'", "[")) else right
                safe_vars = {"__builtins__": {}}
                result = eval(f"'{var_value}' {op_used} '{right_val}'", safe_vars, {})
                return bool(result)
        except Exception as e:
            logger.warning("[FlowEngine] 条件求值失败: %s (expr=%s)", e, expr)
            return False

    def _skip_to_next(self, node_id, pipeline, converge_key=None):
        """跳过已完成/未知节点，继续处理后续节点"""
        flows = pipeline.get("flows", {})
        gateways = pipeline.get("gateways", {})
        activities = pipeline.get("activities", {})

        node = activities.get(node_id) or gateways.get(node_id) or {}
        outgoing = node.get("outgoing", "")
        if isinstance(outgoing, str) and outgoing:
            flow = flows.get(outgoing)
            if flow:
                self._process_node(flow["target"], pipeline, converge_key)
                return
        self._complete()

    def _set_node_status(self, node_id, status):
        node_status = self.execution.node_status or {}
        node_status[node_id] = status
        self.execution.node_status = node_status
        self.execution.save(update_fields=["node_status", "current_node"])

    def _refresh_execution(self):
        """从数据库刷新 execution，获取最新状态（如暂停）"""
        self.execution.refresh_from_db()

    def _complete(self):
        """正常完成"""
        self.execution.status = "completed"
        self.execution.ended_at = datetime.datetime.now()
        self.execution.save()
        self._notify_completed()
        logger.info("[FlowEngine] pipeline completed")

    def _log_result(self, node_id, outputs):
        from opsflow.models import OpsLog

        OpsLog.objects.create(
            execution=self.execution,
            step=node_id,
            command="",
            stdout=json.dumps(outputs, ensure_ascii=False, default=str),
            stderr="",
            returncode=0,
            risk_level="low",
        )

    def _log_error(self, node_id, error_msg):
        from opsflow.models import OpsLog

        OpsLog.objects.create(
            execution=self.execution,
            step=node_id,
            command="",
            stdout="",
            stderr=str(error_msg),
            returncode=-1,
            risk_level="medium",
        )

    def _notify_node(self, node_id, status):
        from opsflow.tasks import notify_node_status

        notify_node_status.delay(self.execution.id, node_id, status)

    def _notify_completed(self):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"execution_{self.execution.id}",
            {"type": "execution.completed", "status": self.execution.status},
        )


# ---------------------------------------------------------------------------
# Celery branch task (defined here to avoid circular imports in tasks.py)
# ---------------------------------------------------------------------------

from celery import shared_task


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def _execute_branch_task(self, execution_id, start_node_id, converge_id):
    """并行分支任务 — 从 start_node_id 执行到 ConvergeGateway"""
    from opsflow.models import FlowExecution

    try:
        execution = FlowExecution.objects.get(id=execution_id)
    except FlowExecution.DoesNotExist:
        return

    engine = FlowEngine(execution)
    pipeline = execution.context.get("bamboo_pipeline", {})
    if not pipeline:
        logger.error("[branch] no bamboo_pipeline in execution context")
        return

    try:
        engine._process_node(start_node_id, pipeline, converge_id)
    except Exception as e:
        logger.exception("[branch] branch task failed: %s", e)
