"""自动重试策略 — 节点 FAILED 时自动触发重试

参考 bk_sops gcloud/taskflow3/domains/auto_retry.py AutoRetryNodeStrategyCreator
适配 OpsFlow nodes/edges pipeline_tree 格式。

使用流程:
  1. FlowEngine.run() 调用 AutoRetryStrategyCreator.batch_create_strategy()
     遍历 pipeline_tree，为 max_retries > 0 的节点创建策略记录
  2. signals/handlers.py 拦截 FAILED → dispatch_auto_retry()
  3. dispatch_auto_retry() 检查重试次数 → 派发 Celery 任务
"""

import logging

logger = logging.getLogger(__name__)


class AutoRetryStrategyCreator:
    """批量创建自动重试策略 — 在 FlowEngine.run() 开始时调用

    Args:
        execution: FlowExecution 实例
        root_pipeline_id: bamboo-engine pipeline ID
    """

    def __init__(self, execution, root_pipeline_id: str = ""):
        self.execution = execution
        self.root_pipeline_id = root_pipeline_id

    def batch_create_strategy(self, pipeline_tree: dict):
        """遍历 pipeline_tree 的 nodes，为 max_retries > 0 的节点创建策略

        OpsFlow pipeline_tree 格式: {"nodes": [...], "edges": [...]}
        """
        from opsflow.models import AutoRetryStrategy

        nodes = pipeline_tree.get('nodes', [])
        strategies = []
        for node in nodes:
            max_retries = node.get('max_retries', 0)
            if max_retries is None or max_retries <= 0:
                continue

            node_id = node.get('id', '')
            if not node_id:
                continue

            retry_delay = node.get('retry_delay') or node.get('params', {}).get('retry_delay', 0)
            try:
                retry_delay = min(abs(int(retry_delay)), 3600)  # max 1h
            except (ValueError, TypeError):
                retry_delay = 0

            try:
                max_retries = min(abs(int(max_retries)), 10)  # max 10
            except (ValueError, TypeError):
                max_retries = 3

            strategies.append(AutoRetryStrategy(
                execution=self.execution,
                node_id=node_id,
                max_retry_times=max_retries,
                interval=retry_delay,
            ))

        if strategies:
            created = AutoRetryStrategy.objects.bulk_create(
                strategies,
                ignore_conflicts=True,  # 已存在的跳过
            )
            logger.info(
                "[AutoRetry] Created %d strategies for execution %s (attempted %d)",
                len(created), self.execution.id, len(strategies),
            )
        else:
            logger.debug(
                "[AutoRetry] No auto-retry strategies needed for execution %s",
                self.execution.id,
            )


def dispatch_auto_retry(execution, node_id: str) -> bool:
    """检查并派发自动重试 — 在信号拦截到 FAILED 时调用

    Args:
        execution: FlowExecution 实例
        node_id: bamboo-engine UUID（非原始节点 ID）

    Returns:
        bool: True=已派发重试，False=无需重试或已耗尽次数
    """
    from opsflow.models import AutoRetryStrategy

    try:
        strategy = AutoRetryStrategy.objects.get(
            execution=execution,
            node_id=node_id,
        )
    except AutoRetryStrategy.DoesNotExist:
        return False

    if strategy.retry_times >= strategy.max_retry_times:
        logger.info(
            "[AutoRetry] Node %s retry exhausted (%d/%d)",
            node_id, strategy.retry_times, strategy.max_retry_times,
        )
        return False

    # 派发 Celery 任务
    from opsflow.tasks import auto_retry_node_task

    auto_retry_node_task.apply_async(
        kwargs={
            'execution_id': execution.id,
            'node_id': node_id,
        },
        countdown=strategy.interval,
    )
    logger.info(
        "[AutoRetry] Dispatched auto-retry for node %s (retry %d/%d, delay=%ds)",
        node_id, strategy.retry_times + 1, strategy.max_retry_times, strategy.interval,
    )
    return True
