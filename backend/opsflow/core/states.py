"""状态枚举与流转矩阵 — 节点生命周期 + Pipeline 级别状态

集中定义所有合法状态及其流转规则，替代散落在各模块中的裸字符串。
"""

from enum import Enum


class NodeState(str, Enum):
    """节点状态枚举 — 每个节点的生命周期状态"""
    PENDING = "pending"            # 等待执行（CREATED / READY）
    RUNNING = "running"            # 执行中
    FINISHED = "completed"          # 成功完成（COMPLETED）
    FAILED = "failed"              # 执行失败
    PAUSED = "paused"              # 人工暂停（SUSPENDED）
    SKIPPED = "skipped"            # 被跳过
    CANCELLED = "cancelled"        # 已取消（REVOKED）
    BLOCKED = "blocked"            # 被阻塞
    PENDING_APPROVAL = "pending_approval"  # 等待审批

    @classmethod
    def bamboo_label(cls) -> dict[str, str]:
        """bamboo-engine 内置状态 → NodeState 映射"""
        from bamboo_engine import states
        return {
            states.READY: cls.PENDING,
            states.RUNNING: cls.RUNNING,
            states.FINISHED: cls.FINISHED,
            states.FAILED: cls.FAILED,
            states.SUSPENDED: cls.PAUSED,
            states.REVOKED: cls.CANCELLED,
            states.BLOCKED: cls.BLOCKED,
        }


class PipelineState(str, Enum):
    """Pipeline 级状态枚举 — FlowExecution.status"""
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── 节点级状态流转矩阵 ──────────────────────────────────────────

VALID_NODE_TRANSITIONS: dict[NodeState, list[NodeState]] = {
    NodeState.PENDING:   [NodeState.RUNNING, NodeState.SKIPPED, NodeState.CANCELLED],
    NodeState.RUNNING:   [NodeState.FINISHED, NodeState.FAILED, NodeState.PAUSED, NodeState.PENDING_APPROVAL],
    NodeState.PAUSED:    [NodeState.RUNNING, NodeState.SKIPPED],
    NodeState.PENDING_APPROVAL: [NodeState.FINISHED, NodeState.FAILED],  # 审批通过/拒绝
    NodeState.FAILED:    [NodeState.RUNNING],       # 重试
    NodeState.FINISHED:  [],                        # 终态
    NodeState.SKIPPED:   [],                        # 终态
    NodeState.CANCELLED: [],                        # 终态
    NodeState.BLOCKED:   [NodeState.RUNNING],
}


# ── Pipeline 级状态流转矩阵 ──────────────────────────────────────

VALID_PIPELINE_TRANSITIONS: dict[PipelineState, list[PipelineState]] = {
    PipelineState.PENDING:    [PipelineState.RUNNING, PipelineState.CANCELLED, PipelineState.PENDING_APPROVAL],
    PipelineState.PENDING_APPROVAL: [PipelineState.RUNNING, PipelineState.CANCELLED],
    PipelineState.RUNNING:    [PipelineState.COMPLETED, PipelineState.FAILED, PipelineState.PAUSED, PipelineState.CANCELLED],
    PipelineState.PAUSED:     [PipelineState.RUNNING, PipelineState.CANCELLED],
    PipelineState.FAILED:     [PipelineState.RUNNING],          # 重试整个 pipeline
    PipelineState.COMPLETED:  [],
    PipelineState.CANCELLED:  [],
}


# ── 校验函数 ───────────────────────────────────────────────────

def validate_node_transition(current: NodeState, target: NodeState) -> bool:
    """检查节点状态转移是否合法，返回 True/False"""
    allowed = VALID_NODE_TRANSITIONS.get(current, [])
    return target in allowed


def validate_pipeline_transition(current: PipelineState, target: PipelineState) -> bool:
    """检查 Pipeline 级状态转移是否合法"""
    allowed = VALID_PIPELINE_TRANSITIONS.get(current, [])
    return target in allowed


def map_bamboo_node_state(bamboo_to_state) -> NodeState | None:
    """bamboo-engine 状态 → NodeState"""
    return NodeState.bamboo_label().get(bamboo_to_state)


def map_pipeline_state(bamboo_to_state) -> PipelineState | None:
    """bamboo-engine 状态 → PipelineState（用于根 pipeline 状态变更）

    NodeState 与 PipelineState 的枚举值不同（如 "finished" vs "completed"），
    此函数绕过 NodeState 直接映射到 PipelineState，避免 ValueError。
    """
    from bamboo_engine import states
    mapping = {
        states.FINISHED: PipelineState.COMPLETED,
        states.FAILED: PipelineState.FAILED,
        states.REVOKED: PipelineState.CANCELLED,
        states.SUSPENDED: PipelineState.PAUSED,
        states.RUNNING: PipelineState.RUNNING,
    }
    return mapping.get(bamboo_to_state)
