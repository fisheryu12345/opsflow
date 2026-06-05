"""Update ITSM Ticket — 在 OpsFlow 执行节点中更新 ITSM 工单

用于自愈流程执行完毕后，自动更新关联的 ITSM 工单状态、备注等信息。
"""

import json
import logging

from opsflow.plugins.base import BasePlugin
from opsflow.schema.form_schema import FormItem, ValidationRule

logger = logging.getLogger(__name__)

FSM = "itsm_update_ticket"


class UpdateItsmTicketPlugin(BasePlugin):
    name = "更新 ITSM 工单"
    code = "itsm_update_ticket"
    group = "ITSM"
    description = "在 OpsFlow 执行节点中更新 ITSM 工单的状态、备注等信息"
    risk_level = "low"
    icon = "Edit"
    color = "#67C23A"

    @classmethod
    def get_form_config(cls):
        return [
            FormItem(
                tag_code="ticket_id_source",
                type="select",
                name="工单来源",
                attrs={
                    "options": [
                        {"label": "从上下文自动获取", "value": "auto"},
                        {"label": "手动指定工单 ID", "value": "manual"},
                    ],
                },
                default="auto",
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="ticket_id",
                type="input",
                name="工单 ID",
                scope="global",
                attrs={
                    "placeholder": "手动指定工单 ID，支持 ${var} 模板变量",
                },
                hookable=True,
            ),
            FormItem(
                tag_code="action",
                type="select",
                name="操作类型",
                attrs={
                    "options": [
                        {"label": "更新备注", "value": "update_meta"},
                        {"label": "关闭工单", "value": "close"},
                        {"label": "更新状态", "value": "update_status"},
                        {"label": "添加审批意见", "value": "add_comment"},
                    ],
                },
                default="update_meta",
                validation=[ValidationRule(type="required")],
            ),
            FormItem(
                tag_code="comment",
                type="textarea",
                name="备注/意见",
                scope="global",
                attrs={
                    "rows": 4,
                    "placeholder": "备注内容或审批意见，支持 ${var} 模板变量",
                },
            ),
            FormItem(
                tag_code="new_status",
                type="select",
                name="目标状态",
                attrs={
                    "options": [
                        {"label": "已完成", "value": "finished"},
                        {"label": "已终止", "value": "terminated"},
                        {"label": "挂起", "value": "suspended"},
                    ],
                },
                default="finished",
            ),
            FormItem(
                tag_code="meta_updates",
                type="textarea",
                name="扩展字段更新",
                scope="global",
                attrs={
                    "rows": 3,
                    "placeholder": 'JSON 格式，如 {"resolution": "已修复"}，支持 ${var} 模板变量',
                },
            ),
        ]

    @classmethod
    def get_var_types(cls) -> dict:
        return {
            "ticket_id": "splice",
            "comment": "splice",
            "meta_updates": "splice",
        }

    def execute(self, ticket_id_source: str = "auto",
                ticket_id: str = "",
                action: str = "update_meta",
                comment: str = "",
                new_status: str = "finished",
                meta_updates: str = "",
                **kwargs) -> dict:
        try:
            from itsm.models import Ticket

            # 确定目标工单
            target_ticket_id = self._resolve_ticket_id(
                ticket_id_source, ticket_id, kwargs
            )
            if not target_ticket_id:
                return {
                    "success": False,
                    "data": {},
                    "error": "无法确定目标工单 ID",
                }

            try:
                ticket = Ticket.objects.get(id=target_ticket_id)
            except Ticket.DoesNotExist:
                return {
                    "success": False,
                    "data": {},
                    "error": f"工单不存在 (id={target_ticket_id})",
                }

            # 解析 meta_updates
            meta_dict = {}
            if meta_updates:
                try:
                    meta_dict = json.loads(meta_updates)
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "data": {},
                        "error": f"meta_updates 不是有效的 JSON: {e}",
                    }

            # 执行操作
            result_data = {"ticket_id": ticket.id, "sn": ticket.sn}

            if action == "update_meta":
                meta = dict(ticket.meta or {})
                meta["opsflow_updated"] = True
                meta.update(meta_dict)
                if comment:
                    meta["opsflow_comment"] = comment
                    meta["opsflow_updated_at"] = __import__(
                        "datetime"
                    ).datetime.now().isoformat()
                ticket.meta = meta
                ticket.save(update_fields=["meta"])
                result_data["action"] = "meta_updated"

            elif action == "close":
                from itsm.services.pipeline_wrapper import PipelineWrapper

                if ticket.pipeline_id:
                    PipelineWrapper.revoke_pipeline(ticket.pipeline_id)
                ticket.set_status("terminated", operator="opsflow")
                if comment:
                    meta = dict(ticket.meta or {})
                    meta["opsflow_close_reason"] = comment
                    ticket.meta = meta
                    ticket.save(update_fields=["meta"])
                result_data["action"] = "closed"

            elif action == "update_status":
                ticket.set_status(new_status, operator="opsflow")
                if comment:
                    meta = dict(ticket.meta or {})
                    meta["opsflow_status_reason"] = comment
                    ticket.meta = meta
                    ticket.save(update_fields=["meta"])
                result_data["action"] = f"status_updated_to_{new_status}"

            elif action == "add_comment":
                state_history = list(ticket.state_history or [])
                state_history.append({
                    "status": ticket.current_status,
                    "operator": "opsflow",
                    "time": __import__("datetime").datetime.now().isoformat(),
                    "comment": comment,
                })
                ticket.state_history = state_history
                if meta_dict:
                    meta = dict(ticket.meta or {})
                    meta.update(meta_dict)
                    ticket.meta = meta
                ticket.save(update_fields=["state_history", "meta"])
                result_data["action"] = "comment_added"

            logger.info(
                "[%s] Updated ITSM ticket %s (sn=%s) action=%s",
                FSM, ticket.id, ticket.sn, action,
            )

            return {
                "success": True,
                "data": {
                    **result_data,
                    "title": ticket.title,
                    "status": ticket.current_status,
                },
            }

        except Exception as e:
            logger.exception("[%s] Failed to update ITSM ticket: %s", FSM, e)
            return {"success": False, "data": {}, "error": str(e)}

    @staticmethod
    def _resolve_ticket_id(source: str, manual_id: str, context: dict) -> int:
        """解析工单 ID

        - auto: 从 execution context 的 ticket_id 或上下文变量获取
        - manual: 使用手动指定的 ticket_id
        """
        if source == "auto":
            # 检查 execution context
            execution = context.get("execution")
            if execution and hasattr(execution, "context"):
                ctx = execution.context or {}
                ticket_id = ctx.get("ticket_id")
                if ticket_id:
                    return int(ticket_id)
            return None

        if source == "manual" and manual_id:
            try:
                return int(manual_id.strip())
            except (ValueError, AttributeError):
                return None

        return None
