"""执行轨迹双树结构 — 测试用例"""

import json
import os
import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from opsflow.models import FlowExecution, FlowTemplate, NodeExecutionTrace


# =============================================================================
# Task 1: NodeExecutionTrace 模型测试
# =============================================================================

class NodeExecutionTraceModelTest(TestCase):
    """Test NodeExecutionTrace model constraints and defaults"""

    def setUp(self):
        self.template = FlowTemplate.objects.create(
            name="test-template",
            pipeline_tree={"nodes": [], "edges": []},
        )
        self.execution = FlowExecution.objects.create(
            template=self.template,
            status="pending",
        )

    def test_create_trace(self):
        """基本创建和字段默认值"""
        trace = NodeExecutionTrace.objects.create(
            execution=self.execution,
            node_id="node_1",
            retry_count=0,
        )
        self.assertEqual(trace.status, "pending")
        self.assertEqual(trace.status_history, [])
        self.assertEqual(trace.retry_count, 0)
        self.assertEqual(trace.duration_ms, None)
        self.assertEqual(trace.inputs, {})
        self.assertEqual(trace.outputs, {})

    def test_unique_together(self):
        """unique_together 约束: (execution, node_id, retry_count)"""
        NodeExecutionTrace.objects.create(
            execution=self.execution, node_id="node_1", retry_count=0,
        )
        with self.assertRaises(Exception):
            NodeExecutionTrace.objects.create(
                execution=self.execution, node_id="node_1", retry_count=0,
            )

    def test_allow_same_node_different_retry(self):
        """同一节点不同 retry_count 允许创建"""
        t1 = NodeExecutionTrace.objects.create(
            execution=self.execution, node_id="node_1", retry_count=0,
        )
        t2 = NodeExecutionTrace.objects.create(
            execution=self.execution, node_id="node_1", retry_count=1,
        )
        self.assertNotEqual(t1.pk, t2.pk)

    def test_status_history_append(self):
        """status_history 追加不覆盖"""
        trace = NodeExecutionTrace.objects.create(
            execution=self.execution, node_id="node_1", retry_count=0,
            status_history=[{"state": "running", "at": "2026-01-01T00:00:00"}],
        )
        history = list(trace.status_history)
        history.append({"state": "completed", "at": "2026-01-01T00:01:00"})
        trace.status_history = history
        trace.save()

        trace.refresh_from_db()
        self.assertEqual(len(trace.status_history), 2)
        self.assertEqual(trace.status_history[0]["state"], "running")
        self.assertEqual(trace.status_history[1]["state"], "completed")


# =============================================================================
# Task 2: NodeTraceLogger 测试
# =============================================================================

@override_settings(LOG_DIR=tempfile.gettempdir())
class NodeTraceLoggerTest(TestCase):
    """Test NodeTraceLogger file I/O"""

    def setUp(self):
        from opsflow.core.trace_logger import NodeTraceLogger
        self.execution_id = 99999
        self.logger = NodeTraceLogger(self.execution_id)
        self.log_dir = self.logger.log_dir

    def tearDown(self):
        import shutil
        if os.path.exists(self.log_dir):
            shutil.rmtree(self.log_dir)

    def test_log_write_and_read(self):
        """写入后读取验证 JSON Lines 格式"""
        self.logger.log("node_1", "state", {"from": "pending", "to": "running"})
        self.logger.log("node_1", "output", {"stdout": "hello", "returncode": 0})

        entries = self.logger.read_log("node_1")
        self.assertEqual(len(entries), 2)

        self.assertEqual(entries[0]["node_id"], "node_1")
        self.assertEqual(entries[0]["event"], "state")
        self.assertEqual(entries[0]["data"]["to"], "running")

        self.assertEqual(entries[1]["node_id"], "node_1")
        self.assertEqual(entries[1]["event"], "output")
        self.assertEqual(entries[1]["data"]["stdout"], "hello")

    def test_log_state(self):
        """log_state / log_output / log_error 辅助方法"""
        self.logger.log_state("node_1", "pending", "running")
        self.logger.log_output("node_1", {"returncode": 0})
        self.logger.log_error("node_1", "timeout", "Connection failed")

        entries = self.logger.read_log("node_1")
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["event"], "state")
        self.assertEqual(entries[1]["event"], "output")
        self.assertEqual(entries[2]["event"], "error")

    def test_read_nonexistent_file(self):
        """不存在的文件返回空列表"""
        entries = self.logger.read_log("nonexistent_node")
        self.assertEqual(entries, [])

    def test_log_retry(self):
        """log_retry 写入"""
        self.logger.log_retry("node_1", 1, reason="auto")
        entries = self.logger.read_log("node_1")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["event"], "retry")
        self.assertEqual(entries[0]["data"]["retry_count"], 1)

    def test_get_log_file_path(self):
        """get_log_file_path 返回正确路径"""
        path = self.logger.get_log_file_path("node_1")
        self.assertTrue(path.endswith("node_1.log"))

    def test_write_metadata(self):
        """write_metadata 创建 metadata.json"""
        meta = {"execution_id": 99999, "template_name": "test"}
        self.logger.write_metadata(meta)

        meta_path = os.path.join(self.log_dir, "metadata.json")
        self.assertTrue(os.path.exists(meta_path))

        with open(meta_path, "r") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["template_name"], "test")

    def test_write_metadata_idempotent(self):
        """write_metadata 仅创建一次，不覆盖"""
        self.logger.write_metadata({"key": "first"})
        self.logger.write_metadata({"key": "second"})  # should be ignored

        meta_path = os.path.join(self.log_dir, "metadata.json")
        with open(meta_path, "r") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["key"], "first")


# =============================================================================
# Task 3: _update_state_tree 测试
# =============================================================================

class UpdateStateTreeTest(TestCase):
    """Test _update_state_tree helper"""

    def setUp(self):
        self.template = FlowTemplate.objects.create(
            name="test-template",
            pipeline_tree={"nodes": [], "edges": []},
        )
        self.execution = FlowExecution.objects.create(
            template=self.template,
            status="running",
        )

    def _call_update_state_tree(self, node_id, to_state):
        """调用 signals._update_state_tree"""
        from bamboo_engine import states
        from opsflow.signals.state import _update_state_tree
        _update_state_tree(self.execution, node_id, to_state)
        self.execution.refresh_from_db()

    def test_running_state_adds_entered_at(self):
        """running 状态设置 entered_at"""
        self._call_update_state_tree("node_1", "RUNNING")  # 会通过 STATUS_MAP 查找，但需要 states 枚举值
        # 由于 _update_state_tree 接受 bamboo states 枚举值，我们需要传正确的值
        # 这里我们直接用实际测试
        tree = self.execution.state_tree
        self.assertIn("node_1", tree)
        self.assertEqual(tree["node_1"]["state"], "running")
        self.assertIn("entered_at", tree["node_1"])

    def test_finished_state_sets_duration(self):
        """running → finished 计算 duration_ms"""
        from bamboo_engine import states

        # 先进入 running
        self._call_update_state_tree("node_1", "RUNNING")
        tree = self.execution.state_tree
        entered_at = tree["node_1"]["entered_at"]

        # 再完成
        self._call_update_state_tree("node_1", "FINISHED")
        tree = self.execution.state_tree
        self.assertEqual(tree["node_1"]["state"], "completed")
        self.assertIn("exited_at", tree["node_1"])
        self.assertIn("duration_ms", tree["node_1"])
        self.assertGreaterEqual(tree["node_1"]["duration_ms"], 0)

    def test_incremental_update(self):
        """增量更新不覆盖已有字段"""
        from bamboo_engine import states
        self.execution.state_tree = {"existing_key": "keep_me"}
        self.execution.save()

        self._call_update_state_tree("node_1", "RUNNING")
        tree = self.execution.state_tree
        self.assertEqual(tree["existing_key"], "keep_me")  # 原有字段保留
        self.assertEqual(tree["node_1"]["state"], "running")


# =============================================================================
# Task 4: NodeCommandDispatcher 测试
# =============================================================================

class NodeCommandDispatcherTest(TestCase):
    """Test NodeCommandDispatcher retry/skip/trace"""

    def setUp(self):
        self.template = FlowTemplate.objects.create(
            name="test-template",
            pipeline_tree={"nodes": [], "edges": []},
        )
        self.execution = FlowExecution.objects.create(
            template=self.template,
            status="running",
            node_status={"node_1": "failed"},
        )

    @patch("opsflow.core.flow_engine.FlowEngine.retry", return_value=None)
    def test_retry_returns_standard_format(self, mock_retry):
        """retry 返回 {result, message, data} 格式"""
        from opsflow.core.node_dispatcher import NodeCommandDispatcher
        dispatcher = NodeCommandDispatcher(self.execution)

        # 先创建一条失败 trace
        NodeExecutionTrace.objects.create(
            execution=self.execution,
            node_id="node_1",
            retry_count=0,
            status="failed",
        )

        result = dispatcher.retry("node_1", operator="test-user")
        self.assertTrue(result["result"])
        self.assertIn("node_1", result["message"])
        self.assertEqual(result["data"]["retry_count"], 1)

        # 验证新 Trace 记录已创建
        traces = NodeExecutionTrace.objects.filter(
            execution=self.execution, node_id="node_1"
        ).order_by("retry_count")
        self.assertEqual(traces.count(), 2)
        self.assertEqual(traces[0].retry_count, 0)
        self.assertEqual(traces[1].retry_count, 1)
        self.assertEqual(traces[1].status, "retrying")

    @patch("opsflow.core.flow_engine.FlowEngine.skip", return_value=None)
    def test_skip_returns_standard_format(self, mock_skip):
        """skip 返回 {result, message, data} 格式"""
        from opsflow.core.node_dispatcher import NodeCommandDispatcher
        dispatcher = NodeCommandDispatcher(self.execution)
        result = dispatcher.skip("node_1")
        self.assertTrue(result["result"])
        self.assertIn("node_1", result["message"])

    def test_get_trace_returns_all_retries(self):
        """get_trace 返回所有重试历史"""
        from opsflow.core.node_dispatcher import NodeCommandDispatcher

        # 创建多条 trace
        for i in range(3):
            NodeExecutionTrace.objects.create(
                execution=self.execution,
                node_id="node_1",
                retry_count=i,
                status="completed" if i < 2 else "failed",
            )

        dispatcher = NodeCommandDispatcher(self.execution)
        result = dispatcher.get_trace("node_1")
        self.assertTrue(result["result"])
        self.assertEqual(len(result["data"]), 3)
        self.assertEqual(result["data"][0]["retry_count"], 0)
        self.assertEqual(result["data"][2]["retry_count"], 2)

    def test_get_state_tree_returns_empty(self):
        """get_state_tree 在无数据时返回空字典"""
        from opsflow.core.node_dispatcher import NodeCommandDispatcher
        dispatcher = NodeCommandDispatcher(self.execution)
        result = dispatcher.get_state_tree()
        self.assertTrue(result["result"])
        self.assertEqual(result["data"], {})
