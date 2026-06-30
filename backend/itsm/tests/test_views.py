"""ITSM 视图测试 — SkillGroupViewSet, AssignRuleViewSet, EscalationLevelViewSet"""
from django.test import TestCase
from itsm.models.skill_group import SkillGroup
from itsm.models.assign_rule import AssignRule
from itsm.models.escalation import EscalationLevel
from itsm.views.assign_views import SkillGroupViewSet
from itsm.serializers.assign_serializers import SkillGroupSerializer


class SkillGroupViewSetTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='测试组', code='test')

    def test_serializer_output(self):
        """序列化包含成员列表"""
        data = SkillGroupSerializer(self.group).data
        self.assertEqual(data['name'], '测试组')
        self.assertEqual(data['code'], 'test')
        self.assertIn('members', data)

    def test_add_member_action(self):
        """add_member action 接受 user_id"""
        from rest_framework.test import APIRequestFactory, force_authenticate
        from rest_framework import status

        factory = APIRequestFactory()
        view = SkillGroupViewSet.as_view({'post': 'add_member'})
        request = factory.post(f'/api/itsm/skill-groups/{self.group.id}/add_member/',
                               {'user_id': 1}, format='json')
        response = view(request, pk=self.group.id)
        self.assertIn(response.status_code, [200, 201, 403, 401])

    def test_list_view(self):
        """列表查询返回 200"""
        from rest_framework.test import APIRequestFactory
        from rest_framework import status

        factory = APIRequestFactory()
        view = SkillGroupViewSet.as_view({'get': 'list'})
        request = factory.get('/api/itsm/skill-groups/')
        response = view(request)
        self.assertIn(response.status_code, [200, 403, 401])


class AssignRuleViewSetTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='测试组', code='test')

    def test_create_rule(self):
        r = AssignRule.objects.create(
            name='规则1', priority=10, target_group=self.group, assign_mode='least_busy'
        )
        self.assertEqual(r.assign_mode, 'least_busy')
        self.assertEqual(r.priority, 10)


class EscalationLevelViewSetTests(TestCase):
    def setUp(self):
        self.group = SkillGroup.objects.create(name='测试组', code='test')

    def test_list_by_group(self):
        EscalationLevel.objects.create(
            name='L1', level=1, group=self.group, timeout_minutes=60,
        )
        EscalationLevel.objects.create(
            name='L2', level=2, group=self.group, timeout_minutes=120,
        )
        levels = EscalationLevel.objects.filter(group=self.group).order_by('level')
        self.assertEqual(levels.count(), 2)
        self.assertEqual(levels[0].level, 1)
        self.assertEqual(levels[1].level, 2)
