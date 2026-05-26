# backend/opsagent/cli/render.py
import sys
from opsagent.core.types import RiskAssessment, SafetyDecision

_COLORS = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def c(text: str, color: str) -> str:
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def tool_call_banner(tool_name: str, args: dict, assessment: RiskAssessment) -> str:
    icon = {
        SafetyDecision.AUTO: c("✓", "green"),
        SafetyDecision.AUTO_ECHO: c("✓", "cyan"),
        SafetyDecision.ASK: c("⚠", "yellow"),
        SafetyDecision.ASK_BLAST: c("⚠", "red"),
        SafetyDecision.DENY: c("✗", "red"),
    }.get(assessment.decision, "?")

    lines = [
        f"  {icon} {c(tool_name, 'bold')}  "
        f"[{assessment.operation.value} × {assessment.environment.value} = {assessment.score:.1f}]  "
        f"{c(assessment.decision.value, 'yellow' if 'ASK' in assessment.decision.value else 'green')}",
    ]
    for k, v in args.items():
        v_str = str(v)
        if len(v_str) > 80:
            v_str = v_str[:77] + "..."
        lines.append(f"    {k}: {c(v_str, 'blue')}")
    return "\n".join(lines)


def tool_result_banner(success: bool, output: str, error: str | None) -> str:
    if success:
        header = c("✓ Success", "green")
    else:
        header = c("✗ Failed", "red")

    lines = [f"  {header}"]
    if output:
        for line in output.split("\n")[:10]:
            lines.append(f"    {line}")
    if error:
        lines.append(f"    {c('Error:', 'red')} {error}")
    return "\n".join(lines)


def approval_prompt(tool_name: str, args: dict, assessment: RiskAssessment) -> str:
    lines = [
        "",
        c(f"╔══ APPROVAL REQUIRED ══╗", "yellow"),
        c(f"║ Tool: {tool_name}", "bold"),
        c(f"║ Risk Score: {assessment.score:.2f} ({assessment.operation.value})", "yellow"),
        c(f"║ Environment: {assessment.environment.value}", "yellow"),
        c(f"║ Blast Radius: {assessment.blast_radius.value}", "yellow"),
    ]
    for k, v in args.items():
        lines.append(c(f"║ {k}: {v}", "blue"))
    lines.append(c(f"╚══════════════════════╝", "yellow"))
    lines.append("Execute? [y/N]: ")
    return "\n".join(lines)
