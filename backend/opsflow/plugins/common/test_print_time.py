"""测试打印时间 — 后台打印当前时间，用于流程引擎功能验证

添加了 1-5 秒随机等待以模拟真实执行耗时。
"""

import random
import time
from datetime import datetime

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class TestPrintTimePlugin(BasePlugin):
    name = "测试打印时间"
    code = "test_print_time"
    group = "通用工具"
    description = "测试原子 — 后台打印当前时间，用于流程引擎功能验证（随机等待 1-5s）"
    risk_level = "low"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="message",
                type="input",
                name="附加消息",
                attrs={"placeholder": "可选附加消息"},
                default="hello",
            ),
            FormItem(
                tag_code="fail",
                type="checkbox",
                name="模拟失败",
                default=False,
                attrs={"options": [{"label": "模拟执行失败（测试条件分支）", "value": True}]},
            ),
        ]

    def execute(self, message: str = "hello", fail: bool = False, **kwargs) -> dict:
        # 模拟真实执行耗时，随机等待 1-5 秒
        sleep_time = random.uniform(1, 5)
        time.sleep(sleep_time)

        now = datetime.now()
        timestamp = now.isoformat()
        test1 = random.randint(1, 10)

        if fail:
            return {
                "success": False,
                "data": {"timestamp": timestamp, "message": message, "sleep_seconds": round(sleep_time, 2), "test1": test1},
                "error": "模拟失败（测试条件分支）",
            }

        return {
            "success": True,
            "data": {
                "timestamp": timestamp,
                "message": message,
                "sleep_seconds": round(sleep_time, 2),
                "test1": test1,
            },
        }

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "test1", "type": "integer", "description": "随机数值 1-10"},
        ]
