"""NetApp 执行器 — 基于 ONTAP REST API 管理存储

executor_type: "netapp"
底层技术: HTTP REST (requests) → NetApp ONTAP API

⚠️ 待完善事项 (见 doc/TODO.md):
  - 凭证管理: 当前使用 os.getenv(), 生产应接入 Vault
  - API 版本: ONTAP 9.6+ REST API, 旧版本需 fallback 到 ZAPI
  - 分页: 列表类操作需要处理分页
  - 证书校验: 生产环境应配置 CA 证书
"""

import json
import logging
import os

import requests
from requests.auth import HTTPBasicAuth

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class NetAppExecutor(BaseExecutor):
    """NetApp ONTAP 存储管理执行器"""

    executor_type = "netapp"

    def _get_session(self, cluster_ip: str) -> requests.Session:
        """创建 ONTAP API Session

        生产环境建议:
          - 从 Vault 读取凭证
          - 使用连接池 (requests.Session)
          - 接入证书校验
        """
        session = requests.Session()
        session.auth = HTTPBasicAuth(
            os.getenv("NETAPP_USER", ""),
            os.getenv("NETAPP_PASSWORD", ""),
        )
        session.verify = os.getenv("NETAPP_VERIFY_SSL", "0") == "1"
        session.headers.update({"Content-Type": "application/json"})
        return session

    def _api_url(self, cluster_ip: str, path: str) -> str:
        return f"https://{cluster_ip}/api/{path.lstrip('/')}"

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行 NetApp 原子操作

        支持原子:
          - netapp_create_volume: 创建存储卷
          - netapp_delete_volume: 删除存储卷
          - netapp_get_volume: 查询卷详情
          - netapp_list_snapshots: 列出快照
          - netapp_create_snapshot: 创建快照
          - netapp_set_export_policy: 设置导出策略
          - netapp_modify_volume: 修改卷属性（扩容）
        """
        atom_type = inputs.get("_atom_type", "")
        cluster_ip = inputs.get("cluster_ip", "")
        if not cluster_ip:
            return ExecuteResult(False, {}, "缺少 cluster_ip")

        try:
            session = self._get_session(cluster_ip)

            if atom_type == "netapp_create_volume":
                return self._create_volume(inputs, session, cluster_ip)
            elif atom_type == "netapp_delete_volume":
                return self._delete_volume(inputs, session, cluster_ip)
            elif atom_type == "netapp_get_volume":
                return self._get_volume(inputs, session, cluster_ip)
            elif atom_type == "netapp_create_snapshot":
                return self._create_snapshot(inputs, session, cluster_ip)
            elif atom_type == "netapp_set_export_policy":
                return self._set_export_policy(inputs, session, cluster_ip)
            elif atom_type == "netapp_modify_volume":
                return self._modify_volume(inputs, session, cluster_ip)
            else:
                return ExecuteResult(False, {}, f"不支持的原子类型: {atom_type}")
        except requests.RequestException as e:
            logger.exception("NetApp API 请求失败")
            return ExecuteResult(False, {}, f"NetApp API 错误: {e}")
        except Exception as e:
            logger.exception("NetApp 操作异常")
            return ExecuteResult(False, {}, str(e))

    def _create_volume(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """创建 FlexVol 卷

        【待完善】
          - 支持 FlexGroup 卷类型
          - QoS 策略设置
          - 自动选择 aggregate（当前需要传入）
        """
        svm = inputs.get("svm_name", "")
        vol_name = inputs.get("volume_name", "")
        size_gb = inputs.get("size_gb", 0)
        aggr = inputs.get("aggregate", "")

        url = self._api_url(cluster_ip, "storage/volumes")
        payload = {
            "name": vol_name,
            "svm": {"name": svm},
            "aggregates": [{"name": aggr}],
            "size": size_gb * 1024 * 1024 * 1024,
            "style": "flexvol",
        }
        # 可选: 快照策略
        if inputs.get("snapshot_policy"):
            payload["snapshot_policy"] = {"name": inputs["snapshot_policy"]}

        resp = session.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()

        return ExecuteResult(True, {
            "volume_uuid": result.get("uuid", ""),
            "volume_name": vol_name,
            "size_gb": size_gb,
            "aggregate": aggr,
            "mount_path": f"/{vol_name}",
            "status": "success",
        })

    def _delete_volume(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """删除存储卷"""
        vol_uuid = inputs.get("volume_uuid", "")
        vol_name = inputs.get("volume_name", "")

        # 优先用 UUID, 没有则用名称查询
        if not vol_uuid and vol_name:
            lookup = self._get_volume_by_name(vol_name, session, cluster_ip)
            if lookup.success:
                vol_uuid = lookup.data.get("uuid", "")
            else:
                return ExecuteResult(True, {"warning": f"卷 {vol_name} 不存在"})

        if vol_uuid:
            url = self._api_url(cluster_ip, f"storage/volumes/{vol_uuid}")
            resp = session.delete(url, timeout=60)
            if resp.status_code == 404:
                return ExecuteResult(True, {"warning": "卷不存在"})
            resp.raise_for_status()

        return ExecuteResult(True, {"status": "deleted", "volume": vol_name or vol_uuid})

    def _get_volume(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """查询卷详情"""
        vol_name = inputs.get("volume_name", "")
        return self._get_volume_by_name(vol_name, session, cluster_ip)

    def _get_volume_by_name(self, vol_name: str, session, cluster_ip: str) -> ExecuteResult:
        """按名称查询卷"""
        url = self._api_url(cluster_ip, f"storage/volumes?name={vol_name}")
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        if not records:
            return ExecuteResult(False, {}, f"卷不存在: {vol_name}")

        vol = records[0]
        return ExecuteResult(True, {
            "uuid": vol.get("uuid", ""),
            "name": vol.get("name", ""),
            "size_gb": round(vol.get("size", 0) / (1024**3), 2),
            "aggregate": (vol.get("aggregates") or [{}])[0].get("name", ""),
            "state": vol.get("state", ""),
        })

    def _create_snapshot(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """创建快照"""
        vol_uuid = inputs.get("volume_uuid", "")
        snap_name = inputs.get("snapshot_name", "")
        url = self._api_url(cluster_ip, f"storage/volumes/{vol_uuid}/snapshots")
        resp = session.post(url, json={"name": snap_name}, timeout=30)
        resp.raise_for_status()
        return ExecuteResult(True, {
            "snapshot_name": snap_name,
            "volume_uuid": vol_uuid,
            "status": "created",
        })

    def _set_export_policy(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """设置导出策略"""
        vol_uuid = inputs.get("volume_uuid", "")
        policy_name = inputs.get("policy_name", "default")
        url = self._api_url(cluster_ip, f"storage/volumes/{vol_uuid}")
        resp = session.patch(url, json={"policy": {"name": policy_name}}, timeout=30)
        resp.raise_for_status()
        return ExecuteResult(True, {
            "volume_uuid": vol_uuid,
            "export_policy": policy_name,
        })

    def _modify_volume(self, inputs: dict, session, cluster_ip: str) -> ExecuteResult:
        """修改卷属性（扩容/改描述等）

        【待完善】
          - ONTAP 缩容仅支持 FlexGroup, FlexVol 只能扩容
          - 需要校验新尺寸 >= 当前尺寸
        """
        vol_uuid = inputs.get("volume_uuid", "")
        new_size_gb = inputs.get("new_size_gb", 0)
        url = self._api_url(cluster_ip, f"storage/volumes/{vol_uuid}")
        payload = {"size": new_size_gb * 1024 * 1024 * 1024}
        if inputs.get("new_snapshot_policy"):
            payload["snapshot_policy"] = {"name": inputs["new_snapshot_policy"]}
        resp = session.patch(url, json=payload, timeout=30)
        resp.raise_for_status()
        return ExecuteResult(True, {
            "volume_uuid": vol_uuid,
            "size_gb": new_size_gb,
            "status": "modified",
        })

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 根据原操作类型执行反向操作"""
        atom_type = inputs.get("_atom_type", "")
        rollback_map = {
            "netapp_create_volume": "netapp_delete_volume",
            "netapp_create_snapshot": None,  # 快照创建一般不需要回滚
            "netapp_set_export_policy": None,  # 改策略一般不需要回滚
        }

        rollback_atom = rollback_map.get(atom_type)
        if not rollback_atom:
            return ExecuteResult(False, {}, f"无可用回滚策略: {atom_type}")

        rb_inputs = dict(inputs)
        rb_inputs["_atom_type"] = rollback_atom
        if context.get("volume_uuid"):
            rb_inputs["volume_uuid"] = context["volume_uuid"]
        if context.get("volume_name"):
            rb_inputs["volume_name"] = context["volume_name"]

        return self.execute(rb_inputs)
