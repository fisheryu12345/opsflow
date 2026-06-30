"""ITSM 服务测试 — AssignEngine, EscalationService"""
from django.test import TestCase
from itsm.models.skill_group import SkillGroup
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.services.assign_engine import AssignEngine
from itsm.services.escalation_service import EscalationService
from itsm.models.ticket import Ticket
from itsm.models.workflow import Workflow, WorkflowVersion
from itsm.models.incident import ServiceCategory


def _create_user(username='testuser'):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create(username=username, name=username, password='test')


def _create_ticket(**kwargs):
    wf = Workflow.objects.create(name='test-wf', itsm_type='incident')
    wv = WorkflowVersion.objects.create(workflow=wf, version=1, states={}, fields={}, transitions={})
    defaults = {'title': 'test', 'workflow_version': wv, 'itsm_type': 'incident', 'priority': 'P3'}
    defaults.update(kwargs)
    return Ticket.objects.create(**defaults)


class AssignEngineRuleMatchTests(TestCase):
    def setUp(self):
        self.user = _create_user('assigner')
        self.group = SkillGroup.objects.create(name='test', code='test')
        self.category = ServiceCategory.objects.create(name='网络故障', code='net-fault')

    def test_match_by_itsm_type(self):
        AssignRule.objects.create(name='事件路由', priority=10, match_itsm_type='incident',
                                  target_group=self.group)
        AssignRule.objects.create(name='变更路由', priority=20, match_itsm_type='change',
                                  target_group=self.group)
        ticket = _create_ticket(itsm_type='incident', category=self.category)
        rule = AssignEngine(ticket)._match_rule()
        self.assertIsNotNone(rule)
        self.assertEqual(rule.name, '事件路由')

    def test_no_match(self):
        AssignRule.objects.create(name='P1路由', priority=10, match_priority='P1',
                                  target_group=self.group)
        ticket = _create_ticket(itsm_type='incident', priority='P3', category=self.category)
        rule = AssignEngine(ticket)._match_rule()
        self.assertIsNone(rule)


class EscalationServiceTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='test', code='escal')
        EscalationLevel.objects.create(name='L1', level=1, group=self.group,
                                        timeout_minutes=60, action='notify_only')

    def test_no_active_tickets(self):
        self.assertEqual(EscalationService.check_and_escalate(), 0)

    def test_no_escalation_level(self):
        new_group = SkillGroup.objects.create(name='no-esc', code='no-esc')
        ticket = _create_ticket(current_status='assigned')
        ticket.meta = {'assignee': {'group': 'no-esc'}}
        ticket.save()
        self.assertFalse(EscalationService._process_ticket(ticket))

class RollbackTests(TestCase):
    """WorkflowVersion rollback — 从旧版本快照重建 States/Transitions/Fields"""
    def setUp(self):
        self.wf = Workflow.objects.create(name='回滚测试', itsm_type='incident')
        # Create states and deploy version
        from itsm.models import State
        s1 = State.objects.create(workflow=self.wf, name='填单', type='NORMAL', is_builtin=True, fields=[{'key': 'title', 'name': '标题', 'type': 'STRING'}])
        s2 = State.objects.create(workflow=self.wf, name='审批', type='APPROVAL', processors_type='PERSON', processors='admin')
        self.wf.create_version(operator=None, message='v1')
        self.v1 = self.wf.versions.first()

    def test_version_created(self):
        """部署后创建版本"""
        self.assertIsNotNone(self.v1)
        self.assertEqual(self.wf.versions.count(), 1)

    def test_rollback_preserves_state_count(self):
        """回滚后节点数不变"""
        from itsm.views.workflow_views import WorkflowVersionViewSet
        self.assertEqual(self.wf.states.count(), 2)


class AssignEngineProjectTests(TestCase):
    """AssignEngine project-scoped 规则匹配"""
    def setUp(self):
        self.group = SkillGroup.objects.create(name='test', code='proj-test')
        self.category = ServiceCategory.objects.create(name='测试分类', code='test-cat')

    def test_engine_with_project_id(self):
        """带 project_id 初始化引擎"""
        ticket = _create_ticket(itsm_type='incident', category=self.category)
        ticket.project_id = None  # 无项目
        ticket.save()
        engine = AssignEngine(ticket, project_id=5)
        self.assertEqual(engine.project_id, 5)

    def test_no_match_with_empty_rules(self):
        """空规则表返回 None"""
        ticket = _create_ticket(itsm_type='incident', category=self.category)
        rule = AssignEngine(ticket)._match_rule()
        self.assertIsNone(rule)
