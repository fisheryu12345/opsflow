"""Mako 模板变量解析测试"""

from django.test import SimpleTestCase
from opsflow.core.mako_resolver import MakoResolver, resolve_with_mako


class TestMakoResolver(SimpleTestCase):
    def setup_method(self):
        self.resolver = MakoResolver()

    def test_simple_variable(self):
        result = self.resolver.resolve("#{ name }", {"name": "world"})
        assert result == "world"

    def test_expression(self):
        result = self.resolver.resolve("#{ 'hello ' + name }", {"name": "world"})
        assert result == "hello world"

    def test_numeric_expression(self):
        result = self.resolver.resolve("#{ a + b }", {"a": 1, "b": 2})
        assert str(result).strip() == "3"

    def test_list_comprehension(self):
        result = self.resolver.resolve("#{ [x * 2 for x in items] }", {"items": [1, 2, 3]})
        assert str(result).strip() == "[2, 4, 6]"

    def test_no_mako_syntax(self):
        """不含 #{} 的字符串原样返回"""
        result = self.resolver.resolve("${name}", {"name": "world"})
        assert result == "${name}"  # 原样返回，由上游 ${key} 处理

    def test_empty_string(self):
        assert self.resolver.resolve("", {"x": 1}) == ""
        assert self.resolver.resolve(None, {"x": 1}) is None

    def test_security_blocked_import(self):
        """安全沙箱阻止恶意导入 — 识别到 __import__ 时原样返回"""
        result = self.resolver.resolve("#{ __import__('os').system('whoami') }", {})
        # 应原样返回（不渲染），且不抛异常
        assert result.startswith("#{")

    def test_security_blocked_eval(self):
        """安全沙箱阻止 eval — 识别到 eval( 时原样返回"""
        result = self.resolver.resolve("#{ eval('1+1') }", {})
        assert result.startswith("#{")  # 原样返回，不会抛异常

    def test_resolve_with_mako_entrypoint(self):
        """resolve_with_mako 通用入口"""
        result = resolve_with_mako("#{ var }", {"var": "test"})
        assert result == "test"

        # 不含 #{} 直接返回
        result2 = resolve_with_mako("${other}", {})
        assert result2 == "${other}"
