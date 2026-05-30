"""Redfish 执行器 — 基于 DMTF Redfish API 管理裸金属服务器

executor_type: "redfish"
底层技术: HTTP REST (requests) → BMC Redfish API

适用场景:
  - 服务器带外管理 (iDRAC / iLO / iBMC / XClarity)
  - 电源管理 (开/关/重启)
  - 固件更新
  - RAID 配置
  - 虚拟介质挂载

⚠️ 待完善事项 (见 doc/TODO.md):
  - 该执行器为伪代码骨架, 仅经过模拟器验证
  - OEM 扩展: 各厂商 (Dell iDRAC, HPE iLO, Lenovo XClarity) 有私有 OEM 属性
  - 事件监听: 硬件告警应通过 Redfish Events/SSE 订阅, 而非轮询
  - 固件更新: 需要处理 Async POST 模式, bamboo-engine schedule 轮询 Task
  - 认证: 当前仅 Basic Auth, 生产应支持 Session (X-Auth-Token)
"""

import json
import logging
import os

import requests
from requests.auth import HTTPBasicAuth

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class RedfishExecutor(BaseExecutor):
    """Redfish 裸金属服务器管理执行器"""

    executor_type = "redfish"

    def _get_session(self, bmc_ip: str) -> requests.Session:
        """创建 Redfish API Session

        生产环境建议:
          - 使用 Token 认证 (POST /redfish/v1/Sessions)
          - 从 Vault 读取 BMC 凭证
          - 证书校验 (iDRAC/iLO 通常自签名, 需配置 CA)
        """
        session = requests.Session()
        session.auth = HTTPBasicAuth(
            os.getenv("REDFISH_USER", "root"),
            os.getenv("REDFISH_PASSWORD", ""),
        )
        session.verify = os.getenv("REDFISH_VERIFY_SSL", "0") == "1"
        session.headers.update({"Content-Type": "application/json"})
        return session

    def _root_url(self, bmc_ip: str) -> str:
        return f"https://{bmc_ip}/redfish/v1"

    def _get_system_resource(self, session, bmc_ip: str) -> str:
        """获取 Systems 集合中的第一个 System OData ID"""
        resp = session.get(f"{self._root_url(bmc_ip)}/Systems", timeout=30)
        resp.raise_for_status()
        members = resp.json().get("Members", [])
        if not members:
            raise RuntimeError("Redfish 未返回 Systems 资源")
        return members[0].get("@odata.id", "")

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行 Redfish 原子操作

        支持原子:
          - redfish_get_system_info: 获取服务器信息
          - redfish_power_on: 开机
          - redfish_power_off: 关机 (强制)
          - redfish_power_cycle: 冷重启
          - redfish_graceful_shutdown: 优雅关机
          - redfish_get_power_state: 获取电源状态
          - redfish_set_boot_device: 设置引导设备
          - redfish_mount_iso: 挂载虚拟介质 (需 OEM 扩展)
          - redfish_list_network_adapters: 列出网络适配器
          - redfish_list_storage: 列出存储控制器
          - redfish_create_raid: 创建 RAID 卷
          - redfish_firmware_inventory: 固件清单
          - redfish_update_firmware: 更新固件 (异步)
        """
        atom_type = inputs.get("_atom_type", "")
        bmc_ip = inputs.get("bmc_ip", "")
        if not bmc_ip:
            return ExecuteResult(False, {}, "缺少 bmc_ip")

        try:
            session = self._get_session(bmc_ip)
            system_path = self._get_system_resource(session, bmc_ip)

            if atom_type == "redfish_get_system_info":
                return self._get_system_info(session, bmc_ip, system_path)
            elif atom_type in ("redfish_power_on", "redfish_power_off",
                               "redfish_power_cycle", "redfish_graceful_shutdown"):
                return self._set_power_state(inputs, session, bmc_ip, system_path)
            elif atom_type == "redfish_get_power_state":
                return self._get_power_state(session, bmc_ip, system_path)
            elif atom_type == "redfish_set_boot_device":
                return self._set_boot_device(inputs, session, bmc_ip, system_path)
            elif atom_type == "redfish_list_storage":
                return self._list_storage(session, bmc_ip, system_path)
            elif atom_type == "redfish_firmware_inventory":
                return self._firmware_inventory(session, bmc_ip)
            else:
                return ExecuteResult(False, {}, f"不支持的原子类型: {atom_type}")
        except requests.RequestException as e:
            logger.exception("Redfish API 请求失败")
            return ExecuteResult(False, {}, f"Redfish 通信错误: {e}")
        except Exception as e:
            logger.exception("Redfish 操作异常")
            return ExecuteResult(False, {}, str(e))

    def _get_system_info(self, session, bmc_ip: str, system_path: str) -> ExecuteResult:
        """获取服务器详细信息"""
        url = f"{self._root_url(bmc_ip)}{system_path}"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        sys = resp.json()

        return ExecuteResult(True, {
            "manufacturer": sys.get("Manufacturer", ""),
            "model": sys.get("Model", ""),
            "serial_number": sys.get("SerialNumber", ""),
            "bios_version": sys.get("BiosVersion", ""),
            "cpu_count": len(sys.get("Processors", {}).get("Members", [])),
            "memory_gb": round(sys.get("MemorySummary", {}).get("TotalSystemMemoryGiB", 0)),
            "power_state": sys.get("PowerState", ""),
            "host_name": sys.get("HostName", ""),
            "part_number": sys.get("PartNumber", ""),
        })

    def _set_power_state(self, inputs: dict, session, bmc_ip: str, system_path: str) -> ExecuteResult:
        """设置电源状态"""
        atom_type = inputs.get("_atom_type", "")
        reset_type_map = {
            "redfish_power_on": "On",
            "redfish_power_off": "ForceOff",
            "redfish_power_cycle": "PowerCycle",
            "redfish_graceful_shutdown": "GracefulShutdown",
        }
        reset_type = reset_type_map.get(atom_type, "On")

        url = f"{self._root_url(bmc_ip)}{system_path}/Actions/ComputerSystem.Reset"
        payload = {"ResetType": reset_type}

        resp = session.post(url, json=payload, timeout=30)
        resp.raise_for_status()

        return ExecuteResult(True, {
            "action": reset_type,
            "status": "completed",
            "message": f"已将服务器电源设置为 {reset_type}",
        })

    def _get_power_state(self, session, bmc_ip: str, system_path: str) -> ExecuteResult:
        """获取当前电源状态"""
        url = f"{self._root_url(bmc_ip)}{system_path}"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        power_state = resp.json().get("PowerState", "Unknown")

        return ExecuteResult(True, {"power_state": power_state})

    def _set_boot_device(self, inputs: dict, session, bmc_ip: str, system_path: str) -> ExecuteResult:
        """设置引导设备

        【待完善】
          - 各厂商支持的 BootSourceOverrideTarget 可能不同
          - Dell: Pxe, Hdd, Cd, BiosSetup, VMedia-DVD
          - HPE: PXE, HDD, CD, USB, SD
        """
        boot_target = inputs.get("boot_target", "Pxe")
        url = f"{self._root_url(bmc_ip)}{system_path}"
        payload = {
            "Boot": {
                "BootSourceOverrideTarget": boot_target,
                "BootSourceOverrideEnabled": "Once",
            }
        }
        resp = session.patch(url, json=payload, timeout=30)
        resp.raise_for_status()

        return ExecuteResult(True, {
            "boot_device": boot_target,
            "status": "set",
            "message": f"下次引导设备设置为 {boot_target}",
        })

    def _list_storage(self, session, bmc_ip: str, system_path: str) -> ExecuteResult:
        """列出存储控制器和磁盘

        【待完善】
          - RAID 创建需要调用 Dell OEM / HPE OEM 扩展 API
          - 各厂商的存储管理 API 差异大, 需要适配层
        """
        url = f"{self._root_url(bmc_ip)}{system_path}/Storage"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        storage_collection = resp.json().get("Members", [])

        controllers = []
        for storage_member in storage_collection:
            storage_url = storage_member.get("@odata.id", "")
            storage_resp = session.get(f"{self._root_url(bmc_ip)}{storage_url}", timeout=30)
            storage_resp.raise_for_status()
            storage_data = storage_resp.json()

            drives = []
            for drive_ref in storage_data.get("Drives", []):
                drive_url = drive_ref.get("@odata.id", "")
                drive_resp = session.get(f"{self._root_url(bmc_ip)}{drive_url}", timeout=30)
                if drive_resp.ok:
                    drive = drive_resp.json()
                    drives.append({
                        "id": drive.get("Id"),
                        "capacity_gb": round(drive.get("CapacityBytes", 0) / (1024**3), 1),
                        "type": drive.get("MediaType", ""),
                        "protocol": drive.get("Protocol", ""),
                        "model": drive.get("Model", ""),
                    })

            controllers.append({
                "id": storage_data.get("Id"),
                "name": storage_data.get("Name"),
                "drives": drives,
            })

        return ExecuteResult(True, {
            "controllers": controllers,
            "controller_count": len(controllers),
            "total_drives": sum(len(c["drives"]) for c in controllers),
        })

    def _firmware_inventory(self, session, bmc_ip: str) -> ExecuteResult:
        """获取固件清单"""
        url = f"{self._root_url(bmc_ip)}/UpdateService/FirmwareInventory"
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        members = resp.json().get("Members", [])

        firmware_list = []
        for member in members:
            fw_url = member.get("@odata.id", "")
            fw_resp = session.get(f"{self._root_url(bmc_ip)}{fw_url}", timeout=30)
            if fw_resp.ok:
                fw = fw_resp.json()
                firmware_list.append({
                    "name": fw.get("Name", ""),
                    "version": fw.get("Version", ""),
                    "status": fw.get("Status", {}).get("Health", ""),
                })

        return ExecuteResult(True, {
            "firmware": firmware_list,
            "count": len(firmware_list),
        })

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 电源状态恢复到操作前

        【待完善】
          - 需要记录操作前的电源状态
          - 固件更新回滚需要调用 UpdateService.SimpleUpdate 指定上一版本
        """
        atom_type = inputs.get("_atom_type", "")
        prev_state = context.get("previous_power_state")

        if atom_type in ("redfish_power_off", "redfish_power_cycle", "redfish_graceful_shutdown"):
            if prev_state == "On":
                rb_inputs = dict(inputs)
                rb_inputs["_atom_type"] = "redfish_power_on"
                return self.execute(rb_inputs)

        return ExecuteResult(False, {}, f"无可用回滚策略: {atom_type}")
