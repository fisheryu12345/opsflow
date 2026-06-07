"""排他网关信号处理测试 — 节点状态更新 + 状态树增量

验证 on_post_set_state 信号处理器对排他网关节点的处理正确性：
- 节点状态写入 node_status（原始 X6 ID 直接作为 key）
- 状态树增量更新
- 分支节点状态正常流转
"""

from unittest.mock import Mock, patch

import pytest

from bamboo_engine import states
from opsflow.signals.state import _update_execution_node_status, _update_state_tree
from opsflow.signals.handlers import on_post_set_state, _push_node_status_via_ws


class TestExclusiveGatewaySignalStateUpdate:
    """排他网关场景下 _update_execution_node_status 和 _update_state_tree"""

    def _make_execution(self, context=None, node_status=None, state_tree=None):
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.context = context or {"bamboo_pipeline_id": "root_1"}
        exec_mock.node_status = node_status or {}
        exec_mock.state_tree = state_tree or {}
        return exec_mock

    def test_gateway_finished_updates_node_status(self):
        """排他网关 FINISHED → node_status[原始ID] == 'completed'（不再经过 id_map）"""
        execution = self._make_execution()
        _update_execution_node_status(execution, "bamboo_uuid_gw1", states.FINISHED)
        assert execution.node_status.get("bamboo_uuid_gw1") == "completed"
        execution.save.assert_called_with(update_fields=["node_status"])

    def test_gateway_running_updates_node_status(self):
        """排他网关 RUNNING → node_status[原始ID] == 'running'"""
        execution = self._make_execution()
        _update_execution_node_status(execution, "bamboo_uuid_gw1", states.RUNNING)
        assert execution.node_status.get("bamboo_uuid_gw1") == "running"

    def test_branch_node_finished_after_gateway(self):
        """网关选定分支上的节点 FINISHED 后正确记录"""
        execution = self._make_execution(
            node_status={"bamboo_uuid_gw1": "completed"}
        )
        _update_execution_node_status(execution, "bamboo_uuid_n1", states.FINISHED)
        assert execution.node_status.get("bamboo_uuid_n1") == "completed"
        assert execution.node_status.get("bamboo_uuid_gw1") == "completed"  # 保留原值

    def test_state_tree_contains_gateway(self):
        """state_tree 增量更新包含网关节点（使用原始 node_id）"""
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

    def test_node_id_directly_used_as_key(self):
        """node_id 直接作为 node_status key（无 id_map 映射）"""
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
        execution.context = {"bamboo_pipeline_id": "root_1"}
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
        """排他网关变为 RUNNING 时 current_node 使用原始 node_id（无 id_map 映射）"""
        execution = Mock()
        execution.id = 1
        execution.context = {"bamboo_pipeline_id": "root_1"}
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

        # 不再经过 id_map 映射，bu_gw1 直接作为原始 ID
        assert execution.current_node == "bu_gw1"
        execution.save.assert_any_call(update_fields=["current_node"])

    def test_gateway_running_processes_handler_without_error(self):
        """排他网关 RUNNING 时 handler 正常执行（不依赖已移除的 _notify_node_status）"""
        execution = Mock()
        execution.id = 1
        execution.context = {"bamboo_pipeline_id": "root_1"}
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

        assert execution.current_node == "bu_gw1"
        execution.save.assert_any_call(update_fields=["current_node"])


class TestWsNodeStatusPush:
    """_push_node_status_via_ws WebSocket 推送测试"""

    def test_skip_when_no_created_by(self):
        """没有 created_by_id 时跳过推送"""
        execution = Mock()
        execution.created_by_id = None
        execution.node_status = {}
        _push_node_status_via_ws(execution, "n1")

    def test_skip_when_no_status(self):
        """node_id 不在 node_status 中时跳过推送"""
        execution = Mock()
        execution.created_by_id = 1
        execution.node_status = {}
        _push_node_status_via_ws(execution, "n1")

    @patch("channels.layers.get_channel_layer")
    def test_push_called_with_correct_args(self, mock_get_cl):
        """正常推送时 channel_layer.group_send 被正确调用"""
        mock_cl = Mock()
        mock_get_cl.return_value = mock_cl

        execution = Mock()
        execution.id = 42
        execution.created_by_id = 7
        execution.node_status = {"n1": "completed"}

        _push_node_status_via_ws(execution, "n1")

        mock_cl.group_send.assert_called_once_with(
            "user_7",
            {
                "type": "push.message",
                "json": {
                    "contentType": "NODE_STATUS",
                    "content": {
                        "execution_id": 42,
                        "node_id": "n1",
                        "status": "completed",
                    },
                },
            }
        )
