"""Shell 执行 — 在目标主机上执行 Shell 命令"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class ShellPlugin(BasePlugin):
    name = "Shell 执行"
    code = "shell"
    group = "Ansible"
    description = "在目标主机上执行 Shell 命令"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="command",
                type="code_editor",
                name="执行命令",
                attrs={"language": "shell", "height": "200px", "placeholder": "#!/bin/bash\n"},
                validation=[ValidationRule(type="required", error_message="请输入命令")],
            ),
            FormItem(
                tag_code="timeout",
                type="int",
                name="超时时间(秒)",
                default=60,
                attrs={"min": 5, "max": 600},
            ),
            FormItem(
                tag_code="ignore_error",
                type="checkbox",
                name="忽略错误",
                default=False,
                attrs={"options": [{"label": "命令失败时继续执行", "value": True}]},
            ),
        ]

    def execute(self, command: str, timeout: int = 60, ignore_error: bool = False, **kwargs) -> dict:
        # 生产环境应使用 Celery task 异步执行或 Ansible runner
        import subprocess
        import shlex
        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True, text=True, timeout=timeout,
            )
            return {
                "success": result.returncode == 0 or ignore_error,
                "data": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                "error": result.stderr if result.returncode != 0 else "",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "data": {}, "error": f"执行超时 ({timeout}s)"}
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}
