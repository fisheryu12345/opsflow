"""重启 ECS 实例"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsRebootPlugin(BasePlugin):
    name = "重启实例"
    name_en = "Reboot Instance"
    code = "aliyun_ecs_restart"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "重启一台运行中的阿里云 ECS 实例"
    description_en = "Reboot an Alibaba Cloud ECS instance"
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
                tag_code="force_reboot",
                type="switch",
                name="强制重启",
                name_en="Force Reboot",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, instance_id: str, region: str = "cn-hangzhou",
                force_reboot: bool = False, **kwargs) -> dict:
        try:
            from aliyunsdkecs.request.v20140526 import RebootInstanceRequest

            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)
            request = RebootInstanceRequest.RebootInstanceRequest()
            request.set_InstanceId(instance_id)
            request.set_ForceReboot(force_reboot)
            client.do_action_with_exception(request)
            return {
                "success": True,
                "data": {"instance_id": instance_id, "status": "Rebooting"},
                "error": "",
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string", "description": "ECS 实例 ID"},
            {"name": "status", "type": "string", "description": "实例状态"},
        ]
