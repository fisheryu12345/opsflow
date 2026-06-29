"""手动暂停原子 — Pipeline 执行到此处时暂停，等待用户手动恢复"""
from opsflow.plugins.base import BasePlugin


class ManualPausePlugin(BasePlugin):
    name = "暂停"
    name_en = "Pause"
    code = "manual_pause"
    group = "Common Tools"
    description = "暂停流程执行，等待用户手动恢复"
    description_en = "Pause pipeline execution and wait for manual resume"
    risk_level = "low"
    icon = "VideoPause"
    color = "#909399"

    show_execution_controls = False
    show_loop_config = False

    def execute(self, **kwargs):
        """立即返回成功，暂停由信号处理器触发"""
        return {"success": True, "data": {"paused": True}}

    @classmethod
    def get_form_config(cls):
        return []  # 无参数，零配置
