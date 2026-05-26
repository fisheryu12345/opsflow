# backend/opsagent/core/audit.py
import hashlib
import json
import datetime
from opsagent.core.types import RiskAssessment, ToolResult


class AuditLogger:
    """Writes audit records. Uses Django ORM when available, falls back to in-memory list."""

    def __init__(self):
        self._records: list[dict] = []

    def log(
        self,
        session_id: int | None,
        seq: int,
        tool_name: str,
        parameters: dict,
        assessment: RiskAssessment,
        result: ToolResult,
        target: str = "",
        llm_reasoning: str = "",
    ) -> dict:
        record = {
            "session_id": session_id,
            "seq": seq,
            "timestamp": datetime.datetime.now().isoformat(),
            "target": target,
            "tool_name": tool_name,
            "parameters_json": parameters,
            "risk_operation": assessment.operation.value,
            "risk_environment": assessment.environment.value,
            "risk_blast_radius": assessment.blast_radius.value,
            "risk_score": assessment.score,
            "safety_decision": assessment.decision.value,
            "approved_by": "",
            "approval_time_ms": None,
            "execution_started": datetime.datetime.now().isoformat(),
            "execution_completed": datetime.datetime.now().isoformat(),
            "execution_duration_ms": 0,
            "execution_success": result.success,
            "result_summary": result.output[:500] if result.output else "",
            "llm_reasoning": llm_reasoning[:1000],
        }
        record["content_hash"] = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode()
        ).hexdigest()
        self._records.append(record)
        self._persist_if_possible(record)
        return record

    def _persist_if_possible(self, record: dict) -> None:
        try:
            from opsagent.models import AuditRecord, Session as SessionModel
            session = SessionModel.objects.filter(session_id=record["session_id"]).first()
            if session is None:
                return
            AuditRecord.objects.create(
                session=session,
                seq=record["seq"],
                target=record["target"],
                tool_name=record["tool_name"],
                parameters_json=record["parameters_json"],
                risk_operation=record["risk_operation"],
                risk_environment=record["risk_environment"],
                risk_blast_radius=record["risk_blast_radius"],
                risk_score=record["risk_score"],
                safety_decision=record["safety_decision"],
                approved_by=record["approved_by"],
                approval_time_ms=record["approval_time_ms"],
                execution_started=record["execution_started"],
                execution_completed=record["execution_completed"],
                execution_duration_ms=record["execution_duration_ms"],
                execution_success=record["execution_success"],
                result_summary=record["result_summary"],
                llm_reasoning=record["llm_reasoning"],
                content_hash=record["content_hash"],
            )
        except Exception:
            pass  # Django not available or not configured — record stays in memory

    def query(self, tool_name: str | None = None, min_score: float | None = None) -> list[dict]:
        results = self._records
        if tool_name:
            results = [r for r in results if r["tool_name"] == tool_name]
        if min_score is not None:
            results = [r for r in results if r["risk_score"] >= min_score]
        return results

    def clear(self):
        self._records.clear()
