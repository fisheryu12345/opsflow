# backend/opsagent/core/safety.py
from opsagent.core.types import (
    RiskLevel, RiskEnv, RiskBlastRadius, SafetyDecision, RiskAssessment,
)
from opsagent.tools.base import ToolDef

_OPERATION_WEIGHTS = {
    RiskLevel.READ: 0,
    RiskLevel.LOW_WRITE: 1,
    RiskLevel.MEDIUM_WRITE: 3,
    RiskLevel.HIGH_WRITE: 7,
    RiskLevel.CRITICAL: 10,
}

_ENV_COEFFICIENTS = {
    RiskEnv.DEVELOPMENT: 0.3,
    RiskEnv.STAGING: 0.3,
    RiskEnv.CANARY: 0.6,
    RiskEnv.PRODUCTION: 1.0,
}

_BLAST_COEFFICIENTS = {
    RiskBlastRadius.SINGLE: 0.5,
    RiskBlastRadius.GROUP: 0.8,
    RiskBlastRadius.CLUSTER_WIDE: 1.0,
}


def compute_risk_score(
    operation: RiskLevel,
    environment: RiskEnv,
    blast_radius: RiskBlastRadius = RiskBlastRadius.SINGLE,
) -> float:
    op_w = _OPERATION_WEIGHTS.get(operation, 0)
    env_c = _ENV_COEFFICIENTS.get(environment, 1.0)
    blast_c = _BLAST_COEFFICIENTS.get(blast_radius, 0.5)
    return round(op_w * env_c * blast_c, 2)


def decide(score: float) -> SafetyDecision:
    if score == 0:
        return SafetyDecision.AUTO
    elif score <= 2.0:
        return SafetyDecision.AUTO_ECHO
    elif score <= 5.0:
        return SafetyDecision.ASK
    else:
        return SafetyDecision.ASK_BLAST


def assess(
    tool: ToolDef,
    environment: RiskEnv,
    blast_radius: RiskBlastRadius = RiskBlastRadius.SINGLE,
) -> RiskAssessment:
    score = compute_risk_score(tool.risk_level, environment, blast_radius)
    decision = decide(score)
    return RiskAssessment(
        operation=tool.risk_level,
        environment=environment,
        blast_radius=blast_radius,
        score=score,
        decision=decision,
        reason=f"score={score:.2f}: {tool.risk_level.value} × env({environment.value}) × blast({blast_radius.value})",
    )


def requires_user_approval(assessment: RiskAssessment) -> bool:
    return assessment.decision in (SafetyDecision.ASK, SafetyDecision.ASK_BLAST)
