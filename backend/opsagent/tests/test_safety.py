# backend/opsagent/tests/test_safety.py
from opsagent.core.safety import compute_risk_score, decide, assess, requires_user_approval
from opsagent.core.types import RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision
from opsagent.tools.base import ToolDef


def _make_tool(risk: RiskLevel) -> ToolDef:
    async def _noop(**kwargs):
        from opsagent.core.types import ToolResult
        return ToolResult(success=True, output="ok")
    return ToolDef(name="test", description="t", parameters={}, risk_level=risk, handler=_noop)


def test_read_is_zero():
    assert compute_risk_score(RiskLevel.READ, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE) == 0


def test_low_write_staging_single():
    score = compute_risk_score(RiskLevel.LOW_WRITE, RiskEnv.STAGING, RiskBlastRadius.SINGLE)
    assert score == 0.15  # 1 × 0.3 × 0.5


def test_high_write_prod_cluster():
    score = compute_risk_score(RiskLevel.HIGH_WRITE, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert score == 7.0  # 7 × 1.0 × 1.0


def test_critical_prod_cluster():
    score = compute_risk_score(RiskLevel.CRITICAL, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert score == 10.0


def test_decide_auto():
    assert decide(0) == SafetyDecision.AUTO


def test_decide_auto_echo():
    assert decide(0.15) == SafetyDecision.AUTO_ECHO
    assert decide(2.0) == SafetyDecision.AUTO_ECHO


def test_decide_ask():
    assert decide(2.1) == SafetyDecision.ASK
    assert decide(5.0) == SafetyDecision.ASK


def test_decide_ask_blast():
    assert decide(5.1) == SafetyDecision.ASK_BLAST
    assert decide(10.0) == SafetyDecision.ASK_BLAST


def test_assess_read_tool_auto():
    tool = _make_tool(RiskLevel.READ)
    a = assess(tool, RiskEnv.PRODUCTION, RiskBlastRadius.CLUSTER_WIDE)
    assert a.decision == SafetyDecision.AUTO
    assert not requires_user_approval(a)


def test_assess_high_write_prod_requires_approval():
    tool = _make_tool(RiskLevel.HIGH_WRITE)
    a = assess(tool, RiskEnv.PRODUCTION, RiskBlastRadius.SINGLE)
    assert requires_user_approval(a)
