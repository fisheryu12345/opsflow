# -*- coding: utf-8 -*-
"""ITSM Ticket model — 工单运行时

Ticket: 工单实例，由 pipeline 驱动流转
TicketStatus: 节点运行时状态
SignTask: 会签/审批操作记录
"""

from django.db import models
from common.utils.models import CoreModel, table_prefix


def generate_sn():
    import datetime
    now = datetime.datetime.now()
    return f"ITSM{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"


class Ticket(CoreModel):
    """ITSM 工单 — pipeline 驱动的运行实例"""
    STATUS_CHOICES = (
        ('draft', '草稿'),
        ('assigned', '已分派'),
        ('receiving', '待认领'),
        ('running', '处理中'),
        ('escalated', '已升级'),
        ('suspended', '挂起'),
        ('finished', '已完成'),
        ('terminated', '已终止'),
        ('failed', '失败'),
    )
    ITSM_TYPE_CHOICES = (
        ('change', '变更申请'),
        ('incident', '事件工单'),
        ('request', '服务请求'),
        ('problem', '问题管理'),
    )
    PRIORITY_CHOICES = (
        ('P1', 'P1 危急'),
        ('P2', 'P2 高'),
        ('P3', 'P3 中'),
        ('P4', 'P4 低'),
    )
    project = models.ForeignKey(
        'iam.Project', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='itsm_tickets', verbose_name='Project',
    )
    sn = models.CharField(max_length=64, unique=True, default=generate_sn, verbose_name="单据号")
    title = models.CharField(max_length=255, verbose_name="工单标题")
    workflow_version = models.ForeignKey('itsm.WorkflowVersion', on_delete=models.CASCADE,
                                         related_name='tickets', verbose_name="流程版本")
    itsm_type = models.CharField(max_length=32, choices=ITSM_TYPE_CHOICES, default='change', verbose_name="服务类型")
    category = models.ForeignKey(
        'itsm.ServiceCategory', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="工单分类",
    )
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default='P3',
                                 verbose_name="优先级")
    urgency = models.CharField(max_length=16, blank=True, default='', verbose_name="紧急程度")
    impact = models.CharField(max_length=16, blank=True, default='', verbose_name="影响范围")
    current_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='draft',
                                       verbose_name="当前状态")
    pipeline_id = models.CharField(max_length=128, blank=True, default='', db_index=True,
                                   verbose_name="Pipeline ID")
    node_status = models.JSONField(default=dict, verbose_name="节点状态快照")
    business = models.ForeignKey(
        'iam.Business', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Business',
        help_text='Business line for tenant isolation / 业务线归属'
    )
    meta = models.JSONField(default=dict, verbose_name="扩展信息")
    state_history = models.JSONField(default=list, verbose_name="状态变更历史")

    class Meta:
        db_table = table_prefix + "itsm_ticket"
        verbose_name = "ITSM 工单"
        verbose_name_plural = verbose_name
        ordering = ['-create_datetime']

    def __str__(self):
        return f"{self.sn} {self.title}"

    def set_status(self, status, operator=''):
        """更新工单状态并记录历史"""
        self.current_status = status
        self.state_history = self.state_history or []
        self.state_history.append({
            'status': status,
            'operator': operator,
            'time': self.update_datetime.isoformat() if self.update_datetime else '',
        })
        self.save(update_fields=['current_status', 'state_history'])

    def get_state(self, state_id):
        """从 workflow_version 快照中获取节点数据
        支持按 dict key（node_key 或 id）和按 state['id'] / state['node_key'] 查找"""
        states = self.workflow_version.states or {}
        key = str(state_id)
        if key in states:
            return states[key]
        # Fallback: search by id or node_key field
        for s in states.values():
            if str(s.get('id')) == key or str(s.get('node_key')) == key:
                return s
        return {}

    def get_first_state(self):
        """获取提单节点"""
        for sid, state in self.workflow_version.states.items():
            if state.get('type') == 'NORMAL':
                return sid, state
        return None, None

    def do_before_enter_state(self, state_id, operator=''):
        """进入节点前处理"""
        state_data = self.get_state(state_id)
        if not state_data:
            return
        db_id = state_data.get('id', state_id)
        nk = state_data.get('node_key', '')
        processors_text = state_data.get('processors', '')
        TicketStatus.objects.update_or_create(
            ticket=self,
            state_id=int(db_id),
            defaults={
                'name': state_data.get('name', ''),
                'type': state_data.get('type', 'NORMAL'),
                'status': 'RUNNING',
                'processors': processors_text,
            }
        )
        node_status = self.node_status or {}
        # Use node_key as primary key for node_status (matches bamboo activity ID)
        key = nk or str(db_id)
        node_status[key] = {
            'status': 'RUNNING',
            'name': state_data.get('name', ''),
        }
        self.node_status = node_status
        self.save(update_fields=['node_status'])
        self.set_status('running', operator)

        # Notification: notify processors
        p_type = state_data.get('processors_type', 'PERSON')
        try:
            from itsm.services.notifications import NotificationService
            from itsm.services.role_resolver import resolve_processors
            resolved = resolve_processors(p_type, processors_text, self)
            if state_data.get('type') in ('APPROVAL', 'SIGN'):
                NotificationService.notify_approval(self, state_data.get('name', ''), resolved)
            else:
                NotificationService.notify_state_enter(self, state_data.get('name', ''), resolved)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f'Notify failed: {e}')

        # 将当前节点处理人同步到工单层 assignee（用于列表显示）
        self._sync_assignee_from_node(state_data, p_type, processors_text)

    def _sync_assignee_from_node(self, state_data, p_type, processors_text):
        """将节点 processors 解析结果写入 ticket.meta.assignee

        前端期待的格式: {'name': '张三', 'username': 'zhangsan', 'id': 1}
        resolve_processors 返回的是用户名列表，此处需转为前端格式。
        """
        try:
            from itsm.services.role_resolver import resolve_processors
            resolved = resolve_processors(p_type, processors_text, self)
            if not resolved:
                return
            # 取第一个处理人作为 assignee
            first = resolved[0]
            meta = dict(self.meta or {})
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(username=first)
                meta['assignee'] = {
                    'id': user.id,
                    'username': user.username,
                    'name': user.name or first,
                }
            except User.DoesNotExist:
                # 无法匹配用户时至少显示名称
                meta['assignee'] = {'name': first, 'username': first}
            self.meta = meta
            self.save(update_fields=['meta'])
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                'Sync assignee from node failed: %s', e
            )

    def do_in_state(self, state_id, fields_data, operator=''):
        """节点处理中 — 保存表单数据"""
        state_data = self.get_state(state_id)
        db_id = state_data.get('id', state_id) if state_data else state_id
        nk = state_data.get('node_key', '') if state_data else ''
        TicketStatus.objects.filter(ticket=self, state_id=int(db_id)).update(
            status='FINISHED',
            fields=fields_data,
        )
        node_status = self.node_status or {}
        key = nk or str(db_id)
        if key in node_status:
            node_status[key]['status'] = 'FINISHED'
        self.node_status = node_status
        self.save(update_fields=['node_status'])

    def do_before_exit_state(self, state_id, operator=''):
        """退出节点前处理"""
        pass

    def do_before_end_pipeline(self):
        """pipeline 结束处理"""
        try:
            from itsm.services.sla_engine import SlaEngine
            SlaEngine.stop_ticket_sla(self)
        except Exception:
            pass
        self.set_status('finished')

    def do_after_create(self, fields_data=None):
        """工单创建后初始化"""
        state_id, state_data = self.get_first_state()
        if state_id:
            # state_id may be node_key (str), use state_data['id'] for DB integer
            db_id = state_data.get('id', state_id)
            TicketStatus.objects.create(
                ticket=self,
                state_id=int(db_id),
                name=state_data.get('name', ''),
                type=state_data.get('type', 'NORMAL'),
                status='WAIT',
                processors=state_data.get('processors', ''),
            )

    def check_approval_finished(self, state_id):
        """检查会签/审批是否已完成"""
        state_data = self.get_state(state_id)
        if not state_data:
            return False  # state not found — cannot determine status
        if not state_data.get('is_multi'):
            return True
        finish_cond = state_data.get('finish_condition', {})
        cond_type = finish_cond.get('type', 'all')
        cond_value = finish_cond.get('value', 1)
        # Find TicketStatus by state_id, then look up SignTask by its pk
        status_record = TicketStatus.objects.filter(ticket=self, state_id=int(state_data.get('id', state_id))).first()
        total = SignTask.objects.filter(ticket=self, status=status_record).count() if status_record else 0
        passed = SignTask.objects.filter(ticket=self, status=status_record, status_val='passed').count() if status_record else 0
        if cond_type == 'percent':
            return total > 0 and (passed / total * 100) >= cond_value
        elif cond_type == 'count':
            return passed >= cond_value
        else:
            return total >= 1 and passed >= 1


class TicketStatus(CoreModel):
    """节点运行时状态 — 工单在每个节点上的实时状态"""
    STATUS_VALUES = (
        ('WAIT', '等待'),
        ('RUNNING', '处理中'),
        ('RECEIVING', '待认领'),
        ('FINISHED', '已完成'),
        ('FAILED', '失败'),
    )
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name='status_records', verbose_name="工单")
    state_id = models.IntegerField(verbose_name="节点 ID")
    name = models.CharField(max_length=128, verbose_name="节点名称")
    type = models.CharField(max_length=32, verbose_name="节点类型")
    status = models.CharField(max_length=16, choices=STATUS_VALUES, default='WAIT',
                               verbose_name="处理状态")
    processors = models.TextField(blank=True, default='', verbose_name="处理人")
    fields = models.JSONField(default=dict, verbose_name="表单数据")
    is_sequential = models.BooleanField(default=False, verbose_name="串行会签")
    distribute_type = models.CharField(max_length=32, default='PROCESS', verbose_name="分配方式")

    class Meta:
        db_table = table_prefix + "itsm_ticket_status"
        verbose_name = "节点状态"
        verbose_name_plural = verbose_name
        unique_together = [('ticket', 'state_id')]

    def __str__(self):
        return f"{self.ticket.sn} / {self.name} [{self.get_status_display()}]"


class SignTask(CoreModel):
    """会签/审批记录 — 每个审批人的操作"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE,
                               related_name='sign_tasks', verbose_name="工单")
    status = models.ForeignKey(TicketStatus, on_delete=models.CASCADE,
                               related_name='sign_tasks', verbose_name="节点状态")
    processor = models.CharField(max_length=64, verbose_name="处理人")
    order = models.IntegerField(default=0, verbose_name="顺序")
    status_val = models.CharField(max_length=16, default='pending', verbose_name="审批状态")
    comment = models.TextField(blank=True, default='', verbose_name="审批意见")

    class Meta:
        db_table = table_prefix + "itsm_sign_task"
        verbose_name = "会签记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.ticket.sn} / {self.processor} [{self.status_val}]"
