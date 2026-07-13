"""ItsmAutoTaskService 测试 — 变量解析与调度判定"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from itsm.pipeline_plugins.components import ItsmAutoTaskService


def _stub_ticket(**over):
    """构造一个满足 _resolve_vars 读取属性的最小 ticket 桩对象"""
    base = dict(
        id=42, sn='ITSM-42', title='T', itsm_type='change',
        priority='P1', creator=7, status='running', meta={},
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestResolveVars(SimpleTestCase):
    """_resolve_vars: 静态变量映射 + 运行时表单字段合并"""

    def test_static_context_substitution(self):
        """${ticket_id} 等上下文占位符被替换为工单属性"""
        extras = {'opsflow_variable_mapping': {'tid': '${ticket_id}', 'sn': 'x-${ticket_sn}'}}
        out = ItsmAutoTaskService._resolve_vars(extras, {}, _stub_ticket())
        self.assertEqual(out['tid'], '42')
        self.assertEqual(out['sn'], 'x-ITSM-42')

    def test_non_string_mapping_passthrough(self):
        """非字符串 mapping 值原样透传，不会抛 TypeError"""
        extras = {'opsflow_variable_mapping': {'n': 10, 'lst': [1, 2], 'obj': {'a': 1}}}
        out = ItsmAutoTaskService._resolve_vars(extras, {}, _stub_ticket())
        self.assertEqual(out['n'], 10)
        self.assertEqual(out['lst'], [1, 2])
        self.assertEqual(out['obj'], {'a': 1})

    def test_form_fields_override_and_field_context(self):
        """提交的 form_fields 覆盖静态值，并可通过 ${field.X} 引用"""
        extras = {'opsflow_variable_mapping': {'msg': 'hi ${field.name}', 'name': 'static'}}
        form = {'name': 'alice'}
        out = ItsmAutoTaskService._resolve_vars(extras, form, _stub_ticket())
        # ${field.name} 用刚提交的值
        self.assertEqual(out['msg'], 'hi alice')
        # 同名 key 被 form_fields 覆盖
        self.assertEqual(out['name'], 'alice')

    def test_unknown_placeholder_kept_literal(self):
        """未知占位符保持原样，不报错"""
        extras = {'opsflow_variable_mapping': {'x': '${nope}'}}
        out = ItsmAutoTaskService._resolve_vars(extras, {}, _stub_ticket())
        self.assertEqual(out['x'], '${nope}')


class TestNeedSchedule(SimpleTestCase):
    """need_schedule: 无模板自动完成的节点不进调度"""

    def test_default_needs_schedule(self):
        svc = ItsmAutoTaskService()
        self.assertTrue(svc.need_schedule())

    def test_auto_completed_skips_schedule(self):
        svc = ItsmAutoTaskService()
        svc._auto_completed = True
        self.assertFalse(svc.need_schedule())
