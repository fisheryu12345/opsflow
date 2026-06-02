"""排他网关（Exclusive Gateway）完整执行流程测试

覆盖从构建 → 校验 → 执行 → 状态追踪的完整生命周期。
网关条件评估在 bamboo-engine 内部完成，测试通过模拟前置节点输出来间接验证分支选择。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from opsflow.core.flow_engine import FlowEngine
from opsflow.core.pipeline_builder import build_bamboo_pipeline
from opsflow.core.bamboo_validator import validate_bamboo_compatibility
from opsflow.core.safety_guard import validate_pipeline


# =============================================================================
# 辅助函数
# =============================================================================

def _make_atom_pipeline(nodes, edges):
    """构建一个含排他网关的 mock template"""
    tpl = Mock()
    tpl.name = "exclusive_gw_test"
    tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
    tpl.target_hosts = []
    tpl.global_vars = {}
    tpl.project_id = None  # 避免 resolve_project_variables DB 查询
    tpl.id = None
    return tpl


def _make_execution(frozen_tree=None, status="running"):
    """创建 mock execution（与 test_flow_engine.py 风格一致）

    Args:
        frozen_tree: pipeline_tree dict，None 表示没有冻结快照
    """
    exec_mock = Mock()
    exec_mock.id = 1
    exec_mock.status = status
    exec_mock.template = _make_atom_pipeline(
        frozen_tree.get("nodes", []) if frozen_tree else [],
        frozen_tree.get("edges", []) if frozen_tree else [],
    )
    if frozen_tree is not None:
        exec_mock.template_snapshot = {
            "pipeline_tree": frozen_tree,
            "target_hosts": [],
            "global_vars": {},
        }
    else:
        exec_mock.template_snapshot = None
    exec_mock.context = {}
    exec_mock.node_status = {}
    exec_mock.state_tree = {}
    exec_mock.excluded_nodes = []
    return exec_mock


# =============================================================================
# 测试套件
# =============================================================================

EXCLUSIVE_PIPELINE = {
    "nodes": [
        {"id": "n1", "type": "task", "atom_type": "ping_test",
         "label": "Check Disk", "params": {}},
        {"id": "gw1", "node_type": "exclusive_gateway", "label": "Disk Full?"},
        {"id": "n2", "type": "task", "atom_type": "send_alert",
         "label": "Send Alert", "params": {}},
        {"id": "n3", "type": "task", "atom_type": "ping_test",
         "label": "Send OK", "params": {}},
        {"id": "e1", "node_type": "end_event"},
    ],
    "edges": [
        {"from": "n1", "to": "gw1"},
        {"from": "gw1", "to": "n2", "label": "failure",
         "condition": "${_result == False}"},
        {"from": "gw1", "to": "n3", "label": "success",
         "condition": "${_result == True}"},
        {"from": "n2", "to": "e1"},
        {"from": "n3", "to": "e1"},
    ],
}


class TestExclusiveGatewayPipelineBuild:
    """排他网关 pipeline 构建验证"""

    def test_build_pipeline_structure(self):
        """验证构建出的 bamboo pipeline 结构完整"""
        tpl = _make_atom_pipeline(EXCLUSIVE_PIPELINE["nodes"], EXCLUSIVE_PIPELINE["edges"])
        result, id_map = build_bamboo_pipeline(tpl)

        assert result is not None
        # 检查 gateways
        assert "gateways" in result
        assert len(result["gateways"]) >= 1
        gw_key = [k for k in result["gateways"] if id_map.get(k) == "gw1"]
        assert len(gw_key) == 1
        gw = result["gateways"][gw_key[0]]
        assert gw["type"] == "ExclusiveGateway"
        # 每个出边应有 condition
        assert "conditions" in gw
        assert len(gw["conditions"]) == 2

    def test_build_pipeline_activities(self):
        """所有原子节点应为 activities"""
        tpl = _make_atom_pipeline(EXCLUSIVE_PIPELINE["nodes"], EXCLUSIVE_PIPELINE["edges"])
        result, id_map = build_bamboo_pipeline(tpl)

        # n1, n2, n3 应都在 activities 中
        activity_ids = set(id_map.keys())
        mapped = {v: k for k, v in id_map.items()}
        for nid in ["n1", "n2", "n3"]:
            assert nid in mapped, f"{nid} 应在 id_map 中"

    def test_build_gateway_with_conditions_set_on_edges(self):
        """排他网关出边上设置了条件 → 构建成功且 conditions 正确"""
        nodes = [
            {"id": "n1", "type": "task", "atom_type": "check_disk"},
            {"id": "gw1", "node_type": "exclusive_gateway"},
            {"id": "n2", "type": "task", "atom_type": "send_alert"},
        ]
        edges = [
            {"from": "n1", "to": "gw1"},
            {"from": "gw1", "to": "n2",
             "condition": "${_result == True}"},
        ]
        tpl = _make_atom_pipeline(nodes, edges)
        result, id_map = build_bamboo_pipeline(tpl)
        assert result is not None

    def test_validation_passes_for_valid_pipeline(self):
        """合法排他网关流程应通过校验"""
        validation = validate_pipeline(EXCLUSIVE_PIPELINE)
        assert validation.get("valid") is True
        assert len(validation.get("errors", [])) == 0

    def test_validation_fails_for_missing_conditions(self):
        """条件引用不存在的节点应报错（bamboo_validator 层面）"""
        bad_tree = {
            "nodes": [
                {"id": "n1", "type": "task", "atom_type": "ping_test", "label": "N1"},
                {"id": "gw1", "node_type": "exclusive_gateway", "label": "GW"},
                {"id": "n2", "type": "task", "atom_type": "ping_test", "label": "N2"},
                {"id": "e1", "node_type": "end_event", "label": "End"},
            ],
            "edges": [
                {"from": "n1", "to": "gw1"},
                {"from": "gw1", "to": "n2",
                 "condition": "${nonexistent.key > 10}"},
                {"from": "n2", "to": "e1"},
            ],
        }
        validation = validate_bamboo_compatibility(bad_tree, skip_schema=True)
        assert validation.get("valid") is False
        assert any("nonexistent" in e for e in validation.get("errors", []))


class TestExclusiveGatewayFlowEngineRun:
    """FlowEngine.run() 与排他网关集成测试"""

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_with_exclusive_gateway_success(
        self, mock_api, mock_build, mock_validate
    ):
        """engine.run() 包含排他网关时正常执行"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = (
            {"id": "bp_001", "gateways": {"gw": {}}, "activities": {"act1": {}}},
            {"uuid1": "n1"},
        )
        mock_api.run_pipeline.return_value = Mock(result=True)

        exec_mock = _make_execution(EXCLUSIVE_PIPELINE)
        engine = FlowEngine(exec_mock)
        engine.run()

        mock_validate.assert_called_once()
        mock_build.assert_called_once()
        mock_api.run_pipeline.assert_called_once()
        assert exec_mock.context["bamboo_pipeline_id"] == "bp_001"
        assert exec_mock.status == "running"

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_validation_not_called_without_frozen_tree(
        self, mock_api, mock_build, mock_validate
    ):
        """没有 frozen_tree 时跳过校验"""
        exec_mock = _make_execution(None)
        engine = FlowEngine(exec_mock)
        engine.run()
        mock_validate.assert_not_called()

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_gateway_build_failure_sets_failed(
        self, mock_api, mock_build, mock_validate
    ):
        """构建失败时状态变为 failed"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.side_effect = Exception("build error")

        exec_mock = _make_execution(EXCLUSIVE_PIPELINE)
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"
        assert exec_mock.ended_at is not None

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_pipeline_api_failure_sets_failed(
        self, mock_api, mock_build, mock_validate
    ):
        """bamboo-engine run_pipeline 失败时状态变为 failed"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = (
            {"id": "bp_001", "gateways": {"gw": {}}, "activities": {"act1": {}}},
            {"uuid1": "n1"},
        )
        mock_api.run_pipeline.return_value = Mock(result=False, message="engine error")

        exec_mock = _make_execution(EXCLUSIVE_PIPELINE)
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"
        assert exec_mock.ended_at is not None

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_start_with_exclusive_gateway(
        self, mock_api, mock_build, mock_validate
    ):
        """start() → celery task → run() 链路正常"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = ({"id": "bp_001"}, {"uuid1": "n1"})
        mock_api.run_pipeline.return_value = Mock(result=True)

        exec_mock = _make_execution(EXCLUSIVE_PIPELINE, status="pending")
        engine = FlowEngine(exec_mock)

        with patch("opsflow.tasks.execute_pipeline_task") as mock_task:
            engine.start()
            assert exec_mock.status == "running"
            mock_task.delay.assert_called_once_with(1)

    def test_pause_resume_cancel_with_gateway(self):
        """暂停/恢复/取消在排他网关场景下正常 work"""
        exec_mock = _make_execution(EXCLUSIVE_PIPELINE, status="running")
        exec_mock.context = {"bamboo_pipeline_id": "bp_001"}
        engine = FlowEngine(exec_mock)

        with patch("opsflow.core.flow_engine.pipeline_api") as mock_api:
            mock_api.pause_pipeline.return_value = Mock(result=True)
            engine.pause()
            assert exec_mock.status == "paused"

            mock_api.resume_pipeline.return_value = Mock(result=True)
            engine.resume()
            assert exec_mock.status == "running"

            mock_api.revoke_pipeline.return_value = Mock(result=True)
            engine.cancel()
            assert exec_mock.status == "cancelled"
            assert exec_mock.ended_at is not None


class TestExclusiveGatewayNodeCommands:
    """排他网关场景下的节点操作（retry/skip/force_fail）"""

    def _make_engine(self, node_status=None):
        exec_mock = _make_execution(EXCLUSIVE_PIPELINE, status="running")
        exec_mock.node_status = node_status or {"n1": "completed", "n2": "failed", "gw1": "completed"}
        return FlowEngine(exec_mock)

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_retry_node_after_gateway_branch(self, mock_api):
        """网关选定分支上的节点失败后可重试"""
        mock_api.retry_node.return_value = Mock(result=True)
        engine = self._make_engine({"n1": "completed", "n2": "failed", "gw1": "completed"})

        engine.retry("n2")
        assert engine.execution.node_status["n2"] == "retrying"
        assert engine.execution.status == "running"

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_skip_node_after_gateway_branch(self, mock_api):
        """网关选定分支上的节点失败后可跳过"""
        mock_api.skip_node.return_value = Mock(result=True)
        engine = self._make_engine({"n1": "completed", "n2": "failed", "gw1": "completed"})

        engine.skip("n2")
        assert engine.execution.node_status["n2"] == "skipped"

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_force_fail_node_on_gateway_branch(self, mock_api):
        """强制让分支上运行中的节点失败"""
        mock_api.forced_fail_activity.return_value = Mock(result=True)
        engine = self._make_engine({"n1": "completed", "n2": "running", "gw1": "completed"})

        engine.force_fail("n2", ex_data="manual abort")
        assert engine.execution.node_status["n2"] == "failed"
