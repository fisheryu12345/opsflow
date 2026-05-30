"""ESXi 执行器 — 基于 pyVmomi 管理 vSphere 虚拟机

executor_type: "esxi"
底层技术: pyVmomi (VMware vSphere Python SDK)

⚠️ 待完善事项 (见 doc/TODO.md):
  - 凭证管理: 当前使用 os.getenv(), 生产应接入 Vault/Secrets Manager
  - 连接池: 每次执行新建连接，高频场景需复用 Session
  - 超时: VM 创建/销毁操作需可配置超时
  - 异步轮询: 长时间任务 (如 VM 克隆) 需 schedule() 轮询
"""

import logging
import os
import ssl
from typing import Optional

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class EsxiExecutor(BaseExecutor):
    """ESXi/vCenter 虚拟机生命周期管理执行器"""

    executor_type = "esxi"

    def _connect(self, host: str):
        """连接 vCenter/ESXi

        生产环境建议:
          - 从 Vault 读取凭证, 而非 os.getenv
          - 使用连接池复用 Session
          - 证书校验设为 True 并配置 CA bundle
        """
        try:
            from pyVim.connect import SmartConnect, Disconnect
            from pyVmomi import vim
        except ImportError:
            raise ImportError("需要安装 pyVmomi: pip install pyvmomi")

        context = ssl._create_unverified_context() if os.getenv("ESXI_VERIFY_SSL", "0") == "0" else None
        si = SmartConnect(
            host=host,
            user=os.getenv("ESXI_USER", ""),
            pwd=os.getenv("ESXI_PASSWORD", ""),
            sslContext=context,
            port=int(os.getenv("ESXI_PORT", "443")),
        )
        return si

    def _get_obj(self, content, vimtype, name):
        """按名称查找 vSphere 对象"""
        for obj in content.viewManager.CreateContainerView(
            content.rootFolder, [vimtype], recursive=True
        ).view:
            if obj.name == name:
                return obj
        return None

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行 ESXi 原子操作

        支持原子:
          - esxi_create_vm: 创建虚拟机
          - esxi_destroy_vm: 删除虚拟机
          - esxi_power_on: 开机
          - esxi_power_off: 关机
          - esxi_get_state: 查询状态
          - esxi_clone_vm: 克隆虚拟机 (需 schedule)
        """
        atom_type = inputs.get("_atom_type", "")
        esxi_host = inputs.get("esxi_host", "")
        if not esxi_host:
            return ExecuteResult(False, {}, "缺少 esxi_host")

        try:
            si = self._connect(esxi_host)
            content = si.RetrieveContent()

            if atom_type == "esxi_get_state":
                return self._get_vm_state(inputs, content)
            elif atom_type == "esxi_power_on":
                return self._power_vm(inputs, content, power_on=True)
            elif atom_type == "esxi_power_off":
                return self._power_vm(inputs, content, power_on=False)
            elif atom_type == "esxi_create_vm":
                return self._create_vm(inputs, content)
            elif atom_type == "esxi_destroy_vm":
                return self._destroy_vm(inputs, content)
            else:
                return ExecuteResult(False, {}, f"不支持的原子类型: {atom_type}")
        except Exception as e:
            logger.exception("ESXi 操作失败")
            return ExecuteResult(False, {}, str(e))

    def _create_vm(self, inputs: dict, content) -> ExecuteResult:
        """创建虚拟机 (伪代码骨架 — 需根据实际环境调整配置)"""
        from pyVmomi import vim

        vm_name = inputs.get("vm_name", "")
        datastore_name = inputs.get("datastore", "datastore1")
        network_name = inputs.get("network", "VM Network")

        # 1. 查找资源
        datacenter = content.rootFolder.childEntity[0]
        vm_folder = datacenter.vmFolder
        host_system = self._get_obj(content, vim.HostSystem, inputs.get("esxi_host"))
        resource_pool = host_system.parent.resourcePool
        datastore = self._get_obj(content, vim.Datastore, datastore_name)

        if not all([host_system, resource_pool, datastore]):
            return ExecuteResult(False, {}, "无法找到 ESXi 资源 (host/datastore)")

        # 2. 构建 VM 配置
        # 【待完善】设备配置（磁盘、网卡）需根据实际环境调整
        vmx_file = vim.vm.FileInfo(
            vmPathName=f"[{datastore_name}] {vm_name}/{vm_name}.vmx"
        )
        config = vim.vm.ConfigSpec(
            name=vm_name,
            memoryMB=inputs.get("memory_mb", 4096),
            numCPUs=inputs.get("cpu", 2),
            files=vmx_file,
            guestId="otherLinux64Guest",
            devices=[
                vim.vm.device.VirtualDeviceSpec(
                    operation=vim.vm.device.VirtualDeviceSpec.Operation.add,
                    device=vim.vm.device.VirtualLsiLogicController(
                        key=100, sharedBus=vim.vm.device.VirtualSCSIController.Sharing.noSharing
                    ),
                ),
            ],
        )

        # 3. 提交任务
        task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
        self._wait_for_task(task)

        vm = task.info.result
        vm_id = vm._moId if hasattr(vm, "_moId") else str(vm)

        return ExecuteResult(True, {
            "vm_id": vm_id,
            "vm_name": vm_name,
            "power_state": "poweredOff",
            "status": "success",
        })

    def _destroy_vm(self, inputs: dict, content) -> ExecuteResult:
        """删除虚拟机"""
        from pyVmomi import vim

        vm_name = inputs.get("vm_name", "")
        vm = self._get_obj(content, vim.VirtualMachine, vm_name)
        if not vm:
            return ExecuteResult(False, {}, f"虚拟机不存在: {vm_name}")

        task = vm.Destroy_Task()
        self._wait_for_task(task)
        return ExecuteResult(True, {"status": "destroyed", "vm_name": vm_name})

    def _power_vm(self, inputs: dict, content, power_on: bool) -> ExecuteResult:
        """开关机"""
        from pyVmomi import vim

        vm_name = inputs.get("vm_name", "")
        vm = self._get_obj(content, vim.VirtualMachine, vm_name)
        if not vm:
            return ExecuteResult(False, {}, f"虚拟机不存在: {vm_name}")

        task = vm.PowerOn_Task() if power_on else vm.PowerOff_Task()
        self._wait_for_task(task)
        return ExecuteResult(True, {
            "vm_name": vm_name,
            "power_state": "poweredOn" if power_on else "poweredOff",
        })

    def _get_vm_state(self, inputs: dict, content) -> ExecuteResult:
        """查询 VM 状态"""
        from pyVmomi import vim

        vm_name = inputs.get("vm_name", "")
        vm = self._get_obj(content, vim.VirtualMachine, vm_name)
        if not vm:
            return ExecuteResult(True, {"exists": False, "vm_name": vm_name})

        return ExecuteResult(True, {
            "exists": True,
            "vm_name": vm_name,
            "power_state": vm.runtime.powerState,
            "guest_ip": vm.guest.ipAddress if vm.guest else "",
            "cpu": vm.config.hardware.numCPU if vm.config else None,
            "memory_mb": vm.config.hardware.memoryMB if vm.config else None,
        })

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 根据原始操作类型执行反向操作

        设计原则:
          - create → destroy
          - power_on → power_off
          - power_off → power_on
        """
        atom_type = inputs.get("_atom_type", "")

        # 根据原操作类型决定回滚动作
        rollback_map = {
            "esxi_create_vm": "esxi_destroy_vm",
            "esxi_power_on": "esxi_power_off",
            "esxi_power_off": "esxi_power_on",
        }
        rollback_atom = rollback_map.get(atom_type)
        if not rollback_atom:
            return ExecuteResult(False, {}, f"无可用回滚策略: {atom_type}")

        # 用原始输入的参数 + 上下文中的资源 ID 执行回滚
        rollback_inputs = dict(inputs)
        rollback_inputs["_atom_type"] = rollback_atom

        # 如果上下文中有关键信息，注入
        if context.get("vm_name"):
            rollback_inputs["vm_name"] = context["vm_name"]

        return self.execute(rollback_inputs)

    @staticmethod
    def _wait_for_task(task, timeout: int = 300):
        """等待 vSphere 任务完成

        【待完善】
          - 当前为同步阻塞, 长时间任务应改为 bamboo-engine schedule 轮询模式
          - 超时应可配置
        """
        try:
            from pyVmomi import vim
        except ImportError:
            return

        import time
        start = time.time()
        while time.time() - start < timeout:
            if task.info.state in (vim.TaskInfo.State.success,
                                    vim.TaskInfo.State.error):
                break
            time.sleep(2)

        if task.info.state == vim.TaskInfo.State.error:
            raise RuntimeError(f"VMware 任务失败: {task.info.error}")
