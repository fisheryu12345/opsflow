"""状态机测试 — NodeState / PipelineState 转移矩阵"""
from django.test import SimpleTestCase

from opsflow.core.states import (
    NodeState,
    PipelineState,
    validate_node_transition,
    validate_pipeline_transition,
    map_bamboo_node_state,
)


class TestNodeState(SimpleTestCase):
    """节点状态转移矩阵验证"""

    @pytest.mark.parametrize("current,target", [
        (NodeState.PENDING, NodeState.RUNNING),
        (NodeState.PENDING, NodeState.SKIPPED),
        (NodeState.PENDING, NodeState.CANCELLED),
        (NodeState.RUNNING, NodeState.FINISHED),
        (NodeState.RUNNING, NodeState.FAILED),
        (NodeState.RUNNING, NodeState.PAUSED),
        (NodeState.PAUSED, NodeState.RUNNING),
        (NodeState.PAUSED, NodeState.SKIPPED),
        (NodeState.FAILED, NodeState.RUNNING),  # 重试
        (NodeState.BLOCKED, NodeState.RUNNING),
    ])
    def test_valid_transitions(self, **kwargs):
        assert validate_node_transition(current, target) is True

    @pytest.mark.parametrize("current,target", [
        (NodeState.PENDING, NodeState.FINISHED),  # 跳过 running
        (NodeState.FINISHED, NodeState.RUNNING),   # 终态不可逆
        (NodeState.SKIPPED, NodeState.RUNNING),
        (NodeState.CANCELLED, NodeState.RUNNING),
        (NodeState.RUNNING, NodeState.SKIPPED),    # 必须经过 paused
        (NodeState.FAILED, NodeState.SKIPPED),     # failed 只能 retry
        (NodeState.FAILED, NodeState.FINISHED),
    ])
    def test_invalid_transitions(self, **kwargs):
        assert validate_node_transition(current, target) is False

    def test_finished_is_terminal(self):
        assert validate_node_transition(NodeState.FINISHED, NodeState.FINISHED) is False

    def test_cancelled_is_terminal(self):
        assert validate_node_transition(NodeState.CANCELLED, NodeState.CANCELLED) is False

    def test_skipped_is_terminal(self):
        assert validate_node_transition(NodeState.SKIPPED, NodeState.SKIPPED) is False

    @pytest.mark.parametrize("count", [1, 5])
    def test_retry_count_does_not_affect_transition(self, **kwargs):
        """重试次数不影响转移合法性"""
        for _ in range(count):
            assert validate_node_transition(NodeState.PENDING, NodeState.RUNNING) is True


class TestPipelineState(SimpleTestCase):
    """Pipeline 级状态转移矩阵验证"""

    @pytest.mark.parametrize("current,target", [
        (PipelineState.PENDING, PipelineState.RUNNING),
        (PipelineState.PENDING, PipelineState.CANCELLED),
        (PipelineState.RUNNING, PipelineState.COMPLETED),
        (PipelineState.RUNNING, PipelineState.FAILED),
        (PipelineState.RUNNING, PipelineState.PAUSED),
        (PipelineState.RUNNING, PipelineState.CANCELLED),
        (PipelineState.PAUSED, PipelineState.RUNNING),
        (PipelineState.PAUSED, PipelineState.CANCELLED),
        (PipelineState.FAILED, PipelineState.RUNNING),  # 重试整个 pipeline
    ])
    def test_valid_transitions(self, **kwargs):
        assert validate_pipeline_transition(current, target) is True

    @pytest.mark.parametrize("current,target", [
        (PipelineState.PENDING, PipelineState.COMPLETED),
        (PipelineState.PENDING, PipelineState.FAILED),
        (PipelineState.COMPLETED, PipelineState.RUNNING),
        (PipelineState.CANCELLED, PipelineState.RUNNING),
        (PipelineState.PAUSED, PipelineState.FAILED),
        (PipelineState.FAILED, PipelineState.COMPLETED),  # failed 只能重试
    ])
    def test_invalid_transitions(self, **kwargs):
        assert validate_pipeline_transition(current, target) is False

    def test_completed_is_terminal(self):
        assert validate_pipeline_transition(PipelineState.COMPLETED, PipelineState.COMPLETED) is False

    def test_cancelled_is_terminal(self):
        assert validate_pipeline_transition(PipelineState.CANCELLED, PipelineState.CANCELLED) is False


class TestMapBambooNodeState(SimpleTestCase):
    """bamboo-engine 状态 → NodeState 映射"""

    def test_maps_ready_to_pending(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.READY)
        assert result == NodeState.PENDING

    def test_maps_running_to_running(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.RUNNING)
        assert result == NodeState.RUNNING

    def test_maps_finished_to_finished(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.FINISHED)
        assert result == NodeState.FINISHED

    def test_maps_failed_to_failed(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.FAILED)
        assert result == NodeState.FAILED

    def test_maps_suspended_to_paused(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.SUSPENDED)
        assert result == NodeState.PAUSED

    def test_maps_revoked_to_cancelled(self):
        from bamboo_engine import states
        result = map_bamboo_node_state(states.REVOKED)
        assert result == NodeState.CANCELLED

    def test_unknown_state_returns_none(self):
        result = map_bamboo_node_state("UNKNOWN_STATE_12345")
        assert result is None

    def test_none_returns_none(self):
        result = map_bamboo_node_state(None)
        assert result is None
