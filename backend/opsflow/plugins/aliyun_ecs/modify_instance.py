"""修改 ECS 实例属性（名称、描述）"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule
from opsflow.plugins.aliyun_ecs._client import get_ecs_client, resolve_cmdb_region

class AliyunEcsModifyPlugin(BasePlugin):
    name = "修改属性"
    name_en = "Modify Instance"
    code = "aliyun_ecs_modify"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "修改阿里云 ECS 实例的名称和描述等属性"
    risk_level = "medium"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="async_select",
                name="实例",
                attrs={"api_endpoint": "/api/opsflow/plugins/aliyun/describe-cmdb-instances/", "placeholder": "从 CMDB 选择实例..."},
                validation=[ValidationRule(type="required", error_message="请选择实例")],
                col=12,
            ),
            FormItem(
                tag_code="instance_name",
                type="input",
                name="新名称",
                attrs={"placeholder": "输入新名称（留空不修改）"},
                col=12,
            ),
            FormItem(
                tag_code="description",
                type="textarea",
                name="新描述",
                attrs={"placeholder": "输入新描述（留空不修改）"},
                col=12,
            ),
        ]

    def execute(self, instance_id: str, instance_name: str = "", description: str = "", region: str = "", **kwargs) -> dict:
        if not region:
            region = resolve_cmdb_region(instance_id)
        if not region:
            return {"success": False, "data": {}, "error": "无法确定实例地域"}
        try:
            from aliyunsdkecs.request.v20140526 import ModifyInstanceAttributeRequest
            client = get_ecs_client(region)
            request = ModifyInstanceAttributeRequest.ModifyInstanceAttributeRequest()
            request.set_InstanceId(instance_id)
            if instance_name:
                request.set_InstanceName(instance_name)
            if description:
                request.set_Description(description)
            client.do_action_with_exception(request)
            return {"success": True, "data": {"instance_id": instance_id, "instance_name": instance_name, "description": description}, "error": ""}
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [{"name": "instance_id", "type": "string", "description": "ECS 实例 ID"}, {"name": "instance_name", "type": "string", "description": "修改后的实例名称"}, {"name": "description", "type": "string", "description": "修改后的描述"}]
