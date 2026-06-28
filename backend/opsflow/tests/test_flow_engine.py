"""FlowEngine 测试 — 状态管理 + run/retry/skip"""

from django.test import SimpleTestCase
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


from opsflow.core.flow_engine import FlowEngine


class TestFlowEngineStateManagement(SimpleTestCase):
    """FlowEngine 状态管理 — 不需要 bamboo 依赖"""

    def _make_execution(self, status="pending"):
        """创建 mock execution"""
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.status = status
        exec_mock.template = Mock()
        exec_mock.template.name = "test"
        exec_mock.template.pipeline_tree = {"nodes": [], "edges": []}
        exec_mock.context = {}
        exec_mock.node_status = {}
        exec_mock.started_at = None
        exec_mock.ended_at = None
        exec_mock.template_snapshot = None
        exec_mock.state_tree = {}
        return exec_mock

    def test_init_stores_execution(self):
        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        assert engine.execution == exec_mock
        assert engine.template == exec_mock.template

    def test_start_sets_running_status(self):
        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        with patch("opsflow.tasks.execute_pipeline_task") as mock_task:
            engine.start()
            assert exec_mock.status == "running"
            assert exec_mock.started_at is not None
            mock_task.delay.assert_called_once_with(1)

    def test_start_sync_calls_task_directly(self):
        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        with patch("opsflow.tasks.execute_pipeline_task") as mock_task:
            engine.start(sync=True)
            mock_task.assert_called_once_with(1)  # 直接调用, 非 .delay

    def test_start_without_node_status_init(self):
        exec_mock = self._make_execution()
        exec_mock.node_status = None
        engine = FlowEngine(exec_mock)
        with patch("opsflow.tasks.execute_pipeline_task"):
            engine.start()
            assert exec_mock.node_status == {}

    def test_pause_sets_paused_status(self):
        exec_mock = self._make_execution(status="running")
        engine = FlowEngine(exec_mock)
        with patch("bamboo_engine.api") as mock_api:
            mock_api.pause_pipeline.return_value = Mock(result=True)
            engine.pause()
            assert exec_mock.status == "paused"
            exec_mock.save.assert_called()

    @patch("bamboo_engine.api")
    def test_resume_sets_running(self, **kwargs):
        exec_mock = self._make_execution(status="paused")
        exec_mock.context = {"bamboo_pipeline_id": "bp_001"}
        engine = FlowEngine(exec_mock)
        mock_api.resume_pipeline.return_value = Mock(result=True)
        engine.resume()
        assert exec_mock.status == "running"

    @patch("bamboo_engine.api")
    def test_resume_failure_does_not_change_status(self, **kwargs):
        exec_mock = self._make_execution(status="paused")
        exec_mock.context = {"bamboo_pipeline_id": "bp_001"}
        engine = FlowEngine(exec_mock)
        mock_api.resume_pipeline.return_value = Mock(result=False, message="no pipeline")
        engine.resume()
        # 失败时不改变状态
        assert exec_mock.status == "paused"

    @patch("bamboo_engine.api")
    def test_cancel_sets_cancelled_status(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.context = {"bamboo_pipeline_id": "bp_001"}
        engine = FlowEngine(exec_mock)
        mock_api.revoke_pipeline.return_value = Mock(result=True)
        engine.cancel()
        assert exec_mock.status == "cancelled"
        assert exec_mock.ended_at is not None

    @patch("bamboo_engine.api")
    def test_cancel_without_bamboo_id(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.context = {}  # no bamboo_pipeline_id
        engine = FlowEngine(exec_mock)
        engine.cancel()
        assert exec_mock.status == "cancelled"
        mock_api.revoke_pipeline.assert_not_called()

    @patch("bamboo_engine.api")
    def test_retry_updates_node_status(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.node_status = {"n1": "failed"}
        engine = FlowEngine(exec_mock)
        mock_api.retry_node.return_value = Mock(result=True)
        engine.retry("n1")
        assert exec_mock.node_status["n1"] == "retrying"
        assert exec_mock.status == "running"

    @patch("bamboo_engine.api")
    def test_skip_updates_node_status(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.node_status = {"n1": "failed"}
        engine = FlowEngine(exec_mock)
        mock_api.skip_node.return_value = Mock(result=True)
        engine.skip("n1")
        assert exec_mock.node_status["n1"] == "skipped"

    @patch("bamboo_engine.api")
    def test_force_fail_sets_failed_status(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.node_status = {"n1": "running"}
        engine = FlowEngine(exec_mock)
        mock_api.forced_fail_activity.return_value = Mock(result=True)
        engine.force_fail("n1", ex_data="manual")
        assert exec_mock.node_status["n1"] == "failed"

    @patch("bamboo_engine.api")
    def test_pause_no_bamboo_id_still_saves_status(self, **kwargs):
        exec_mock = self._make_execution(status="running")
        exec_mock.context = {}
        engine = FlowEngine(exec_mock)
        engine.pause()
        assert exec_mock.status == "paused"


class TestFlowEngineRun(SimpleTestCase):
    """FlowEngine.run() — pipline 构建+执行"""

    def _make_execution(self, frozen_tree=None):
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.status = "running"
        exec_mock.template = Mock()
        exec_mock.template.name = "test"
        exec_mock.template.pipeline_tree = {"nodes": [], "edges": []}
        exec_mock.template_snapshot = {
            "pipeline_tree": frozen_tree or {"nodes": [], "edges": []},
            "global_vars": {},
        }
        exec_mock.context = {}
        exec_mock.node_status = {}
        exec_mock.state_tree = {}
        return exec_mock

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("bamboo_engine.api")
    def test_run_success_path(self, **kwargs):
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = (
            {"id": "bp_001", "activities": {"act1": {"type": "ServiceActivity"}}},
            {"uuid": "n1"},
        )
        mock_api.run_pipeline.return_value = Mock(result=True)

        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        engine.run()

        mock_validate.assert_called_once()
        mock_build.assert_called_once()
        mock_api.run_pipeline.assert_called_once()
        assert exec_mock.context["bamboo_pipeline_id"] == "bp_001"

    @patch("opsflow.core.flow_engine.validate_pipeline")
    def test_run_validation_failure(self, **kwargs):
        mock_validate.return_value = {"valid": False, "errors": ["bad pipeline"],
                                       "warnings": []}

        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"
        assert exec_mock.ended_at is not None

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("bamboo_engine.api")
    def test_run_api_failure(self, **kwargs):
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = (
            {"id": "bp_001", "activities": {"act1": {"type": "ServiceActivity"}}},
            {"uuid": "n1"},
        )
        mock_api.run_pipeline.return_value = Mock(result=False, message="engine error")

        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("bamboo_engine.api")
    def test_run_exception_handling(self, **kwargs):
        mock_validate.side_effect = Exception("unexpected error")

        exec_mock = self._make_execution()
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"
        assert exec_mock.ended_at is not None

    def test_run_without_template_snapshot(self):
        exec_mock = self._make_execution()
        exec_mock.template_snapshot = None
        engine = FlowEngine(exec_mock)
        # 应该不会崩溃
        with patch("opsflow.core.flow_engine.validate_pipeline") as mock_v:
            mock_v.side_effect = Exception("error")
            engine.run()  # 不应抛出异常


class TestFlowEngineWSNotification(SimpleTestCase):
    """WebSocket 通知（best-effort）"""

    def test_notify_completed_no_channel_layer(self):
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.status = "completed"
        engine = FlowEngine(exec_mock)
        # 没有 channel layer 时不应抛出异常
        with patch("channels.layers.get_channel_layer") as mock_cl:
            mock_cl.return_value = None
            engine._notify_completed()  # 不应抛出

    def test_send_ws_exception_handled(self):
        exec_mock = Mock()
        exec_mock.id = 1
        exec_mock.status = "completed"
        engine = FlowEngine(exec_mock)
        with patch("channels.layers.get_channel_layer") as mock_cl:
            mock_cl.side_effect = Exception("no channels")
            engine._send_ws_completed()  # 不应抛出
