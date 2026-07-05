"""ITSM 模型测试"""
from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError
from itsm.models.skill_group import SkillGroup, OnDutySchedule
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.models.transfer_log import TicketTransferLog
from itsm.models.ticket import Ticket
from itsm.models.workflow import Workflow, WorkflowVersion
from itsm.models.state import State
from itsm.models.transition import Transition
from itsm.models.sla import SlaTask


def _create_user(username='testuser'):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create(username=username, name=username, password='test')


def _create_ticket(**kwargs):
    """创建测试 Ticket，自动创建 Workflow + WorkflowVersion"""
    wf = Workflow.objects.create(name='test-wf', itsm_type='incident')
    wv = WorkflowVersion.objects.create(workflow=wf, version=1, states={}, fields={}, transitions={})
    defaults = {'title': 'test', 'workflow_version': wv, 'itsm_type': 'incident', 'priority': 'P3'}
    defaults.update(kwargs)
    return Ticket.objects.create(**defaults)


class SkillGroupTests(TestCase):
    def test_create(self):
        g = SkillGroup.objects.create(name='网络组', code='net')
        self.assertTrue(g.is_active)

    def test_code_unique(self):
        SkillGroup.objects.create(name='a', code='net')
        with self.assertRaises(IntegrityError):
            SkillGroup.objects.create(name='b', code='net')

    def test_leader_nullable(self):
        g = SkillGroup.objects.create(name='a', code='x')
        self.assertIsNone(g.leader)


class OnDutyScheduleTests(TestCase):
    def setUp(self):
        self.user = _create_user('onduty')
        self.group = SkillGroup.objects.create(name='a', code='b')

    def test_create(self):
        from datetime import date
        d = OnDutySchedule.objects.create(
            group=self.group, user=self.user, duty_date=date.today(), duty_type='primary'
        )
        self.assertEqual(d.duty_type, 'primary')

    def test_unique_together(self):
        from datetime import date
        OnDutySchedule.objects.create(
            group=self.group, user=self.user, duty_date=date.today(), duty_type='primary'
        )
        with self.assertRaises(IntegrityError):
            OnDutySchedule.objects.create(
                group=self.group, user=self.user, duty_date=date.today(), duty_type='primary'
            )


class AssignRuleTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='a', code='c')

    def test_defaults(self):
        r = AssignRule.objects.create(name='r', target_group=self.group)
        self.assertEqual(r.priority, 100)
        self.assertEqual(r.assign_mode, 'to_onduty')

    def test_ordering(self):
        AssignRule.objects.create(name='r2', priority=200, target_group=self.group)
        AssignRule.objects.create(name='r1', priority=50, target_group=self.group)
        rules = list(AssignRule.objects.all())
        self.assertEqual(rules[0].name, 'r1')


class EscalationLevelTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='a', code='d')

    def test_create(self):
        e = EscalationLevel.objects.create(
            name='L1', level=1, group=self.group, timeout_minutes=60, action='transfer_to_next_level'
        )
        self.assertEqual(e.level, 1)

    def test_unique(self):
        EscalationLevel.objects.create(name='L1', level=1, group=self.group, timeout_minutes=60)
        with self.assertRaises(IntegrityError):
            EscalationLevel.objects.create(name='L1b', level=1, group=self.group, timeout_minutes=120)


class TicketTransferLogTests(TestCase):
    def setUp(self):
        self.user = _create_user('transfer')
        self.group = SkillGroup.objects.create(name='a', code='e')
        self.ticket = _create_ticket()

    def test_create(self):
        t = TicketTransferLog.objects.create(
            ticket=self.ticket, to_user=self.user, to_group=self.group, transfer_type='auto_assign', reason='x'
        )
        self.assertEqual(t.transfer_type, 'auto_assign')

    def test_default_type(self):
        t = TicketTransferLog.objects.create(
            ticket=self.ticket, to_user=self.user, to_group=self.group, reason='x'
        )
        self.assertEqual(t.transfer_type, 'manual')


class TicketStatusChoicesTests(TestCase):
    def test_new_statuses(self):
        choices = dict(Ticket.STATUS_CHOICES)
        self.assertIn('assigned', choices)
        self.assertIn('receiving', choices)
        self.assertIn('escalated', choices)

    def test_category_field(self):
        fields = {f.name for f in Ticket._meta.get_fields()}
        self.assertIn('category', fields)


class StateNodeKeyTests(TestCase):
    def setUp(self):
        self.wf = Workflow.objects.create(name='nodekey-wf', itsm_type='change')

    def test_node_key_unique_per_workflow(self):
        State.objects.create(workflow=self.wf, name='开始', type='START', node_key='start_1')
        with self.assertRaises(IntegrityError):
            State.objects.create(workflow=self.wf, name='开始2', type='START', node_key='start_1')

    def test_node_key_allowed_across_workflows(self):
        wf2 = Workflow.objects.create(name='wf2', itsm_type='change')
        State.objects.create(workflow=self.wf, name='s1', type='NORMAL', node_key='n1')
        # Same node_key in different workflow should work
        State.objects.create(workflow=wf2, name='s2', type='NORMAL', node_key='n1')

    def test_node_key_nullable(self):
        s = State.objects.create(workflow=self.wf, name='无标识', type='NORMAL')
        self.assertIsNone(s.node_key)


class TransitionNodeKeyTests(TestCase):
    def setUp(self):
        self.wf = Workflow.objects.create(name='trans-wf', itsm_type='change')
        self.from_state = State.objects.create(workflow=self.wf, name='a', type='NORMAL', node_key='a')
        self.to_state = State.objects.create(workflow=self.wf, name='b', type='NORMAL', node_key='b')

    def test_create_with_node_keys(self):
        t = Transition.objects.create(
            workflow=self.wf, from_state=self.from_state, to_state=self.to_state,
            from_node_key='a', to_node_key='b',
        )
        self.assertEqual(t.from_node_key, 'a')
        self.assertEqual(t.to_node_key, 'b')

    def test_node_keys_nullable(self):
        t = Transition.objects.create(workflow=self.wf, from_state=self.from_state, to_state=self.to_state)
        self.assertIsNone(t.from_node_key)


class WorkflowCreateVersionNodeKeyTests(TestCase):
    def setUp(self):
        self.wf = Workflow.objects.create(name='ver-wf', itsm_type='change')

    def test_version_uses_node_key_as_key(self):
        s1 = State.objects.create(workflow=self.wf, name='审批', type='APPROVAL', node_key='approve_1')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(username='tester', name='tester', password='x')
        version = self.wf.create_version(operator=user.id)
        self.assertIn('approve_1', version.states)
        state_data = version.states['approve_1']
        self.assertEqual(state_data['name'], '审批')

    def test_version_has_start_end_safety_net(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(username='tester2', name='tester2', password='x')
        version = self.wf.create_version(operator=user.id)
        self.assertIn('__start__', version.states)
        self.assertIn('__end__', version.states)

    def test_version_includes_node_key_in_snapshot(self):
        s = State.objects.create(workflow=self.wf, name='填单', type='NORMAL', node_key='fill_1')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create(username='tester3', name='tester3', password='x')
        version = self.wf.create_version(operator=user.id)
        state_data = version.states['fill_1']
        self.assertEqual(state_data['node_key'], 'fill_1')


class SlaTaskPausedAtTests(TestCase):
    def setUp(self):
        self.ticket = _create_ticket()

    def test_paused_at_field_exists(self):
        task = SlaTask.objects.create(
            ticket=self.ticket,
            deadline='2026-07-06 00:00:00+00:00',
            task_status='running',
        )
        self.assertIsNone(task.paused_at)

    def test_paused_at_updated(self):
        from django.utils import timezone
        now = timezone.now()
        task = SlaTask.objects.create(
            ticket=self.ticket,
            deadline=now + timezone.timedelta(hours=1),
            task_status='paused',
            paused_at=now,
        )
        self.assertIsNotNone(task.paused_at)
