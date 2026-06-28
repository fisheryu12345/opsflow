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
                        type="async_select",
                        name="地域",
                        name_en="Region",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-regions/",
                            "placeholder": "选择地域...",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择地域")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="zone_id",
                        type="async_select",
                        name="可用区",
                        name_en="Zone ID",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-zones/",
                            "depends_on": "region",
                            "placeholder": "选择可用区（可选）...",
                        },
                        col=6,
                    ),
                    FormItem(
                        tag_code="image_id",
                        type="async_select",
                        name="镜像",
                        name_en="Image",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-images/",
                            "depends_on": "region",
                            "placeholder": "选择镜像...",
                            "description": "选择可用镜像，切换地域后自动刷新",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择镜像")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="instance_type",
                        type="async_select",
                        name="实例规格",
                        name_en="Instance Type",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-instance-types/",
                            "depends_on": "region,zone_id",
                            "placeholder": "先选地域和可用区...",
                            "description": "选择可用实例规格，选可用区后仅显示支持的规格",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择实例规格")],
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
                        type="async_select",
                        name="安全组",
                        name_en="Security Group",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-security-groups/",
                            "depends_on": "region",
                            "placeholder": "选择安全组...",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择安全组")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="vswitch_id",
                        type="async_select",
                        name="VSwitch",
                        name_en="VSwitch",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-vswitches/",
                            "depends_on": "region,zone_id",
                            "placeholder": "选择交换机（先选可用区）...",
                        },
                        validation=[ValidationRule(type="required", error_message="请选择 VSwitch")],
                        col=6,
                    ),
                    FormItem(
                        tag_code="internet_max_bandwidth_out",
                        type="slider",
                        name="公网带宽",
                        name_en="Bandwidth",
                        default=0,
                        attrs={"min": 0, "max": 20, "label-0": "无公网", "label-n": "{value} Mbps"},
                        col=12,
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
                        type="async_select",
                        name="系统盘类型",
                        name_en="Disk Category",
                        default="cloud_essd",
                        attrs={
                            "api_endpoint": "/api/opsflow/plugins/aliyun/describe-disk-categories/",
                            "depends_on": "region,instance_type",
                            "placeholder": "选择云盘类型...",
                        },
                        col=6,
                    ),
                ],
            ),
        ]

    def execute(self, instance_name: str, region: str = "",
                zone_id: str = "", image_id: str = "", instance_type: str = "",
                security_group_id: str = "", vswitch_id: str = "",
                internet_max_bandwidth_out: int = 0,
                system_disk_size: int = 0,
                system_disk_category: str = "",
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
            if system_disk_size > 0:
                req.set_SystemDiskSize(system_disk_size)
            if system_disk_category:
                req.set_SystemDiskCategory(system_disk_category)
            req.set_InternetMaxBandwidthOut(internet_max_bandwidth_out)
            if zone_id:
                req.set_ZoneId(zone_id)

            resp = client.do_action_with_exception(req)
            import json
            data = json.loads(resp)
            created_id = data.get("InstanceId", "")

            public_ip = ""
            if internet_max_bandwidth_out > 0 and created_id:
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
