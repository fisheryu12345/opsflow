"""重启 ECS 实例"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule
from opsflow.plugins.aliyun_ecs._client import get_ecs_client, resolve_cmdb_region

class AliyunEcsRebootPlugin(BasePlugin):
    name = "重启实例"
    name_en = "Reboot Instance"
    code = "aliyun_ecs_restart"
    group = "阿里云 ECS"
    group_en = "Aliyun ECS"
    version = "v1.0"
    description = "重启一台运行中的阿里云 ECS 实例"
    description_en = "Restart an Alibaba Cloud ECS instance"
    risk_level = "medium"
    icon = "Refresh"
    color = "#E6A23C"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="async_select",
                name="实例",
                name_en="Instance",
                attrs={"api_endpoint": "/api/opsflow/plugins/aliyun/describe-cmdb-instances/", "placeholder": "从 CMDB 选择实例...", "placeholder_en": "Select instance from CMDB..."},
                validation=[ValidationRule(type="required", error_message="请选择实例")],
                col=12,
            ),
            FormItem(
                tag_code="force_reboot",
                type="switch",
                name="强制重启",
                name_en="Force Reboot",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否", "active_text_en": "Yes", "inactive_text_en": "No"},
                col=6,
            ),
        ]

    def execute(self, instance_id: str, region: str = "", force_reboot: bool = False, **kwargs) -> dict:
        if not region:
            region = resolve_cmdb_region(instance_id)
        if not region:
            return {"success": False, "data": {}, "error": "无法确定实例地域"}
        try:
            from aliyunsdkecs.request.v20140526 import RebootInstanceRequest
            client = get_ecs_client(region)
            request = RebootInstanceRequest.RebootInstanceRequest()
            request.set_InstanceId(instance_id)
            request.set_ForceReboot(bool(force_reboot))
            client.do_action_with_exception(request)
            return {"success": True, "data": {"instance_id": instance_id, "status": "Rebooting"}, "error": ""}
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [{"name": "instance_id", "type": "string", "description": "ECS 实例 ID", "description_en": "ECS instance ID"}, {"name": "status", "type": "string", "description": "实例状态", "description_en": "Instance status"}]
