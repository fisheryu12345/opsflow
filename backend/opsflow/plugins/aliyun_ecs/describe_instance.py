"""查询 ECS 实例详情"""
from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule
from opsflow.plugins.aliyun_ecs._client import get_ecs_client, resolve_cmdb_region

class AliyunEcsDescribePlugin(BasePlugin):
    name = "查询实例"
    name_en = "Describe Instance"
    code = "aliyun_ecs_describe"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "查询阿里云 ECS 实例的详细信息"
    risk_level = "low"

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
        ]

    def execute(self, instance_id: str, region: str = "", **kwargs) -> dict:
        if not region:
            region = resolve_cmdb_region(instance_id)
        if not region:
            return {"success": False, "data": {}, "error": "无法确定实例地域"}
        try:
            from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
            client = get_ecs_client(region)
            request = DescribeInstancesRequest.DescribeInstancesRequest()
            request.set_InstanceIds(f'["{instance_id}"]')
            resp = client.do_action_with_exception(request)
            import json
            data = json.loads(resp)
            instances = data.get("Instances", {}).get("Instance", [])
            if not instances:
                return {"success": False, "data": {}, "error": f"实例 {instance_id} 未找到"}
            inst = instances[0]
            return {
                "success": True,
                "data": {
                    "instance_id": inst.get("InstanceId"),
                    "instance_name": inst.get("InstanceName", ""),
                    "status": inst.get("Status", ""),
                    "private_ip": (inst.get("VpcAttributes", {}) or {}).get("PrivateIpAddress", {}).get("IpAddress", [""])[0] if inst.get("VpcAttributes") else "",
                    "public_ip": (inst.get("PublicIpAddress", {}) or {}).get("IpAddress", [""])[0] if inst.get("PublicIpAddress") else "",
                    "os_name": inst.get("OSName", ""),
                    "instance_type": inst.get("InstanceType", ""),
                    "region_id": inst.get("RegionId", ""),
                    "creation_time": inst.get("CreationTime", ""),
                },
                "error": "",
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string", "description": "ECS 实例 ID"},
            {"name": "instance_name", "type": "string", "description": "实例名称"},
            {"name": "status", "type": "string", "description": "实例状态"},
            {"name": "private_ip", "type": "string", "description": "私网 IP"},
            {"name": "public_ip", "type": "string", "description": "公网 IP"},
            {"name": "os_name", "type": "string", "description": "操作系统"},
            {"name": "instance_type", "type": "string", "description": "实例规格"},
            {"name": "region_id", "type": "string", "description": "地域 ID"},
            {"name": "creation_time", "type": "string", "description": "创建时间"},
        ]
