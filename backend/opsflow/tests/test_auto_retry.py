"""自动重试策略测试 — AutoRetryStrategyCreator + dispatch_auto_retry"""

from unittest.mock import Mock, patch

from opsflow.core.auto_retry import AutoRetryStrategyCreator, dispatch_auto_retry


def _make_execution(mock_id=1):
    exec_mock = Mock()
    exec_mock.id = mock_id
    return exec_mock


class TestAutoRetryStrategyCreator:
    """AutoRetryStrategyCreator.batch_create_strategy 测试"""

    def test_empty_tree_no_strategies(self):
        """空 pipeline_tree 不创建策略"""
        creator = AutoRetryStrategyCreator(_make_execution())
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy({"nodes": [], "edges": []})
            mock_model.objects.bulk_create.assert_not_called()

    def test_no_retry_nodes_no_strategies(self):
        """所有节点 max_retries=0 不创建策略"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 0},
                {"id": "n2"},
                {"id": "n3", "max_retries": -1},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            mock_model.objects.bulk_create.assert_not_called()

    def test_max_retries_none_skipped(self):
        """max_retries=None 跳过"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {"nodes": [{"id": "n1", "max_retries": None}]}
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            mock_model.objects.bulk_create.assert_not_called()

    def test_creates_strategies_for_valid_nodes(self):
        """max_retries>0 的节点创建策略"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 3, "retry_delay": 30},
                {"id": "n2", "max_retries": 5, "retry_delay": 60},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            mock_model.objects.bulk_create.assert_called_once()
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert len(strategies) == 2
            assert strategies[0].node_id == "n1"
            assert strategies[0].max_retry_times == 3
            assert strategies[0].interval == 30

    def test_retry_delay_clamped_to_max(self):
        """retry_delay > 3600 被钳制到 3600"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 2, "retry_delay": 7200},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].interval == 3600

    def test_max_retries_clamped(self):
        """max_retries > 10 被钳制到 10"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 99},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].max_retry_times == 10

    def test_negative_max_retries_abs(self):
        """负数 max_retries 取绝对值"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": -3},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].max_retry_times == 3

    def test_invalid_max_retries_default(self):
        """非数字 max_retries 回退到 3"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": "abc"},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].max_retry_times == 3

    def test_retry_delay_from_params(self):
        """retry_delay 从 params 回退"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 2, "params": {"retry_delay": 45}},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].interval == 45

    def test_empty_node_id_skipped(self):
        """空 id 节点跳过"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "", "max_retries": 3},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            mock_model.objects.bulk_create.assert_not_called()

    def test_retry_delay_invalid_fallback_zero(self):
        """非数字 retry_delay 回退到 0"""
        creator = AutoRetryStrategyCreator(_make_execution())
        tree = {
            "nodes": [
                {"id": "n1", "max_retries": 2, "retry_delay": "not_a_number"},
            ],
        }
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            creator.batch_create_strategy(tree)
            strategies = mock_model.objects.bulk_create.call_args[0][0]
            assert strategies[0].interval == 0


class TestDispatchAutoRetry:
    """dispatch_auto_retry 测试"""

    def test_no_strategy_returns_false(self):
        """没有策略记录返回 False"""
        execution = _make_execution()
        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            mock_model.objects.get.side_effect = mock_model.DoesNotExist
            result = dispatch_auto_retry(execution, "n1")
        assert result is False

    def test_retry_exhausted_returns_false(self):
        """重试次数耗尽返回 False"""
        execution = _make_execution()
        strategy = Mock()
        strategy.retry_times = 3
        strategy.max_retry_times = 3

        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model:
            mock_model.objects.get.return_value = strategy
            result = dispatch_auto_retry(execution, "n1")
        assert result is False

    def test_retry_dispatched_returns_true(self):
        """有剩余重试次数时派发任务并返回 True"""
        execution = _make_execution()
        strategy = Mock()
        strategy.retry_times = 1
        strategy.max_retry_times = 3
        strategy.interval = 30

        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model, \
             patch("opsflow.core.auto_retry.auto_retry_node_task") as mock_task:
            mock_model.objects.get.return_value = strategy
            result = dispatch_auto_retry(execution, "n1")

        assert result is True
        mock_task.apply_async.assert_called_once_with(
            kwargs={"execution_id": 1, "node_id": "n1"},
            countdown=30,
        )

    def test_retry_zero_interval(self):
        """interval=0 时立即执行"""
        execution = _make_execution()
        strategy = Mock()
        strategy.retry_times = 0
        strategy.max_retry_times = 3
        strategy.interval = 0

        with patch("opsflow.core.auto_retry.AutoRetryStrategy") as mock_model, \
             patch("opsflow.core.auto_retry.auto_retry_node_task") as mock_task:
            mock_model.objects.get.return_value = strategy
            result = dispatch_auto_retry(execution, "n1")

        assert result is True
        mock_task.apply_async.assert_called_once_with(
            kwargs={"execution_id": 1, "node_id": "n1"},
            countdown=0,
        )
