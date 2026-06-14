"""启动 ECS 实例"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsStartPlugin(BasePlugin):
    name = "启动实例"
    name_en = "Start Instance"
    code = "aliyun_ecs_start"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "启动一台已停止的阿里云 ECS 实例"
    description_en = "Start an Alibaba Cloud ECS instance"
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
        ]

    def execute(self, instance_id: str, region: str = "cn-hangzhou", **kwargs) -> dict:
        try:
            from aliyunsdkecs.request.v20140526 import StartInstanceRequest

            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)
            request = StartInstanceRequest.StartInstanceRequest()
            request.set_InstanceId(instance_id)
            client.do_action_with_exception(request)
            return {"success": True, "data": {"instance_id": instance_id, "status": "Starting"}, "error": ""}
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string", "description": "ECS 实例 ID"},
            {"name": "status", "type": "string", "description": "实例状态"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：停止实例"""
        inst_id = context.get("instance_id", kwargs.get("instance_id", ""))
        if inst_id:
            return {"success": True, "data": {"action": "stop_instance", "instance_id": inst_id}}
        return {"success": True, "data": {}}
