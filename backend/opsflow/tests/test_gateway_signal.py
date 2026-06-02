"""排他网关信号处理测试 — 节点状态更新 + 状态树增量

验证 on_post_set_state 信号处理器对排他网关节点的处理正确性：
- gateway 节点状态更新写入 node_status
- 状态树增量更新
- 分支节点状态正常流转
"""

from unittest.mock import Mock, patch

import pytest

from bamboo_engine import states
from opsflow.signals.state import _update_execution_node_status, _update_state_tree
from opsflow.signals.handlers import on_post_set_state


class TestExclusiveGatewaySignalStateUpdate:
    """排他网关场景下 _update_execution_node_status 和 _update_state_tree"""

    def _make_execution(self, context=None, node_status=None, state_tree=None):
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.context = context or {
            "node_id_map": {"bamboo_uuid_gw1": "gw1", "bamboo_uuid_n1": "n1"},
        }
        exec_mock.node_status = node_status or {}
        exec_mock.state_tree = state_tree or {}
        return exec_mock

    def test_gateway_finished_updates_node_status(self):
        """排他网关 FINISHED → node_status[gw] == 'completed'"""
        execution = self._make_execution()
        _update_execution_node_status(execution, "bamboo_uuid_gw1", states.FINISHED)
        assert execution.node_status.get("gw1") == "completed"
        execution.save.assert_called_with(update_fields=["node_status"])

    def test_gateway_running_updates_node_status(self):
        """排他网关 RUNNING → node_status[gw] == 'running'"""
        execution = self._make_execution()
        _update_execution_node_status(execution, "bamboo_uuid_gw1", states.RUNNING)
        assert execution.node_status.get("gw1") == "running"

    def test_branch_node_finished_after_gateway(self):
        """网关选定分支上的节点 FINISHED 后正确记录"""
        execution = self._make_execution(
            node_status={"gw1": "completed"}
        )
        _update_execution_node_status(execution, "bamboo_uuid_n1", states.FINISHED)
        assert execution.node_status.get("n1") == "completed"
        assert execution.node_status.get("gw1") == "completed"  # 保留原值

    def test_state_tree_contains_gateway(self):
        """state_tree 增量更新包含网关节点"""
        execution = self._make_execution()
        _update_state_tree(execution, "bamboo_uuid_gw1", states.RUNNING)
        assert "bamboo_uuid_gw1" in execution.state_tree
        assert execution.state_tree["bamboo_uuid_gw1"]["state"] == "running"
        assert "entered_at" in execution.state_tree["bamboo_uuid_gw1"]

    def test_state_tree_gateway_completed_has_duration(self):
        """网关从 RUNNING → FINISHED，状态树记录耗时"""
        execution = self._make_execution()
        _update_state_tree(execution, "bamboo_uuid_gw1", states.RUNNING)
        _update_state_tree(execution, "bamboo_uuid_gw1", states.FINISHED)
        entry = execution.state_tree["bamboo_uuid_gw1"]
        assert entry["state"] == "completed"
        assert entry["exited_at"] is not None
        assert "duration_ms" in entry

    def test_id_map_fallback_when_not_found(self):
        """node_id_map 中没有该节点时直接使用 bamboo UUID"""
        execution = self._make_execution(context={})
        _update_execution_node_status(execution, "unknown_uuid", states.FINISHED)
        assert execution.node_status.get("unknown_uuid") == "completed"


class TestExclusiveGatewaySignalHandler:
    """on_post_set_state 信号处理器在排他网关场景下的行为"""

    def _make_on_post_set_state_args(self, node_id="bu_gw1", to_state=states.FINISHED):
        """构造 on_post_set_state 的标准参数"""
        return {
            "sender": Mock(),
            "node_id": node_id,
            "to_state": to_state,
            "version": "v1",
            "root_id": "root_1",
            "parent_id": None,
            "loop": 0,
        }

    def test_gateway_finished_dispatches_all_sub_handlers(self):
        """排他网关 FINISHED 时所有子 handler 被调用"""
        execution = Mock()
        execution.id = 1
        execution.context = {"node_id_map": {"bu_gw1": "gw1"}}
        execution.node_status = {}
        execution.state_tree = {}

        patches = [
            patch("opsflow.models.FlowExecution"),
            patch("opsflow.signals.handlers._update_execution_node_status"),
            patch("opsflow.signals.handlers._update_state_tree"),
            patch("opsflow.signals.handlers._record_node_trace"),
            patch("opsflow.signals.handlers._update_node_timeout"),
            patch("opsflow.signals.handlers._log_node_result"),
            patch("opsflow.signals.handlers._write_node_trace_log"),
            patch("opsflow.signals.handlers._notify_node_status"),
        ]
        mocks = [p.start() for p in patches]
        mock_flow_exec = mocks[0]
        mock_flow_exec.objects.get.return_value = execution

        try:
            on_post_set_state(**self._make_on_post_set_state_args(
                to_state=states.FINISHED))
        finally:
            for p in patches:
                p.stop()

        mock_node_status, mock_state_tree, mock_trace, mock_timeout = mocks[1:5]
        mock_node_status.assert_called_once_with(execution, "bu_gw1", states.FINISHED)
        mock_state_tree.assert_called_once_with(execution, "bu_gw1", states.FINISHED)
        mock_trace.assert_called_once_with(execution, "bu_gw1", states.FINISHED)
        mock_timeout.assert_called_once_with(execution, "bu_gw1", states.FINISHED)

    def test_gateway_running_updates_current_node(self):
        """排他网关变为 RUNNING 时更新 current_node"""
        execution = Mock()
        execution.id = 1
        execution.context = {"node_id_map": {"bu_gw1": "gw1"}}
        execution.node_status = {}
        execution.state_tree = {}
        execution.current_node = None

        patches = [
            patch("opsflow.models.FlowExecution"),
            patch("opsflow.signals.handlers._update_execution_node_status"),
            patch("opsflow.signals.handlers._update_state_tree"),
            patch("opsflow.signals.handlers._record_node_trace"),
            patch("opsflow.signals.handlers._update_node_timeout"),
        ]
        mocks = [p.start() for p in patches]
        mock_flow_exec = mocks[0]
        mock_flow_exec.objects.get.return_value = execution

        try:
            on_post_set_state(**self._make_on_post_set_state_args(
                to_state=states.RUNNING))
        finally:
            for p in patches:
                p.stop()

        assert execution.current_node == "gw1"
        execution.save.assert_any_call(update_fields=["current_node"])

    def test_gateway_running_sends_ws_notification(self):
        """排他网关 RUNNING 时发送 WS 通知"""
        execution = Mock()
        execution.id = 1
        execution.context = {"node_id_map": {"bu_gw1": "gw1"}}
        execution.node_status = {}
        execution.state_tree = {}

        patches = [
            patch("opsflow.models.FlowExecution"),
            patch("opsflow.signals.handlers._update_execution_node_status"),
            patch("opsflow.signals.handlers._update_state_tree"),
            patch("opsflow.signals.handlers._record_node_trace"),
            patch("opsflow.signals.handlers._update_node_timeout"),
            patch("opsflow.signals.handlers._notify_node_status"),
        ]
        mocks = [p.start() for p in patches]
        mock_flow_exec = mocks[0]
        mock_flow_exec.objects.get.return_value = execution
        mock_notify = mocks[-1]

        try:
            on_post_set_state(**self._make_on_post_set_state_args(
                to_state=states.RUNNING))
        finally:
            for p in patches:
                p.stop()

        mock_notify.assert_called_once_with(execution, "gw1", "running")
