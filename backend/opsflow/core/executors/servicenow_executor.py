"""ServiceNow 执行器 — 基于 REST API 管理 ITSM 流程

executor_type: "servicenow"
底层技术: HTTP REST (requests) → ServiceNow Table API

⚠️ 待完善事项 (见 doc/TODO.md):
  - 该执行器为伪代码骨架, 未经过真实 ServiceNow 实例验证
  - 认证方式: 当前仅支持 Basic Auth, 生产可能需要 OAuth2
  - 表结构: ServiceNow 实例可能自定义了表结构, 需要适配
  - 速率限制: ServiceNow REST API 有请求频率限制, 需要重试逻辑
  - 附件: 创建工单时可能需要上传附件, 当前未实现
"""

import json
import logging
import os

import requests
from requests.auth import HTTPBasicAuth

from .base import BaseExecutor, ExecuteResult

logger = logging.getLogger(__name__)


class ServiceNowExecutor(BaseExecutor):
    """ServiceNow ITSM 流程自动化执行器"""

    executor_type = "servicenow"

    def _get_session(self, instance: str) -> requests.Session:
        """创建 ServiceNow API Session

        生产环境建议:
          - 使用 OAuth2 (client_credentials) 替代 Basic Auth
          - 从 Vault 读取凭证
          - 配置重试策略 (Retry-After 头)
        """
        session = requests.Session()
        session.auth = HTTPBasicAuth(
            os.getenv("SERVICENOW_USER", ""),
            os.getenv("SERVICENOW_PASSWORD", ""),
        )
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        session.verify = os.getenv("SERVICENOW_VERIFY_SSL", "0") == "1"
        return session

    def _api_url(self, instance: str, path: str) -> str:
        return f"https://{instance}.service-now.com/api/now/{path.lstrip('/')}"

    def execute(self, inputs: dict) -> ExecuteResult:
        """执行 ServiceNow 原子操作

        支持原子:
          - servicenow_create_incident: 创建故障单
          - servicenow_update_incident: 更新故障单
          - servicenow_get_incident: 查询故障单
          - servicenow_create_change_request: 创建变更单
          - servicenow_get_cmdb_ci: 查询 CMDB CI
          - servicenow_create_catalog_request: 创建服务目录请求
        """
        atom_type = inputs.get("_atom_type", "")
        instance = os.getenv("SERVICENOW_INSTANCE", "")
        if not instance:
            return ExecuteResult(False, {}, "未配置 SERVICENOW_INSTANCE")

        try:
            session = self._get_session(instance)

            if atom_type == "servicenow_create_incident":
                return self._create_incident(inputs, session, instance)
            elif atom_type == "servicenow_update_incident":
                return self._update_incident(inputs, session, instance)
            elif atom_type == "servicenow_get_incident":
                return self._get_incident(inputs, session, instance)
            elif atom_type == "servicenow_create_change_request":
                return self._create_change_request(inputs, session, instance)
            elif atom_type == "servicenow_get_cmdb_ci":
                return self._get_cmdb_ci(inputs, session, instance)
            else:
                return ExecuteResult(False, {}, f"不支持的原子类型: {atom_type}")
        except requests.RequestException as e:
            logger.exception("ServiceNow API 请求失败")
            return ExecuteResult(False, {}, f"ServiceNow API 错误: {e}")
        except Exception as e:
            logger.exception("ServiceNow 操作异常")
            return ExecuteResult(False, {}, str(e))

    def _create_incident(self, inputs: dict, session, instance: str) -> ExecuteResult:
        """创建故障单

        【待完善】
          - assignment_group 需要校验存在性
          - 支持附件上传
          - 支持关联 CI (cmdb_ci 字段)
        """
        url = self._api_url(instance, "table/incident")
        payload = {
            "short_description": inputs.get("short_description", ""),
            "description": inputs.get("description", ""),
            "urgency": inputs.get("urgency", "3"),   # 1=高 2=中 3=低
            "impact": inputs.get("impact", "3"),
            "caller_id": inputs.get("caller_id", ""),
            "assignment_group": inputs.get("assignment_group", ""),
            "category": inputs.get("category", "software"),
            "subcategory": inputs.get("subcategory", ""),
        }
        # 移除空值
        payload = {k: v for k, v in payload.items() if v}

        resp = session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json().get("result", {})

        return ExecuteResult(True, {
            "incident_id": result.get("sys_id", ""),
            "incident_number": result.get("number", ""),
            "state": result.get("state", ""),
            "short_description": result.get("short_description", ""),
            "sys_created_on": result.get("sys_created_on", ""),
            "status": "created",
        })

    def _update_incident(self, inputs: dict, session, instance: str) -> ExecuteResult:
        """更新故障单状态"""
        sys_id = inputs.get("sys_id", "")
        if not sys_id:
            return ExecuteResult(False, {}, "缺少 sys_id")

        url = self._api_url(instance, f"table/incident/{sys_id}")
        payload = {}
        for field in ("state", "work_notes", "close_notes", "assignment_group",
                      "assigned_to", "urgency", "impact"):
            if inputs.get(field):
                payload[field] = inputs[field]

        resp = session.patch(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json().get("result", {})

        return ExecuteResult(True, {
            "sys_id": result.get("sys_id", ""),
            "number": result.get("number", ""),
            "state": result.get("state", ""),
            "status": "updated",
        })

    def _get_incident(self, inputs: dict, session, instance: str) -> ExecuteResult:
        """查询故障单"""
        sys_id = inputs.get("sys_id", "")
        number = inputs.get("number", "")

        query = f"sys_id={sys_id}" if sys_id else f"number={number}"
        url = self._api_url(instance, f"table/incident?{query}")

        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("result", [])
        if not records:
            return ExecuteResult(False, {}, f"故障单不存在: {sys_id or number}")

        incident = records[0]
        return ExecuteResult(True, {
            "sys_id": incident.get("sys_id"),
            "number": incident.get("number"),
            "state": incident.get("state"),
            "short_description": incident.get("short_description"),
            "assignment_group": incident.get("assignment_group", {}).get("display_value"),
            "assigned_to": incident.get("assigned_to", {}).get("display_value"),
            "sys_updated_on": incident.get("sys_updated_on"),
        })

    def _create_change_request(self, inputs: dict, session, instance: str) -> ExecuteResult:
        """创建变更单

        【待完善】
          - 审批流: 根据 type 自动设置审批人
          - CAB (Change Advisory Board) 会议调度
          - 变更窗口 (change_window) 冲突检测
        """
        url = self._api_url(instance, "table/change_request")
        payload = {
            "short_description": inputs.get("short_description", ""),
            "description": inputs.get("description", ""),
            "type": inputs.get("type", "normal"),    # normal / standard / emergency
            "risk": inputs.get("risk", "3"),
            "impact": inputs.get("impact", "3"),
            "priority": inputs.get("priority", "4"),
            "assignment_group": inputs.get("assignment_group", ""),
            "start_date": inputs.get("start_date", ""),
            "end_date": inputs.get("end_date", ""),
            "implementation_plan": inputs.get("implementation_plan", ""),
            "backout_plan": inputs.get("backout_plan", ""),
            "test_plan": inputs.get("test_plan", ""),
        }
        payload = {k: v for k, v in payload.items() if v}

        resp = session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json().get("result", {})

        return ExecuteResult(True, {
            "change_id": result.get("sys_id", ""),
            "change_number": result.get("number", ""),
            "state": result.get("state", ""),
            "status": "created",
        })

    def _get_cmdb_ci(self, inputs: dict, session, instance: str) -> ExecuteResult:
        """查询 CMDB CI 信息

        【待完善】
          - 支持自定义 CI 类 (sys_class_name)
          - 支持模糊搜素
          - 支持获取 CI 的关系图 (cmdb_rel_ci)
        """
        sys_id = inputs.get("sys_id", "")
        name = inputs.get("name", "")
        ci_class = inputs.get("ci_class", "cmdb_ci_server")

        if not sys_id and not name:
            return ExecuteResult(False, {}, "需要 sys_id 或 name")

        query = f"sys_id={sys_id}" if sys_id else f"name={name}"
        url = self._api_url(instance, f"table/{ci_class}?{query}")

        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("result", [])
        if not records:
            return ExecuteResult(False, {}, f"CI 不存在: {name or sys_id}")

        ci = records[0]
        return ExecuteResult(True, {
            "sys_id": ci.get("sys_id"),
            "name": ci.get("name"),
            "sys_class_name": ci.get("sys_class_name"),
            "ip_address": ci.get("ip_address"),
            "serial_number": ci.get("serial_number"),
            "install_status": ci.get("install_status"),
            "environment": ci.get("environment"),
        })

    def rollback(self, inputs: dict, context: dict) -> ExecuteResult:
        """回滚 — 将工单状态回退到上一个状态

        设计原则:
          - created → closed (标记为已关闭)
          - 不真正删除记录 (ServiceNow 规范不允许 delete)
          - 写入回滚备注
        """
        atom_type = inputs.get("_atom_type", "")
        sys_id = context.get("incident_id") or context.get("change_id") or ""

        if not sys_id:
            return ExecuteResult(False, {}, "无上下文 ID 用于回滚")

        # 对于工单类操作, 回滚策略是关闭并添加备注
        rollback_note = f"OpsFlow 自动回滚: 原操作 {atom_type}"
        rb_inputs = {
            "_atom_type": atom_type.replace("create_", "update_"),
            "sys_id": sys_id,
            "state": "7",  # Closed
            "work_notes": rollback_note,
            "close_notes": rollback_note,
        }

        instance = os.getenv("SERVICENOW_INSTANCE", "")
        if not instance:
            return ExecuteResult(False, {}, "未配置 SERVICENOW_INSTANCE")

        try:
            session = self._get_session(instance)
            if "incident" in atom_type:
                return self._update_incident(rb_inputs, session, instance)
            elif "change_request" in atom_type:
                return self._update_incident(rb_inputs, session, instance)
        except Exception as e:
            return ExecuteResult(False, {}, str(e))

        return ExecuteResult(False, {}, f"无可用回滚策略: {atom_type}")
