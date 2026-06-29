"""BasePlugin 基类 — 所有标准插件继承此类"""

from typing import Any, Callable, Dict, List, Optional

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
    name: str = ""               # 显示名称（中文，如 "Shell 执行"）
    name_en: str = ""            # 显示名称（英文，可选，如 "Shell Execute"）
    group: str = ""              # 分组（如 "Ansible", "ESXi"）
    version: str = "v1.0"
    description: str = ""
    description_en: str = ""     # 描述（英文，可选）
    risk_level: str = "low"      # low / medium / high
    icon: str = ""               # 显示图标（emoji 或 Element Plus 图标名）
    color: str = ""              # 主题色 hex（如 "#409EFF"）
    _need_schedule: bool = False # True=异步回调模式（长任务轮询）
    show_execution_controls: bool = True  # 是否显示 Execution Control 区域
    show_loop_config: bool = True         # 是否显示 Loop Config

    @classmethod
    def need_schedule(cls) -> bool:
        """是否需要异步调度（长任务回调/轮询模式）

        如果返回 True，子类必须实现 schedule() 方法。
        bamboo-engine 在 execute() 返回后会定期调用 schedule()，
        直到返回 True（完成）或 False（失败）。
        """
        return cls._need_schedule

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

    def schedule(self, context: dict, **kwargs) -> bool | None:
        """异步回调（适用于 need_schedule=True 的插件）

        当 execute() 返回 True 后，bamboo-engine 会定期调用此方法。
        只需返回 True（完成）、False（失败）或 None（继续等待）。

        Args:
            context: execute() 返回的 data.outputs（含 _result、executor_output 等）
            **kwargs: 原始入参
        """
        raise NotImplementedError("need_schedule=True 的子类必须实现 schedule()")

    @classmethod
    def get_output_schema(cls) -> list:
        """输出格式定义（可选，用于前端展示）"""
        return []

    @classmethod
    def get_var_types(cls) -> Dict[str, str]:
        """返回字段名→变量类型的映射

        类型值:
          - "plain":   静态值，不做 ${key} 替换
          - "splice":  模板字符串，运行时 ${key} 替换（默认行为）
          - "split":   替换后用逗号分割为列表
          - "lazy":    延迟计算，由 lazy_resolver 回调处理

        示例:
            return {"threshold": "plain"}
        """
        return {}
