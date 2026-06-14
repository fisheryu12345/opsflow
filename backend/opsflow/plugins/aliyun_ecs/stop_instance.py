"""停止 ECS 实例"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsStopPlugin(BasePlugin):
    name = "停止实例"
    name_en = "Stop Instance"
    code = "aliyun_ecs_stop"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "停止一台运行中的阿里云 ECS 实例（可选强制停止）"
    description_en = "Stop an Alibaba Cloud ECS instance (force stop optional)"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="input",
                name="实例 ID",
                name_en="Instance ID",
                attrs={"placeholder": "i-xxxxxxxxxxxxx"},
                validation=[ValidationRule(type="required", error_message="请输入实例 ID")],
                col=12,
            ),
            FormItem(
                tag_code="region",
                type="input",
                name="地域",
                name_en="Region",
                default="cn-hangzhou",
                attrs={"placeholder": "如 cn-hangzhou"},
                col=6,
            ),
            FormItem(
                tag_code="force_stop",
                type="switch",
                name="强制停止",
                name_en="Force Stop",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, instance_id: str, region: str = "cn-hangzhou",
                force_stop: bool = False, **kwargs) -> dict:
        try:
            from aliyunsdkecs.request.v20140526 import StopInstanceRequest

            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)
            request = StopInstanceRequest.StopInstanceRequest()
            request.set_InstanceId(instance_id)
            request.set_ForceStop(force_stop)
            client.do_action_with_exception(request)
            return {
                "success": True,
                "data": {"instance_id": instance_id, "status": "Stopping", "force_stop": force_stop},
                "error": "",
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string", "description": "ECS 实例 ID"},
            {"name": "status", "type": "string", "description": "实例状态"},
            {"name": "force_stop", "type": "bool", "description": "是否强制停止"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：启动实例"""
        inst_id = context.get("instance_id", kwargs.get("instance_id", ""))
        if inst_id:
            return {"success": True, "data": {"action": "start_instance", "instance_id": inst_id}}
        return {"success": True, "data": {}}
