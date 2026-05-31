"""pytest 全局 fixtures — 所有测试模块共享"""

import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_bamboo_runtime():
    """Mock BambooDjangoRuntime 避免依赖数据库 ERI 表"""
    with patch("opsflow.core.flow_engine.BambooDjangoRuntime") as mock:
        instance = Mock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_pipeline_api():
    """Mock bamboo_engine.api 方法"""
    with patch("opsflow.core.flow_engine.pipeline_api") as mock:
        mock.run_pipeline.return_value = Mock(result=True, message="ok")
        mock.pause_pipeline.return_value = Mock(result=True, message="ok")
        mock.resume_pipeline.return_value = Mock(result=True, message="ok")
        mock.revoke_pipeline.return_value = Mock(result=True, message="ok")
        mock.retry_node.return_value = Mock(result=True, message="ok")
        mock.skip_node.return_value = Mock(result=True, message="ok")
        mock.forced_fail_activity.return_value = Mock(result=True, message="ok")
        yield mock
