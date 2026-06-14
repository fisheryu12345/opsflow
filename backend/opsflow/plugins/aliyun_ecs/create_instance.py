"""创建 ECS 实例（含可选公网 IP 分配）"""

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, FormGroup, ValidationRule


class AliyunEcsCreatePlugin(BasePlugin):
    name = "创建实例"
    name_en = "Create Instance"
    code = "aliyun_ecs_create"
    group = "阿里云 ECS"
    version = "v1.0"
    description = "创建一台阿里云 ECS 实例（可选分配公网 IP）"
    description_en = "Create an Alibaba Cloud ECS instance with optional public IP"
    risk_level = "high"

    @classmethod
    def get_form_config(cls):
        return [
            FormGroup(
                name="基础配置",
                tag_code="basic",
                items=[
                    FormItem(
                        tag_code="instance_name",
                        type="input",
                        name="实例名称",
                        name_en="Instance Name",
                        attrs={"placeholder": "my-ecs-instance"},
                        validation=[ValidationRule(type="required", error_message="请输入实例名称")],
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
                        tag_code="zone_id",
                        type="input",
                        name="可用区",
                        name_en="Zone ID",
                        default="",
                        attrs={"placeholder": "如 cn-hangzhou-g（可选）"},
                        col=6,
                    ),
                    FormItem(
                        tag_code="image_id",
                        type="input",
                        name="镜像 ID",
                        name_en="Image ID",
                        attrs={"placeholder": "aliyun_2_1903_x64_20G_alibase_2023...",
                               "description": "可从「查询镜像」原子获取"},
                        validation=[ValidationRule(type="required", error_message="请输入镜像 ID")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="instance_type",
                        type="input",
                        name="实例规格",
                        name_en="Instance Type",
                        attrs={"placeholder": "ecs.g6.large"},
                        validation=[ValidationRule(type="required", error_message="请输入实例规格")],
                        col=6,
                    ),
                ],
            ),
            FormGroup(
                name="网络配置",
                tag_code="network",
                items=[
                    FormItem(
                        tag_code="security_group_id",
                        type="input",
                        name="安全组 ID",
                        name_en="Security Group ID",
                        attrs={"placeholder": "sg-xxxxxxxxxxxxx"},
                        validation=[ValidationRule(type="required", error_message="请输入安全组 ID")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="vswitch_id",
                        type="input",
                        name="VSwitch ID",
                        name_en="VSwitch ID",
                        attrs={"placeholder": "vsw-xxxxxxxxxxxxx"},
                        validation=[ValidationRule(type="required", error_message="请输入 VSwitch ID")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="internet_max_bandwidth_out",
                        type="int",
                        name="公网带宽 (Mbps)",
                        name_en="Max Bandwidth Out",
                        default=0,
                        attrs={"min": 0, "max": 200, "placeholder": "0=不分配公网"},
                        col=6,
                    ),
                    FormItem(
                        tag_code="allocate_public_ip",
                        type="switch",
                        name="分配公网 IP",
                        name_en="Allocate Public IP",
                        default=True,
                        attrs={"active_text": "是", "inactive_text": "否"},
                        col=6,
                    ),
                ],
            ),
            FormGroup(
                name="存储配置",
                tag_code="storage",
                items=[
                    FormItem(
                        tag_code="system_disk_size",
                        type="int",
                        name="系统盘大小 (GB)",
                        name_en="System Disk Size",
                        default=40,
                        attrs={"min": 20, "max": 500},
                        col=6,
                    ),
                    FormItem(
                        tag_code="system_disk_category",
                        type="select",
                        name="系统盘类型",
                        name_en="Disk Category",
                        default="cloud_ssd",
                        attrs={
                            "options": [
                                {"label": "cloud_ssd - SSD 云盘", "value": "cloud_ssd"},
                                {"label": "cloud_efficiency - 高效云盘", "value": "cloud_efficiency"},
                                {"label": "cloud_essd - ESSD", "value": "cloud_essd"},
                                {"label": "cloud - 普通云盘", "value": "cloud"},
                            ],
                        },
                        col=6,
                    ),
                ],
            ),
        ]

    def execute(self, instance_name: str, region: str = "cn-hangzhou",
                zone_id: str = "", image_id: str = "", instance_type: str = "",
                security_group_id: str = "", vswitch_id: str = "",
                internet_max_bandwidth_out: int = 0,
                allocate_public_ip: bool = True,
                system_disk_size: int = 40,
                system_disk_category: str = "cloud_ssd",
                **kwargs) -> dict:
        try:
            from aliyunsdkecs.request.v20140526 import (
                CreateInstanceRequest,
                AllocatePublicIpAddressRequest,
            )

            from opsflow.plugins.aliyun_ecs._client import get_ecs_client
            client = get_ecs_client(region)

            req = CreateInstanceRequest.CreateInstanceRequest()
            req.set_ImageId(image_id)
            req.set_InstanceType(instance_type)
            req.set_InstanceName(instance_name)
            req.set_SecurityGroupId(security_group_id)
            req.set_VSwitchId(vswitch_id)
            req.set_SystemDiskSize(system_disk_size)
            req.set_SystemDiskCategory(system_disk_category)
            req.set_InternetMaxBandwidthOut(internet_max_bandwidth_out)
            if zone_id:
                req.set_ZoneId(zone_id)

            resp = client.do_action_with_exception(req)
            import json
            data = json.loads(resp)
            created_id = data.get("InstanceId", "")

            public_ip = ""
            if allocate_public_ip and internet_max_bandwidth_out > 0 and created_id:
                try:
                    ip_req = AllocatePublicIpAddressRequest.AllocatePublicIpAddressRequest()
                    ip_req.set_InstanceId(created_id)
                    ip_resp = client.do_action_with_exception(ip_req)
                    ip_data = json.loads(ip_resp)
                    public_ip = ip_data.get("IpAddress", "")
                except Exception:
                    pass

            return {
                "success": True,
                "data": {
                    "instance_id": created_id,
                    "instance_name": instance_name,
                    "public_ip": public_ip,
                    "region": region,
                },
                "error": "",
            }
        except Exception as e:
            return {"success": False, "data": {}, "error": str(e)}

    @classmethod
    def get_output_schema(cls):
        return [
            {"name": "instance_id", "type": "string", "description": "新建的 ECS 实例 ID"},
            {"name": "instance_name", "type": "string", "description": "实例名称"},
            {"name": "public_ip", "type": "string", "description": "公网 IP（如有分配）"},
            {"name": "region", "type": "string", "description": "地域"},
        ]

    def rollback(self, context: dict, **kwargs) -> dict:
        """回滚：释放刚创建的实例"""
        inst_id = context.get("instance_id", "")
        if inst_id:
            return {"success": True, "data": {"action": "delete_instance", "instance_id": inst_id}}
        return {"success": True, "data": {}}
