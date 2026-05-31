"""BasePlugin 基类 — 所有标准插件继承此类"""

from typing import Any, Dict, List

from opsflow.schema.form_schema import FormConfig


class BasePlugin:
    """标准插件基类 — 每个运维原子（技能）继承此类

    子类必须实现:
      - code, name, group (类属性)
      - get_form_config()
      - execute(**kwargs)
    """

    # === 元信息（子类覆盖） ===
    code: str = ""               # 插件唯一标识（如 "shell"）
    name: str = ""               # 显示名称（如 "Shell 执行"）
    group: str = ""              # 分组（如 "Ansible", "ESXi"）
    version: str = "v1.0"
    description: str = ""
    risk_level: str = "low"      # low / medium / high

    @classmethod
    def get_form_config(cls) -> FormConfig:
        """返回该插件的表单配置（前端 RenderForm 渲染用）"""
        raise NotImplementedError

    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行插件逻辑

        Args:
            **kwargs: 由 form_config 定义的入参，前端表单收集后传入

        Returns:
            dict: 包含 success(bool), data(dict), error(str) 等
                  example: {"success": True, "data": {"stdout": "..."}}
        """
        raise NotImplementedError

    def rollback(self, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """回滚操作（可选覆盖）

        Args:
            context: 原始 execute() 返回的 data
            **kwargs: 原始入参
        """
        return {"success": True, "data": {}}

    @classmethod
    def get_output_schema(cls) -> list:
        """输出格式定义（可选，用于前端展示）"""
        return []
