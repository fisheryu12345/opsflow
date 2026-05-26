# backend/opsagent/tests/test_audit.py
from opsagent.core.audit import AuditLogger
from opsagent.core.types import (
    RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision, RiskAssessment, ToolResult,
)


def test_audit_log_in_memory():
    logger = AuditLogger()
    logger.clear()

    assessment = RiskAssessment(
        operation=RiskLevel.READ,
        environment=RiskEnv.STAGING,
        blast_radius=RiskBlastRadius.SINGLE,
        score=0.0,
        decision=SafetyDecision.AUTO,
    )
    result = ToolResult(success=True, output="kubectl get pods output")

    record = logger.log(
        session_id=None, seq=1, tool_name="k8s_get",
        parameters={"resource": "pods"}, assessment=assessment, result=result,
    )

    assert record["tool_name"] == "k8s_get"
    assert record["risk_score"] == 0.0
    assert record["safety_decision"] == "AUTO"
    assert len(record["content_hash"]) == 64


def test_audit_query_filter():
    logger = AuditLogger()
    logger.clear()

    a1 = RiskAssessment(RiskLevel.READ, RiskEnv.STAGING, RiskBlastRadius.SINGLE, 0.0, SafetyDecision.AUTO)
    a2 = RiskAssessment(RiskLevel.HIGH_WRITE, RiskEnv.PRODUCTION, RiskBlastRadius.SINGLE, 7.0, SafetyDecision.ASK_BLAST)
    r = ToolResult(success=True, output="ok")

    logger.log(None, 1, "k8s_get", {}, a1, r)
    logger.log(None, 2, "k8s_restart", {}, a2, r)

    assert len(logger.query(tool_name="k8s_restart")) == 1
    assert len(logger.query(min_score=5.0)) == 1
    assert len(logger.query(tool_name="k8s_get", min_score=1.0)) == 0
