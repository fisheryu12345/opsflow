# backend/opsagent/core/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class RiskLevel(str, Enum):
    READ = "READ"
    LOW_WRITE = "LOW_WRITE"
    MEDIUM_WRITE = "MEDIUM_WRITE"
    HIGH_WRITE = "HIGH_WRITE"
    CRITICAL = "CRITICAL"


class RiskEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"


class RiskBlastRadius(str, Enum):
    SINGLE = "single"
    GROUP = "group"
    CLUSTER_WIDE = "cluster-wide"


class SafetyDecision(str, Enum):
    AUTO = "AUTO"
    AUTO_ECHO = "AUTO_ECHO"
    ASK = "ASK"
    ASK_BLAST = "ASK_BLAST"
    DENY = "DENY"


@dataclass
class RiskAssessment:
    operation: RiskLevel
    environment: RiskEnv
    blast_radius: RiskBlastRadius
    score: float
    decision: SafetyDecision
    reason: str = ""


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    session_id: str
    operator: str
    environment_name: str | None = None
    env_type: RiskEnv = RiskEnv.DEVELOPMENT
    constraints_md: str = ""
    topology_json: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[..., Awaitable[ToolResult]]
