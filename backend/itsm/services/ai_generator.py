# -*- coding: utf-8 -*-
"""AI 驱动的 ITSM 工作流生成器

将自然语言描述转换为 Workflow + States + Transitions + Fields 定义
"""

import json
import logging

logger = logging.getLogger(__name__)


class AIGenerator:
    """AI 驱动的 ITSM 工作流生成器"""

    SYSTEM_PROMPT = """你是一个 ITSM 流程设计专家。根据用户自然语言描述，生成标准的工作流定义 JSON。

工作流包含以下节点类型:
- NORMAL: 普通节点（填单/处理），包含表单字段
- APPROVAL: 审批节点（单签/多签）
- SIGN: 会签节点（多审批人）
- TASK: 自动任务节点（API调用）
- START/END: 起止节点（系统自动添加）

每个节点可配置:
- name: 节点名称
- type: 节点类型
- processors_type: 处理人类型 (PERSON/STARTER_LEADER/ROLE)
- processors: 处理人配置
- fields: 表单字段（每个字段含 key/name/type/required/choices）
- is_multi: 是否多签
- finish_condition: 完成条件

连线 direction 通常为 FORWARD。审批拒绝分支建议自动生成。
"""

    def generate_workflow(self, description: str, itsm_type: str = 'change') -> dict:
        """根据自然语言生成完整工作流定义"""
        # 内置模板用于快速生成（无需调用 AI）
        return self._builtin_generate(description, itsm_type)

    def generate_fields(self, state_description: str) -> list:
        """根据节点描述生成表单字段"""
        from ..models.field import Field
        # 返回内置的常见字段模板
        templates = {
            '审批意见': [
                {'key': 'approve_result', 'name': '审批结果', 'type': 'RADIO',
                 'required': True, 'choice': [{'label': '通过', 'value': 'true'},
                                               {'label': '拒绝', 'value': 'false'}]},
                {'key': 'approve_comment', 'name': '审批意见', 'type': 'TEXT',
                 'required': False},
            ],
            '基本信息': [
                {'key': 'title', 'name': '标题', 'type': 'STRING', 'required': True},
                {'key': 'description', 'name': '描述', 'type': 'TEXT', 'required': False},
            ],
            '变更信息': [
                {'key': 'change_type', 'name': '变更类型', 'type': 'SELECT', 'required': True,
                 'choice': [{'label': '标准变更', 'value': 'standard'},
                            {'label': '普通变更', 'value': 'normal'},
                            {'label': '紧急变更', 'value': 'emergency'}]},
                {'key': 'risk_level', 'name': '风险等级', 'type': 'SELECT', 'required': True,
                 'choice': [{'label': '低', 'value': 'low'},
                            {'label': '中', 'value': 'medium'},
                            {'label': '高', 'value': 'high'}]},
                {'key': 'change_plan', 'name': '变更方案', 'type': 'RICHTEXT', 'required': True},
                {'key': 'rollback_plan', 'name': '回滚方案', 'type': 'TEXT', 'required': True},
            ],
        }
        for name, fields in templates.items():
            if name in state_description:
                return fields
        return templates['基本信息']

    def _builtin_generate(self, description: str, itsm_type: str) -> dict:
        """内置模板引擎 — 根据关键词快速生成"""
        desc_lower = description.lower()

        # 检测审批级数
        levels = self._count_approval_levels(description)

        states = []
        transitions = []

        # START node
        states.append({'id': 1, 'name': '开始', 'type': 'START', 'is_builtin': True})

        # Fill form node
        states.append({
            'id': 2, 'name': '填写申请', 'type': 'NORMAL', 'is_builtin': True,
            'processors_type': 'STARTER', 'processors': '',
            'fields': self._detect_fields(itsm_type, description),
        })
        transitions.append({
            'from_state_id': 1, 'to_state_id': 2,
            'name': '', 'condition_type': 'default', 'condition': {},
        })

        # Approval nodes
        prev_id = 2
        approval_names = self._detect_approval_names(description)
        for i, (approver_type, approver_name) in enumerate(approval_names):
            state_id = 3 + i
            states.append({
                'id': state_id, 'name': approver_name, 'type': 'APPROVAL',
                'processors_type': approver_type, 'processors': '[]',
                'is_multi': False, 'finish_condition': {'type': 'all', 'value': 1},
                'fields': [
                    {'key': 'approve_result', 'name': '审批结果', 'type': 'RADIO',
                     'required': True,
                     'choice': [{'label': '通过', 'value': 'true'},
                                {'label': '拒绝', 'value': 'false'}]},
                    {'key': 'approve_comment', 'name': '审批意见',
                     'type': 'TEXT', 'required': False},
                ],
            })
            transitions.append({
                'from_state_id': prev_id, 'to_state_id': state_id,
                'name': '提交', 'condition_type': 'default', 'condition': {},
            })
            # Reject branch → END
            reject_state_id = 100 + state_id
            states.append({
                'id': reject_state_id, 'name': '已拒绝', 'type': 'END', 'is_builtin': True,
            })
            transitions.append({
                'from_state_id': state_id, 'to_state_id': reject_state_id,
                'name': '拒绝', 'condition_type': 'branch',
                'condition': {'approve_result': {'eq': 'false'}},
            })
            prev_id = state_id

        # Execute node (if has execute keywords)
        if any(kw in desc_lower for kw in ['执行', '部署', '变更', '发布', '上线']):
            exec_id = prev_id + 1
            states.append({
                'id': exec_id, 'name': '自动执行', 'type': 'TASK',
                'processors_type': 'PERSON', 'processors': '[]',
                'fields': [],
            })
            transitions.append({
                'from_state_id': prev_id, 'to_state_id': exec_id,
                'name': '通过', 'condition_type': 'default', 'condition': {},
            })
            prev_id = exec_id

        # END node
        end_id = prev_id + 1
        states.append({'id': end_id, 'name': '结束', 'type': 'END', 'is_builtin': True})
        transitions.append({
            'from_state_id': prev_id, 'to_state_id': end_id,
            'name': '', 'condition_type': 'default', 'condition': {},
        })

        return {
            'workflow': {
                'name': description[:128],
                'itsm_type': itsm_type,
                'description': description,
            },
            'states': states,
            'transitions': transitions,
        }

    def _count_approval_levels(self, description: str) -> int:
        keywords = ['一级', '二级', '三级', '四级', '五级', '1级', '2级', '3级']
        for kw in keywords:
            if kw in description:
                num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                           '1': 1, '2': 2, '3': 3}
                for k, v in num_map.items():
                    if k in kw:
                        return v
        # Count approval keywords
        count = 0
        for kw in ['审批', '审核', '批准', 'approval']:
            if kw in description:
                count += description.count(kw)
        return max(count, 1)

    def _detect_approval_names(self, description: str) -> list:
        """检测审批节点名称和处理人类型"""
        levels = self._count_approval_levels(description)
        if '采购' in description:
            names = [('STARTER_LEADER', '主管审批'),
                     ('ROLE', '财务审批'),
                     ('ROLE', '总监审批')]
            return names[:levels or 3]
        if '紧急' in description or '故障' in description:
            return [('STARTER_LEADER', '值班主管审批')]
        # Default
        defaults = [('STARTER_LEADER', '直属主管审批'),
                    ('ROLE', '部门经理审批')]
        return defaults[:levels]

    def _detect_fields(self, itsm_type: str, description: str) -> list:
        """根据 ITSM 类型检测表单字段"""
        if itsm_type == 'change':
            return self.generate_fields('变更信息')
        if itsm_type == 'incident':
            return [
                {'key': 'title', 'name': '事件标题', 'type': 'STRING', 'required': True},
                {'key': 'severity', 'name': '严重级别', 'type': 'SELECT', 'required': True,
                 'choice': [{'label': '严重', 'value': 'critical'},
                            {'label': '高', 'value': 'high'},
                            {'label': '中', 'value': 'medium'},
                            {'label': '低', 'value': 'low'}]},
                {'key': 'description', 'name': '事件描述', 'type': 'TEXT', 'required': True},
            ]
        return self.generate_fields('基本信息')
