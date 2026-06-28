"""Optional 节点失败自动跳过测试 — _check_optional_skip / on_post_set_state 集成"""
from django.test import SimpleTestCase

from unittest.mock import Mock, patch

from opsflow.signals.handlers import _check_optional_skip


def _make_execution(template_snapshot=None, pipeline_tree=None, template_id=1):
    """创建 mock execution — 支持 template_snapshot 和 pipeline_tree fallback"""
    exec_mock = Mock()
    exec_mock.id = 42
    exec_mock.template_id = template_id
    exec_mock.template_snapshot = template_snapshot

    template = Mock()
    template.pipeline_tree = pipeline_tree
    exec_mock.template = template
    return exec_mock


# =============================================================================
# _check_optional_skip — 辅助函数单元测试
# =============================================================================


class TestCheckOptionalSkip(SimpleTestCase):
    """_check_optional_skip 辅助函数"""

    def test_optional_true_in_snapshot(self):
        """template_snapshot 中 optional=True → 返回 True"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1', 'optional': True},
                    {'id': 'node_2', 'optional': False},
                ],
            },
        })
        result = _check_optional_skip(execution, 'node_1')
        self.assertTrue(result)

    def test_optional_false_returns_false(self):
        """optional=False → 返回 False"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1', 'optional': False},
                ],
            },
        })
        result = _check_optional_skip(execution, 'node_1')
        self.assertFalse(result)

    def test_no_optional_field_returns_false(self):
        """没有 optional 字段 → 返回 False"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1'},
                ],
            },
        })
        result = _check_optional_skip(execution, 'node_1')
        self.assertFalse(result)

    def test_node_not_found_returns_false(self):
        """节点不在树中 → 返回 False"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1'},
                ],
            },
        })
        result = _check_optional_skip(execution, 'unknown_node')
        self.assertFalse(result)

    def test_no_snapshot_fallback_to_pipeline_tree(self):
        """template_snapshot=None → 回退到 template.pipeline_tree"""
        execution = _make_execution(
            template_snapshot=None,
            pipeline_tree={
                'nodes': [
                    {'id': 'node_1', 'optional': True},
                ],
            },
        )
        result = _check_optional_skip(execution, 'node_1')
        self.assertTrue(result)

    def test_no_snapshot_no_tree_returns_false(self):
        """无 snapshot 也无 pipeline_tree → 返回 False"""
        execution = _make_execution(template_snapshot=None, pipeline_tree=None)
        result = _check_optional_skip(execution, 'node_1')
        self.assertFalse(result)

    def test_exception_caught_returns_false(self):
        """异常时返回 False 不抛异常"""
        execution = _make_execution(template_snapshot=None, pipeline_tree=None)
        execution.template = None
        execution.template_id = None
        result = _check_optional_skip(execution, 'node_1')
        self.assertFalse(result)


# =============================================================================
# on_post_set_state — 集成测试（mock FlowExecution.objects.get 避免 DB）
# =============================================================================


class TestOptionalSkipInSignal(SimpleTestCase):
    """on_post_set_state 信号中 optional skip 集成"""

    def _trigger_failed_signal(self, execution, node_id='node_1'):
        """模拟触发 on_post_set_state FAILED 信号"""
        with patch('opsflow.models.FlowExecution.objects.get', return_value=execution), \
             patch('opsflow.signals.handlers.post_set_state'):
            from opsflow.signals.handlers import on_post_set_state
            on_post_set_state(
                sender=Mock(),
                node_id=node_id,
                to_state='FAILED',
                version='v1',
                root_id='pipeline_root',
                parent_id='',
                loop=None,
            )

    def test_non_optional_node_does_not_skip(self):
        """非 optional 节点失败 → 不调用 FlowEngine.skip"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1'},
                ],
            },
        })

        with patch('opsflow.core.auto_retry.dispatch_auto_retry', return_value=False), \
             patch('opsflow.core.flow_engine.FlowEngine') as mock_engine_cls:
            self._trigger_failed_signal(execution)
            mock_engine_cls.assert_not_called()

    def test_optional_node_skips(self):
        """optional 节点失败 → 自动调用 FlowEngine.skip"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1', 'optional': True},
                ],
            },
        })

        with patch('opsflow.core.auto_retry.dispatch_auto_retry', return_value=False), \
             patch('opsflow.core.flow_engine.FlowEngine') as mock_engine_cls:
            self._trigger_failed_signal(execution)
            mock_engine_cls.return_value.skip.assert_called_once_with('node_1')

    def test_auto_retry_priority_over_optional(self):
        """auto_retry 活跃时 optional 不介入 — 重试优先"""
        execution = _make_execution(template_snapshot={
            'pipeline_tree': {
                'nodes': [
                    {'id': 'node_1', 'optional': True},
                ],
            },
        })

        with patch('opsflow.core.auto_retry.dispatch_auto_retry', return_value=True), \
             patch('opsflow.core.flow_engine.FlowEngine') as mock_engine_cls:
            self._trigger_failed_signal(execution)
            mock_engine_cls.return_value.skip.assert_not_called()
