"""超时追踪 — 节点状态变更时更新 Redis 超时集合

职责:
  - RUNNING 状态: 检查节点是否有 NodeTimeoutConfig，有则加入
    Redis 有序集合 opsflow:executing_nodes, score=到期时间戳
  - FINISHED/FAILED/SUSPENDED: 从集合中移除

参考 bk_sops `_node_timeout_info_update()`
"""

import logging

from bamboo_engine import states

logger = logging.getLogger(__name__)

REDIS_EXECUTING_NODES_KEY = "opsflow:executing_nodes"


def _get_redis():
    """获取 Redis 连接"""
    import redis
    return redis.Redis(
        host="127.0.0.1", port=6379, db=0,
        socket_connect_timeout=3,
        decode_responses=True,
    )


def _update_node_timeout(execution, node_id: str, to_state):
    """根据节点状态变更更新 Redis 超时追踪集合"""
    try:
        from opsflow.models import NodeTimeoutConfig
        import datetime

        r = _get_redis()
        key = f"{node_id}_{getattr(to_state, 'version', '0')}"

        if to_state == states.RUNNING:
            # 检查此节点是否有超时配置
            configs = NodeTimeoutConfig.objects.filter(
                execution=execution,
                node_id=node_id,
            )
            if not configs.exists():
                return

            config = configs.first()
            deadline = (
                datetime.datetime.now() +
                datetime.timedelta(seconds=config.timeout_seconds)
            ).timestamp()
            r.zadd(REDIS_EXECUTING_NODES_KEY, {key: deadline}, nx=True)
            logger.debug(
                "[Timeout] Node %s added to pool, deadline in %ds",
                node_id, config.timeout_seconds,
            )

        elif to_state in (
            states.FINISHED, states.FAILED,
            states.SUSPENDED, states.REVOKED,
        ):
            removed = r.zrem(REDIS_EXECUTING_NODES_KEY, key)
            if removed:
                logger.debug(
                    "[Timeout] Node %s removed from pool (state=%s)",
                    node_id, to_state,
                )

    except Exception as e:
        logger.warning(
            "[Timeout] _update_node_timeout error for node %s: %s",
            node_id, e,
        )
