"""节点超时策略 — 超时后自动执行 forced_fail / forced_fail_and_skip

参考 bk_sops gcloud/taskflow3/domains/node_timeout_strategy.py

架构:
  1. FlowEngine.run() → batch_create_timeout_configs() 遍历 pipeline_tree
     为 timeout_seconds > 0 的节点创建 NodeTimeoutConfig 记录
  2. signals/state.py RUNNING → 写入 Redis 有序集合 opsflow:executing_nodes
     score=到期时间戳(timeout_seconds+当前时间)
  3. signals/state.py FINISHED/FAILED → 从 Redis 集合移除
  4. dispatch_timeout_nodes Celery 任务(10s间隔) 扫描到期节点
  5. execute_node_timeout_strategy Celery 任务执行对应策略
"""

from datetime import timedelta

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

# Redis 有序集合键：存储正在执行的节点及其到期时间
REDIS_EXECUTING_NODES_KEY = "opsflow:executing_nodes"
# 超时检查间隔（秒）
TIMEOUT_CHECK_INTERVAL = 10


# ── 策略实现 ─────────────────────────────────────────────────────────


class NodeTimeoutStrategy:
    """节点超时策略基类"""
    TIMEOUT_NODE_OPERATOR = "opsflow_system"
    EX_DATA_HINT = "节点已因超过超时设置被系统终止"

    def deal_with_timeout_node(self, execution, node_id: str, config) -> dict:
        """处理超时节点

        Args:
            execution: FlowExecution 实例
            node_id: bamboo-engine UUID
            config: NodeTimeoutConfig 实例

        Returns:
            dict: {"result": bool, "message": str}
        """
        raise NotImplementedError


class ForcedFailStrategy(NodeTimeoutStrategy):
    """强制失败策略 — 调用 api.forced_fail_activity"""

    def deal_with_timeout_node(self, execution, node_id: str, config) -> dict:
        from bamboo_engine import api as pipeline_api
        from pipeline.eri.runtime import BambooDjangoRuntime

        runtime = BambooDjangoRuntime()
        result = pipeline_api.forced_fail_activity(
            runtime, node_id,
            ex_data=self.EX_DATA_HINT,
            send_post_set_state_signal=True,
        )
        if result.result:
            logger.info(
                "[Timeout] Node %s force-failed by timeout (%ds)",
                node_id, config.timeout_seconds,
            )
        else:
            logger.error(
                "[Timeout] Force-fail node %s failed: %s",
                node_id, result.message,
            )
        return {"result": result.result, "message": result.message}


class ForcedFailAndSkipStrategy(NodeTimeoutStrategy):
    """强制失败并跳过策略"""

    def deal_with_timeout_node(self, execution, node_id: str, config) -> dict:
        from opsflow.core.flow_engine import FlowEngine

        engine = FlowEngine(execution)

        # 1. 强制失败
        engine.force_fail(node_id, ex_data=self.EX_DATA_HINT)

        # 2. 跳过
        engine.skip(node_id)

        logger.info(
            "[Timeout] Node %s force-failed and skipped by timeout (%ds)",
            node_id, config.timeout_seconds,
        )
        return {"result": True, "message": "forced_fail_and_skip"}


# 策略查找表
NODE_TIMEOUT_HANDLER = {
    "forced_fail": ForcedFailStrategy(),
    "forced_fail_and_skip": ForcedFailAndSkipStrategy(),
}


# ── 策略创建 ─────────────────────────────────────────────────────────


def batch_create_timeout_configs(execution, pipeline_tree: dict):
    """遍历 pipeline_tree，为 timeout_seconds > 0 的节点创建超时配置"""
    from opsflow.models import NodeTimeoutConfig

    nodes = pipeline_tree.get('nodes', [])
    configs = []
    for node in nodes:
        timeout = node.get('timeout_seconds')
        if not timeout or timeout <= 0:
            continue

        node_id = node.get('id', '')
        if not node_id:
            continue

        try:
            timeout = min(abs(int(timeout)), 86400)  # max 24h
        except (ValueError, TypeError):
            continue

        configs.append(NodeTimeoutConfig(
            execution=execution,
            node_id=node_id,
            timeout_seconds=timeout,
            action=NodeTimeoutConfig.Action.FORCED_FAIL,
        ))

    if configs:
        created = NodeTimeoutConfig.objects.bulk_create(
            configs,
            ignore_conflicts=True,
        )
        logger.info(
            "[Timeout] Created %d timeout configs for execution %s (attempted %d)",
            len(created), execution.id, len(configs),
        )


# ── Redis 超时管理 ────────────────────────────────────────────────────


def get_redis():
    """获取 Redis 连接"""
    from common.utils.redis_helper import get_redis as _get_redis
    return _get_redis(db=0)


def update_node_timeout(execution, node_id: str, to_state: str, version: str = ""):
    """更新节点超时状态 — 在信号处理器中调用

    参考 bk_sops `_node_timeout_info_update()`

    在 RUNNING 时加入 Redis 有序集合（score=到期时间戳），
    在 FINISHED/FAILED/SUSPENDED 时移除。
    """
    try:
        r = get_redis()
        key = f"{node_id}_{version or '0'}"

        if to_state == "RUNNING":
            from bamboo_engine import states
            from opsflow.models import NodeTimeoutConfig

            configs = NodeTimeoutConfig.objects.filter(
                execution=execution,
                node_id=node_id,
            )
            if not configs.exists():
                return

            config = configs.first()
            deadline = (
                timezone.now() +
                timedelta(seconds=config.timeout_seconds)
            ).timestamp()
            r.zadd(REDIS_EXECUTING_NODES_KEY, {key: deadline}, nx=True)
            logger.debug(
                "[Timeout] Node %s added to timeout pool, deadline=%s",
                node_id, deadline,
            )

        elif to_state in ("FINISHED", "FAILED", "SUSPENDED", "REVOKED"):
            r.zrem(REDIS_EXECUTING_NODES_KEY, key)
            logger.debug(
                "[Timeout] Node %s removed from timeout pool (state=%s)",
                node_id, to_state,
            )

    except Exception as e:
        logger.warning(
            "[Timeout] update_node_timeout error for node %s: %s",
            node_id, e,
        )


def dispatch_timeout_nodes():
    """扫描 Redis 有序集合，找出到期节点并派发执行策略

    由 APScheduler 定时任务调用（每 TIMEOUT_CHECK_INTERVAL 秒）
    """
    from opsflow.models import FlowExecution, NodeTimeoutConfig

    try:
        r = get_redis()
        import time
        now = time.time()
        # 获取 score <= now 的条目（已到期的）
        expired = r.zrangebyscore(
            REDIS_EXECUTING_NODES_KEY, 0, now,
            withscores=False,
        )
        if not expired:
            return

        for key in expired:
            # key 格式: "node_id_version"
            parts = key.rsplit('_', 1)
            node_id = parts[0]
            # 从集合中移除
            r.zrem(REDIS_EXECUTING_NODES_KEY, key)

            # 查找对应的 execution 和 config
            # 通过 NodeTimeoutConfig 反向查找 execution
            configs = NodeTimeoutConfig.objects.filter(node_id=node_id)
            for config in configs:
                execution = config.execution
                if execution.status not in ('running', 'pending'):
                    continue

                action = config.action
                handler = NODE_TIMEOUT_HANDLER.get(action)
                if handler:
                    from opsflow.tasks import execute_node_timeout_strategy
                    execute_node_timeout_strategy.delay(
                        execution_id=execution.id,
                        node_id=node_id,
                        action=action,
                    )
                    logger.info(
                        "[Timeout] Dispatched timeout strategy '%s' for node %s (execution %s)",
                        action, node_id, execution.id,
                    )

    except Exception as e:
        logger.warning("[Timeout] dispatch_timeout_nodes error: %s", e)
