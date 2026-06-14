"""释放 ECS 实例"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsDeletePlugin(BasePlugin):
    name = "释放实例"
    name_en = "Delete Instance"
    code = "aliyun_ecs_delete"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "释放（销毁）一台阿里云 ECS 实例（不可恢复）"
    description_en = "Delete/Release an Alibaba Cloud ECS instance (irreversible)"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="input",
                name="实例 ID",
                name_en="Instance ID",
                attrs={"placeholder": "i-xxxxxxxxxxxxx", "description": "注意：此操作不可恢复"},
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
                tag_code="force",
                type="switch",
                name="强制释放",
                name_en="Force Delete",
                default=False,
                attrs={"active_text": "是", "inactive_text": "否"},
                col=6,
            ),
        ]

    def execute(self, instance_id: str, region: str = "cn-hangzhou",
                force: bool = False, **kwargs) -> dict:
        try:
            from aliyunsdkecs.request.v20140526 import DeleteInstanceRequest

            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)
            request = DeleteInstanceRequest.DeleteInstanceRequest()
            request.set_InstanceId(instance_id)
            request.set_Force(force)
            client.do_action_with_exception(request)
            return {
                "success": True,
                "data": {"instance_id": instance_id, "status": "deleted"},
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
