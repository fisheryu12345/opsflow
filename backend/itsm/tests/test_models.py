"""ITSM 模型测试"""
from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError
from itsm.models.skill_group import SkillGroup, OnDutySchedule
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.models.transfer_log import TicketTransferLog
from itsm.models.ticket import Ticket
from itsm.models.workflow import Workflow, WorkflowVersion


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
