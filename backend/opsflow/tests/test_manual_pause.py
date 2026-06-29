"""Manual Pause 原子测试 — ManualPausePlugin / PluginService 集成"""
from django.test import SimpleTestCase

from unittest.mock import Mock, patch


class TestManualPausePlugin(SimpleTestCase):
    """ManualPausePlugin 原子"""

    def test_execute_returns_success(self):
        """execute() 返回 {success: True}"""
        from opsflow.plugins.common.manual_pause import ManualPausePlugin
        plugin = ManualPausePlugin()
        result = plugin.execute()
        self.assertTrue(result["success"])
        self.assertTrue(result["data"]["paused"])

    def test_get_form_config_returns_empty(self):
        """无参数配置"""
        from opsflow.plugins.common.manual_pause import ManualPausePlugin
        config = ManualPausePlugin.get_form_config()
        self.assertEqual(config, [])

    def test_plugin_metadata(self):
        """元数据字段完整"""
        from opsflow.plugins.common.manual_pause import ManualPausePlugin
        self.assertEqual(ManualPausePlugin.code, 'manual_pause')
        self.assertEqual(ManualPausePlugin.group, 'Common Tools')
        self.assertEqual(ManualPausePlugin.risk_level, 'low')


class TestPluginServiceManualPause(SimpleTestCase):
    """PluginService.execute 中 manual_pause 暂停触发"""

    def _make_data(self):
        """创建模拟的 data 对象"""
        data = Mock()
        data.inputs = {
            '_atom_type': 'manual_pause',
            '_execution_id': 42,
        }
        data.outputs = {}
        return data

    def test_execute_pauses_pipeline(self):
        """PluginService 执行 manual_pause → 调用 FlowEngine.pause()"""
        execution = Mock()
        execution.id = 42
        execution.context = {}

        with patch('opsflow.models.FlowExecution.objects.get', return_value=execution), \
             patch('opsflow.core.flow_engine.FlowEngine') as mock_engine_cls:

            from opsflow.core.plugin_service_adapter import PluginService
            service = PluginService()
            data = self._make_data()
            result = service.execute(data, parent_data=None)

            self.assertTrue(result)
            mock_engine_cls.return_value.pause.assert_called_once()
            self.assertEqual(execution.context['_pause_reason'], 'manual_pause')

    def test_execute_db_error_caught(self):
        """DB 查询异常时捕获不抛异常"""
        with patch('opsflow.models.FlowExecution.objects.get', side_effect=Exception("DB error")), \
             patch('opsflow.core.flow_engine.FlowEngine') as mock_engine_cls:

            from opsflow.core.plugin_service_adapter import PluginService
            service = PluginService()
            data = self._make_data()
            result = service.execute(data, parent_data=None)

            # 异常被捕获，仍返回 True
            self.assertTrue(result)
            mock_engine_cls.return_value.pause.assert_not_called()
