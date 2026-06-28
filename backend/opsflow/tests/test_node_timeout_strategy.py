"""节点超时策略测试 — batch_create_timeout_configs / update_node_timeout / dispatch_timeout_nodes / 策略实现"""
from django.test import SimpleTestCase

from unittest.mock import ANY, Mock, patch, MagicMock

from opsflow.core.node_timeout_strategy import (
    ForcedFailStrategy,
    ForcedFailAndSkipStrategy,
    batch_create_timeout_configs,
    update_node_timeout,
    dispatch_timeout_nodes,
    REDIS_EXECUTING_NODES_KEY,
)


def _make_execution(mock_id=1):
    exec_mock = Mock()
    exec_mock.id = mock_id
    return exec_mock


# =============================================================================
# batch_create_timeout_configs
# =============================================================================


class TestBatchCreateTimeoutConfigs(SimpleTestCase):
    """batch_create_timeout_configs 测试"""

    def test_empty_tree_no_configs(self):
        """空 pipeline_tree 不创建配置"""
        execution = _make_execution()
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, {"nodes": [], "edges": []})
            mock_model.objects.bulk_create.assert_not_called()

    def test_no_timeout_nodes_skipped(self):
        """所有节点 timeout_seconds=0/None 不创建"""
        execution = _make_execution()
        tree = {
            "nodes": [
                {"id": "n1", "timeout_seconds": 0},
                {"id": "n2"},  # 没有 timeout 字段
                {"id": "n3", "timeout_seconds": -1},
            ],
        }
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, tree)
            mock_model.objects.bulk_create.assert_not_called()

    def test_creates_configs_for_valid_nodes(self):
        """timeout_seconds>0 的节点创建配置"""
        execution = _make_execution()
        tree = {
            "nodes": [
                {"id": "n1", "timeout_seconds": 300},
                {"id": "n2", "timeout_seconds": 600},
            ],
        }
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, tree)
            mock_model.objects.bulk_create.assert_called_once()
            configs = mock_model.objects.bulk_create.call_args[0][0]
            assert len(configs) == 2
            assert configs[0].node_id == "n1"
            assert configs[0].timeout_seconds == 300

    def test_timeout_clamped_to_max(self):
        """timeout_seconds > 86400 被钳制到 86400"""
        execution = _make_execution()
        tree = {
            "nodes": [
                {"id": "n1", "timeout_seconds": 999999},
            ],
        }
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, tree)
            configs = mock_model.objects.bulk_create.call_args[0][0]
            assert configs[0].timeout_seconds == 86400

    def test_invalid_timeout_skipped(self):
        """非数字 timeout_seconds 跳过"""
        execution = _make_execution()
        tree = {
            "nodes": [
                {"id": "n1", "timeout_seconds": "abc"},
            ],
        }
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, tree)
            mock_model.objects.bulk_create.assert_not_called()

    def test_empty_node_id_skipped(self):
        """空 id 节点跳过"""
        execution = _make_execution()
        tree = {
            "nodes": [
                {"id": "", "timeout_seconds": 300},
            ],
        }
        with patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            batch_create_timeout_configs(execution, tree)
            mock_model.objects.bulk_create.assert_not_called()


# =============================================================================
# update_node_timeout (Redis)
# =============================================================================


class TestUpdateNodeTimeout(SimpleTestCase):
    """update_node_timeout 测试（Redis 交互）"""

    def test_running_adds_to_redis(self):
        """RUNNING 状态将节点加入 Redis 有序集合"""
        execution = _make_execution()
        mock_redis = MagicMock()
        mock_config = Mock()
        mock_config.timeout_seconds = 300

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis), \
             patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model, \
             patch("opsflow.core.node_timeout_strategy.datetime") as mock_dt:
            mock_dt.datetime.now.return_value.timestamp.return_value = 1000.0
            mock_model.objects.filter.return_value.exists.return_value = True
            mock_model.objects.filter.return_value.first.return_value = mock_config

            update_node_timeout(execution, "node_1", "RUNNING", version="v1")

            expected_key = "node_1_v1"
            mock_redis.zadd.assert_called_once()
            args = mock_redis.zadd.call_args[0]
            assert args[0] == REDIS_EXECUTING_NODES_KEY
            assert expected_key in args[1]
            assert args[1][expected_key] == 1300.0  # 1000 + 300
            assert mock_redis.zadd.call_args[1].get("nx") is True

    def test_running_no_config_skips(self):
        """RUNNING 但没有超时配置 → 不写 Redis"""
        execution = _make_execution()
        mock_redis = MagicMock()

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis), \
             patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            mock_model.objects.filter.return_value.exists.return_value = False
            update_node_timeout(execution, "node_1", "RUNNING")
            mock_redis.zadd.assert_not_called()

    def test_finished_removes_from_redis(self):
        """FINISHED 状态从 Redis 移除"""
        execution = _make_execution()
        mock_redis = MagicMock()

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis):
            update_node_timeout(execution, "node_1", "FINISHED", version="v1")
            mock_redis.zrem.assert_called_once_with(REDIS_EXECUTING_NODES_KEY, "node_1_v1")

    def test_failed_removes_from_redis(self):
        """FAILED 状态也从 Redis 移除"""
        execution = _make_execution()
        mock_redis = MagicMock()

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis):
            update_node_timeout(execution, "node_1", "FAILED", version="v1")
            mock_redis.zrem.assert_called_once_with(REDIS_EXECUTING_NODES_KEY, "node_1_v1")

    def test_unknown_state_noop(self):
        """未知状态不操作 Redis"""
        execution = _make_execution()
        mock_redis = MagicMock()

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis):
            update_node_timeout(execution, "node_1", "PENDING")
            mock_redis.zadd.assert_not_called()
            mock_redis.zrem.assert_not_called()

    def test_redis_error_caught(self):
        """Redis 异常被捕获不抛异常"""
        execution = _make_execution()
        mock_redis = MagicMock()
        mock_redis.zadd.side_effect = Exception("Redis down")

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis), \
             patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_model:
            mock_model.objects.filter.return_value.exists.return_value = True
            mock_model.objects.filter.return_value.first.return_value = Mock(timeout_seconds=60)
            # 不应该抛异常
            update_node_timeout(execution, "node_1", "RUNNING")


# =============================================================================
# dispatch_timeout_nodes
# =============================================================================


class TestDispatchTimeoutNodes(SimpleTestCase):
    """dispatch_timeout_nodes 测试"""

    def test_no_expired_nodes_noop(self):
        """没有到期节点不派发任务"""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = []

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis):
            result = dispatch_timeout_nodes()  # 不应抛异常
            assert result is None

    def test_expired_node_dispatches_strategy(self):
        """到期节点派发超时策略任务"""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = ["node_1_v1"]
        mock_config = Mock()
        mock_config.action = "forced_fail"
        mock_config.execution.id = 1
        mock_config.execution.status = "running"

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis), \
             patch("opsflow.core.node_timeout_strategy.FlowExecution") as mock_exec, \
             patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_config_model, \
             patch("opsflow.core.node_timeout_strategy.execute_node_timeout_strategy") as mock_task:

            mock_config_model.objects.filter.return_value = [mock_config]
            dispatch_timeout_nodes()

            mock_task.delay.assert_called_once_with(
                execution_id=1,
                node_id="node_1",
                action="forced_fail",
            )

    def test_expired_execution_not_running_skipped(self):
        """执行已完成的到期节点不派发"""
        mock_redis = MagicMock()
        mock_redis.zrangebyscore.return_value = ["node_1_v1"]
        mock_config = Mock()
        mock_config.execution.status = "completed"

        with patch("opsflow.core.node_timeout_strategy.get_redis", return_value=mock_redis), \
             patch("opsflow.core.node_timeout_strategy.NodeTimeoutConfig") as mock_config_model, \
             patch("opsflow.core.node_timeout_strategy.execute_node_timeout_strategy") as mock_task:

            mock_config_model.objects.filter.return_value = [mock_config]
            dispatch_timeout_nodes()

            mock_task.delay.assert_not_called()


# =============================================================================
# 策略实现
# =============================================================================


class TestForcedFailStrategy(SimpleTestCase):
    """ForcedFailStrategy 测试"""

    def test_forced_fail_success(self):
        """forced_fail 成功返回 {'result': True}"""
        strategy = ForcedFailStrategy()
        execution = _make_execution()

        with patch("opsflow.core.node_timeout_strategy.pipeline_api") as mock_api:
            mock_api.forced_fail_activity.return_value = Mock(result=True, message="ok")
            result = strategy.deal_with_timeout_node(execution, "n1", Mock(timeout_seconds=60))

        assert result["result"] is True
        mock_api.forced_fail_activity.assert_called_once_with(
            ANY, "n1",
            ex_data=ForcedFailStrategy.EX_DATA_HINT,
            send_post_set_state_signal=True,
        )

    def test_forced_fail_failure(self):
        """forced_fail API 失败返回 {'result': False}"""
        strategy = ForcedFailStrategy()
        execution = _make_execution()

        with patch("opsflow.core.node_timeout_strategy.pipeline_api") as mock_api:
            mock_api.forced_fail_activity.return_value = Mock(result=False, message="error")
            result = strategy.deal_with_timeout_node(execution, "n1", Mock())

        assert result["result"] is False
        assert result["message"] == "error"


class TestForcedFailAndSkipStrategy(SimpleTestCase):
    """ForcedFailAndSkipStrategy 测试"""

    def test_force_fail_then_skip(self):
        """先强制失败再跳过"""
        strategy = ForcedFailAndSkipStrategy()
        execution = _make_execution()
        execution.node_status = {}

        with patch("opsflow.core.node_timeout_strategy.FlowEngine") as mock_engine_cls:
            mock_engine = mock_engine_cls.return_value
            result = strategy.deal_with_timeout_node(execution, "n1", Mock(timeout_seconds=60))

        assert result["result"] is True
        mock_engine.force_fail.assert_called_once_with("n1", ex_data=strategy.EX_DATA_HINT)
        mock_engine.skip.assert_called_once_with("n1")
