"""ITSMEngine 测试 — PipelineWrapper 迁移验证"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from itsm.models.ticket import Ticket
from itsm.models.workflow import Workflow, WorkflowVersion


def _create_user(username='testuser'):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create(username=username, name=username, password='test')


def _create_ticket(**kwargs):
    wf = Workflow.objects.create(name='test-wf', itsm_type='incident')
    states = kwargs.pop('_states', {
        '1': {'id': 1, 'type': 'START', 'name': '开始'},
        '2': {'id': 2, 'type': 'END', 'name': '结束'},
    })
    transitions = kwargs.pop('_transitions', {
        't1': {'from_state_id': 1, 'to_state_id': 2, 'condition': {}, 'condition_type': 'default'},
    })
    wv = WorkflowVersion.objects.create(workflow=wf, version=1, states=states, fields={}, transitions=transitions)
    defaults = {'title': 'test', 'workflow_version': wv, 'itsm_type': 'incident', 'priority': 'P3'}
    defaults.update(kwargs)
    return Ticket.objects.create(**defaults)


class ITSMEngineRunTests(TestCase):
    """ITSMEngine.run() — pipeline 启动"""

    @patch('itsm.services.itsm_engine.pipeline_api')
    @patch('itsm.services.itsm_engine.BambooDjangoRuntime')
    def test_run_success(self, mock_runtime_cls, mock_pipeline_api):
        """run() 成功创建并启动 pipeline"""
        mock_runtime = MagicMock()
        mock_runtime_cls.return_value = mock_runtime
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.run_pipeline.return_value = mock_result

        ticket = _create_ticket()
        wv = ticket.workflow_version
        from itsm.services.itsm_engine import ITSMEngine

        pipeline_id, tree = ITSMEngine(ticket).run(wv)

        self.assertTrue(pipeline_id)
        mock_pipeline_api.run_pipeline.assert_called_once()
        self.assertEqual(tree.get('id'), pipeline_id)

    @patch('itsm.services.itsm_engine.pipeline_api')
    @patch('itsm.services.itsm_engine.BambooDjangoRuntime')
    def test_run_failure_raises(self, mock_runtime_cls, mock_pipeline_api):
        """run() 失败时抛出 RuntimeError"""
        mock_result = MagicMock()
        mock_result.result = False
        mock_result.message = 'test error'
        mock_pipeline_api.run_pipeline.return_value = mock_result

        ticket = _create_ticket()
        wv = ticket.workflow_version
        from itsm.services.itsm_engine import ITSMEngine

        with self.assertRaises(RuntimeError) as ctx:
            ITSMEngine(ticket).run(wv)
        self.assertIn('test error', str(ctx.exception))


class ITSMEnginePauseResumeRevokeTests(TestCase):
    """ITSMEngine.pause/resume/revoke — pipeline 生命周期管理"""

    def setUp(self):
        self.ticket = _create_ticket(pipeline_id='test-pipeline-001')

    @patch('itsm.services.itsm_engine.pipeline_api')
    def test_pause(self, mock_pipeline_api):
        """pause() 暂停 pipeline + 工单状态变为 suspended"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.pause_pipeline.return_value = mock_result

        from itsm.services.itsm_engine import ITSMEngine
        engine = ITSMEngine(self.ticket)
        engine.pause()

        mock_pipeline_api.pause_pipeline.assert_called_once()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.current_status, 'suspended')

    @patch('itsm.services.itsm_engine.pipeline_api')
    def test_resume(self, mock_pipeline_api):
        """resume() 恢复 pipeline + 工单状态变为 running"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.resume_pipeline.return_value = mock_result

        from itsm.services.itsm_engine import ITSMEngine
        engine = ITSMEngine(self.ticket)
        engine.resume()

        mock_pipeline_api.resume_pipeline.assert_called_once()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.current_status, 'running')

    @patch('itsm.services.itsm_engine.pipeline_api')
    def test_revoke(self, mock_pipeline_api):
        """revoke() 撤销 pipeline + 工单状态变为 terminated"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.revoke_pipeline.return_value = mock_result

        from itsm.services.itsm_engine import ITSMEngine
        engine = ITSMEngine(self.ticket)
        engine.revoke()

        mock_pipeline_api.revoke_pipeline.assert_called_once()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.current_status, 'terminated')

    @patch('itsm.services.itsm_engine.Schedule.objects.filter')
    @patch('itsm.services.itsm_engine.pipeline_api')
    @patch('itsm.services.itsm_engine.BambooDjangoRuntime')
    def test_activity_callback(self, mock_runtime_cls, mock_pipeline_api, mock_filter):
        """activity_callback 转发到 bamboo api"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.callback.return_value = mock_result

        # Mock Schedule lookup
        mock_schedule = MagicMock()
        mock_schedule.version = 'vtest123'
        mock_qs = MagicMock()
        mock_qs.first.return_value = mock_schedule
        mock_filter.return_value.order_by.return_value = mock_qs

        from itsm.services.itsm_engine import ITSMEngine
        result = ITSMEngine.activity_callback('node-1', {'key': 'val'})

        self.assertTrue(result)
        mock_pipeline_api.callback.assert_called_once_with(
            mock_runtime_cls.return_value, 'node-1', 'vtest123', {'key': 'val'}
        )

    @patch('itsm.services.itsm_engine.Schedule.objects.filter')
    @patch('itsm.services.itsm_engine.pipeline_api')
    @patch('itsm.services.itsm_engine.BambooDjangoRuntime')
    def test_activity_callback_no_schedule(self, mock_runtime_cls, mock_pipeline_api, mock_filter):
        """activity_callback 没有 Schedule 时返回 False 不报错"""
        mock_qs = MagicMock()
        mock_qs.first.return_value = None
        mock_filter.return_value.order_by.return_value = mock_qs

        from itsm.services.itsm_engine import ITSMEngine
        result = ITSMEngine.activity_callback('node-1', {'key': 'val'})

        self.assertFalse(result)
        mock_pipeline_api.callback.assert_not_called()

    @patch('itsm.services.itsm_engine.pipeline_api')
    @patch('itsm.services.itsm_engine.BambooDjangoRuntime')
    def test_revoke_by_pipeline_id(self, mock_runtime_cls, mock_pipeline_api):
        """revoke_by_pipeline_id 通过 pipeline_id 直接撤销"""
        mock_result = MagicMock()
        mock_result.result = True
        mock_pipeline_api.revoke_pipeline.return_value = mock_result

        from itsm.services.itsm_engine import ITSMEngine
        ITSMEngine.revoke_by_pipeline_id('test-pipeline-001')

        mock_pipeline_api.revoke_pipeline.assert_called_once()
