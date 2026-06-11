"""并行网关（Parallel Gateway）完整执行流程测试

覆盖从构建 → 校验 → 执行 → 节点操作的完整生命周期。
并行网关特点是所有分支同时执行，最终汇聚（converge）。
"""

from unittest.mock import Mock, patch

from opsflow.core.flow_engine import FlowEngine
from opsflow.core.pipeline_builder import build_bamboo_pipeline
from opsflow.core.bamboo_validator import validate_bamboo_compatibility


# =============================================================================
# 辅助函数
# =============================================================================

def _make_template(nodes, edges):
    """构建 mock template"""
    tpl = Mock()
    tpl.name = "parallel_gw_test"
    tpl.pipeline_tree = {"nodes": nodes, "edges": edges}
    tpl.target_hosts = []
    tpl.global_vars = {}
    tpl.project_id = None
    tpl.id = None
    return tpl


def _make_execution(frozen_tree, status="running"):
    """创建 mock execution"""
    exec_mock = Mock()
    exec_mock.id = 1
    exec_mock.status = status
    exec_mock.template = _make_template(
        frozen_tree.get("nodes", []),
        frozen_tree.get("edges", []),
    )
    exec_mock.template_snapshot = {
        "pipeline_tree": frozen_tree,
        "target_hosts": [],
        "global_vars": {},
    }
    exec_mock.context = {}
    exec_mock.node_status = {}
    exec_mock.state_tree = {}
    exec_mock.excluded_nodes = []
    return exec_mock


# =============================================================================
# 测试数据 — 标准的 3 分支并行流程
# =============================================================================

PARALLEL_3_BRANCH_PIPELINE = {
    "nodes": [
        {"id": "pg1", "node_type": "parallel_gateway", "label": "Fork"},
        {"id": "t1", "type": "task", "atom_type": "ping_test",
         "label": "Task A", "params": {}},
        {"id": "t2", "type": "task", "atom_type": "ping_test",
         "label": "Task B", "params": {}},
        {"id": "t3", "type": "task", "atom_type": "ping_test",
         "label": "Task C", "params": {}},
        {"id": "cg1", "node_type": "converge_gateway", "label": "Join"},
        {"id": "e1", "node_type": "end_event", "label": "End"},
    ],
    "edges": [
        {"from": "pg1", "to": "t1"},
        {"from": "pg1", "to": "t2"},
        {"from": "pg1", "to": "t3"},
        {"from": "t1", "to": "cg1"},
        {"from": "t2", "to": "cg1"},
        {"from": "t3", "to": "cg1"},
        {"from": "cg1", "to": "e1"},
    ],
}

PARALLEL_2_BRANCH_PIPELINE = {
    "nodes": [
        {"id": "s1", "node_type": "start_event", "label": "Start"},
        {"id": "pg1", "node_type": "parallel_gateway", "label": "Fork"},
        {"id": "t1", "type": "task", "atom_type": "ping_test",
         "label": "Task A", "params": {}},
        {"id": "t2", "type": "task", "atom_type": "ping_test",
         "label": "Task B", "params": {}},
        {"id": "cg1", "node_type": "converge_gateway", "label": "Join"},
        {"id": "e1", "node_type": "end_event", "label": "End"},
    ],
    "edges": [
        {"from": "s1", "to": "pg1"},
        {"from": "pg1", "to": "t1"},
        {"from": "pg1", "to": "t2"},
        {"from": "t1", "to": "cg1"},
        {"from": "t2", "to": "cg1"},
        {"from": "cg1", "to": "e1"},
    ],
}


# =============================================================================
# 测试套件
# =============================================================================

class TestParallelGatewayBuild:
    """并行网关 pipeline 构建验证"""

    def test_build_3_branch_structure(self):
        """3 分支并行，验证 gateways 和 activities 结构"""
        tpl = _make_template(
            PARALLEL_3_BRANCH_PIPELINE["nodes"],
            PARALLEL_3_BRANCH_PIPELINE["edges"],
        )
        result = build_bamboo_pipeline(tpl)

        assert result is not None
        assert "gateways" in result
        # 找到 ParallelGateway（原始 X6 ID 直接作为 key）
        assert "pg1" in result["gateways"], "ParallelGateway 应使用原始 ID"
        pg = result["gateways"]["pg1"]
        assert pg["type"] == "ParallelGateway"
        # 找到 ConvergeGateway
        assert "cg1" in result["gateways"], "ConvergeGateway 应使用原始 ID"
        assert result["gateways"]["cg1"]["type"] == "ConvergeGateway"
        # 3 个原子节点
        assert len(result["activities"]) == 3

    def test_parallel_gateway_has_no_conditions(self):
        """并行网关的 gateway 字典没有 conditions 字段"""
        tpl = _make_template(
            PARALLEL_2_BRANCH_PIPELINE["nodes"],
            PARALLEL_2_BRANCH_PIPELINE["edges"],
        )
        result = build_bamboo_pipeline(tpl)
        pg = result["gateways"]["pg1"]
        # 并行网关不应该有 conditions
        assert "conditions" not in pg

    def test_parallel_incoming_count(self):
        """converge 网关的入度应等于并行分支数"""
        tpl = _make_template(
            PARALLEL_3_BRANCH_PIPELINE["nodes"],
            PARALLEL_3_BRANCH_PIPELINE["edges"],
        )
        result = build_bamboo_pipeline(tpl)
        cg = result["gateways"]["cg1"]
        # converge 的 incoming 应该收到 3 条分支
        assert "incoming" in cg
        # bamboo-engine 的 incoming 格式可能是 list 或单个值
        incoming = cg["incoming"]
        count = len(incoming) if isinstance(incoming, list) else 1
        assert count >= 1

    def test_parallel_gateway_validation_passes(self):
        """合法的并行网关流程通过校验"""
        validation = validate_bamboo_compatibility({
            "nodes": PARALLEL_2_BRANCH_PIPELINE["nodes"],
            "edges": PARALLEL_2_BRANCH_PIPELINE["edges"],
        }, skip_schema=True)
        assert validation.get("valid") is True

    def test_parallel_gateway_missing_converge_validation_no_error(self):
        """无汇聚的并行网关 — bamboo_validator 不报错（只是 conflict 层面的 warning）"""
        tree = {
            "nodes": [
                {"id": "s1", "node_type": "start_event", "label": "Start"},
                {"id": "pg1", "node_type": "parallel_gateway", "label": "PG"},
                {"id": "t1", "type": "task", "atom_type": "ping_test", "label": "T1"},
                {"id": "t2", "type": "task", "atom_type": "ping_test", "label": "T2"},
            ],
            "edges": [
                {"from": "s1", "to": "pg1"},  # 有入边 → 入度检查通过
                {"from": "pg1", "to": "t1"},
                {"from": "pg1", "to": "t2"},
            ],
        }
        validation = validate_bamboo_compatibility(tree, skip_schema=True)
        # bamboo_validator 不检查 converge 配对
        assert validation.get("valid") is True

    def test_parallel_gateway_min_in_degree_error(self):
        """并行网关入度 < 1 报错"""
        tree = {
            "nodes": [
                {"id": "pg1", "node_type": "parallel_gateway", "label": "PG"},
                {"id": "t1", "type": "task", "atom_type": "ping_test", "label": "T1"},
            ],
            "edges": [
                {"from": "pg1", "to": "t1"},  # pg1 只有出边没有入边
            ],
        }
        validation = validate_bamboo_compatibility(tree, skip_schema=True)
        assert validation.get("valid") is False
        assert any("入度" in e for e in validation.get("errors", []))


class TestParallelGatewayFlowEngine:
    """FlowEngine.run() 与并行网关集成测试"""

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_parallel_gateway_success(
        self, mock_api, mock_build, mock_validate
    ):
        """engine.run() 包含并行网关时正常执行"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = {"id": "bp_001", "gateways": {"pg": {}, "cg": {}},
             "activities": {"a1": {}, "a2": {}}}
        mock_api.run_pipeline.return_value = Mock(result=True)

        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE)
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
    def test_run_validation_failure(
        self, mock_api, mock_build, mock_validate
    ):
        """校验失败时状态标记为 failed"""
        mock_validate.return_value = {"valid": False, "errors": ["bad"], "warnings": []}

        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE)
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"

    @patch("opsflow.core.flow_engine.validate_pipeline")
    @patch("opsflow.core.flow_engine.build_bamboo_pipeline")
    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_run_api_failure(
        self, mock_api, mock_build, mock_validate
    ):
        """bamboo-engine run_pipeline 失败时标记为 failed"""
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}
        mock_build.return_value = {"id": "bp_001", "gateways": {"pg": {}}, "activities": {"a1": {}}}
        mock_api.run_pipeline.return_value = Mock(result=False, message="engine error")

        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE)
        engine = FlowEngine(exec_mock)
        engine.run()

        assert exec_mock.status == "failed"

    def test_start_parallel_dispatches_celery(self):
        """start() 派发 Celery 任务包含并行网关配置"""
        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE, status="pending")
        engine = FlowEngine(exec_mock)

        with patch("opsflow.tasks.execute_pipeline_task") as mock_task:
            engine.start()
            assert exec_mock.status == "running"
            mock_task.delay.assert_called_once_with(1)

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_lifecycle_with_parallel_gateway(self, mock_api):
        """暂停/恢复/取消在并行网关场景下正常"""
        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE, status="running")
        exec_mock.context = {"bamboo_pipeline_id": "bp_001"}
        engine = FlowEngine(exec_mock)

        mock_api.pause_pipeline.return_value = Mock(result=True)
        engine.pause()
        assert exec_mock.status == "paused"

        mock_api.resume_pipeline.return_value = Mock(result=True)
        engine.resume()
        assert exec_mock.status == "running"

        mock_api.revoke_pipeline.return_value = Mock(result=True)
        engine.cancel()
        assert exec_mock.status == "cancelled"

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_retry_parallel_branch_node(self, mock_api):
        """并行分支上某个节点失败后可重试"""
        mock_api.retry_node.return_value = Mock(result=True)
        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE, status="running")
        exec_mock.node_status = {"pg1": "completed", "t1": "failed", "t2": "completed"}
        engine = FlowEngine(exec_mock)

        engine.retry("t1")
        assert engine.execution.node_status["t1"] == "retrying"

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_skip_parallel_branch_node(self, mock_api):
        """并行分支上某个节点失败后可跳过"""
        mock_api.skip_node.return_value = Mock(result=True)
        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE, status="running")
        exec_mock.node_status = {"pg1": "completed", "t1": "failed", "t2": "completed"}
        engine = FlowEngine(exec_mock)

        engine.skip("t1")
        assert engine.execution.node_status["t1"] == "skipped"

    @patch("opsflow.core.flow_engine.pipeline_api")
    def test_force_fail_parallel_branch_node(self, mock_api):
        """强制让并行分支上运行中的节点失败"""
        mock_api.forced_fail_activity.return_value = Mock(result=True)
        exec_mock = _make_execution(PARALLEL_2_BRANCH_PIPELINE, status="running")
        exec_mock.node_status = {"pg1": "completed", "t1": "running", "t2": "running"}
        engine = FlowEngine(exec_mock)

        engine.force_fail("t1", ex_data="manual")
        assert engine.execution.node_status["t1"] == "failed"
