"""查询 ECS 实例详情"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule


class AliyunEcsDescribePlugin(BasePlugin):
    name = "查询实例"
    name_en = "Describe Instance"
    code = "aliyun_ecs_describe"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "查询阿里云 ECS 实例的详细信息（状态、IP、配置等）"
    description_en = "Describe an Alibaba Cloud ECS instance"
    risk_level = "low"

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
            from aliyunsdkecs.request.v20140526 import DescribeInstancesRequest
            from aliyunsdkcore.client import AcsClient

            client = self._get_client(region)
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

    def _get_client(self, region: str):
        """获取 AcsClient（允许单元测试 mock）"""
        from opsflow.plugins.aliyun_ecs._client import get_ecs_client
        return get_ecs_client(region)

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
