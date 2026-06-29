"""创建自定义镜像"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsCreateImagePlugin(BasePlugin):
    name = "创建镜像"
    name_en = "Create Image"
    code = "aliyun_ecs_create_image"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "基于一台 ECS 实例创建自定义镜像"
    description_en = "Create a custom image from an ECS instance"
    risk_level = "medium"
    icon = "Picture"
    color = "#409EFF"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="instance_id",
                type="input",
                name="源实例 ID",
                name_en="Source Instance ID",
                attrs={"placeholder": "i-xxxxxxxxxxxxx", "placeholder_en": "i-xxxxxxxxxxxxx"},
                validation=[ValidationRule(type="required", error_message="请输入源实例 ID")],
                col=12,
            ),
            FormItem(
                tag_code="image_name",
                type="input",
                name="镜像名称",
                name_en="Image Name",
                attrs={"placeholder": "my-image-20260614", "placeholder_en": "my-image-20260614"},
                validation=[ValidationRule(type="required", error_message="请输入镜像名称")],
                col=12,
            ),
            FormItem(
                tag_code="description",
                type="textarea",
                name="描述",
                name_en="Description",
                attrs={"placeholder": "可选镜像描述", "placeholder_en": "Optional image description"},
                col=12,
            ),
            FormItem(
                tag_code="region",
                type="async_select",
                name="地域",
                name_en="Region",
                attrs={
                    "api_endpoint": "/api/opsflow/plugins/aliyun/describe-regions/",
                    "placeholder": "选择地域...",
                    "placeholder_en": "Select region...",
                },
                validation=[ValidationRule(type="required", error_message="请选择地域")],
                col=6,
            ),
        ]

    def execute(self, instance_id: str, image_name: str,
                description: str = "", region: str = "", **kwargs) -> dict:
        if not region:
            return {"success": False, "data": {}, "error": "region 不能为空"}
        try:
            from aliyunsdkecs.request.v20140526 import CreateImageRequest
            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)
            request = CreateImageRequest.CreateImageRequest()
            request.set_InstanceId(instance_id)
            request.set_ImageName(image_name)
            if description:
                request.set_Description(description)
            resp = client.do_action_with_exception(request)
            import json
            data = json.loads(resp)
            image_id = data.get("ImageId", "")
            return {
                "success": True,
                "data": {
                    "image_id": image_id,
                    "image_name": image_name,
                    "source_instance_id": instance_id,
                },
                "error": "",
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "image_id", "type": "string", "description": "创建的镜像 ID"},
            {"name": "image_name", "type": "string", "description": "镜像名称"},
            {"name": "source_instance_id", "type": "string", "description": "源实例 ID"},
        ]
