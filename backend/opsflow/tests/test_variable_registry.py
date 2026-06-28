"""变量注册表测试 — RegisterVariableMeta 自动注册 + VariableLibrary 检索"""

from django.test import TestCase

# 导入变量类型包触发注册
from opsflow.core import variable_types  # noqa: F401
from opsflow.core.variable_registry import VARIABLE_REGISTRY, VariableLibrary, SpliceVariable, LazyVariable


class TestVariableRegistry(TestCase):
    """RegisterVariableMeta 自动注册"""

    def test_registry_contains_common_types(self):
        """VARIABLE_REGISTRY 应包含所有通用变量类型"""
        required = ["input", "textarea", "int", "float", "datetime",
                    "date", "time", "password", "select",
                    "text_value_select", "datatable", "ip_selector",
                    "current_time", "format_support_current_time"]
        for code in required:
            assert code in VARIABLE_REGISTRY, f"缺少变量类型: {code}"

    def test_registry_has_correct_count(self):
        assert len(VARIABLE_REGISTRY) >= 14

    def test_each_variable_has_required_attrs(self):
        for code, klass in VARIABLE_REGISTRY.items():
            assert klass.code, f"{code} 缺少 code"
            assert klass.name, f"{code} 缺少 name"
            assert klass.tag, f"{code} 缺少 tag"
            assert klass.type in ("general", "meta", "dynamic"), f"{code} type 无效"


class TestVariableLibrary(TestCase):
    """VariableLibrary 检索和解析"""

    def test_get_var_class_returns_class(self):
        klass = VariableLibrary.get_var_class("input")
        assert klass is not None
        assert klass.code == "input"

    def test_get_var_returns_instance(self):
        var = VariableLibrary.get_var("input", value="hello")
        assert var is not None
        assert var.get_value() == "hello"

    def test_resolve_simple_value(self):
        result = VariableLibrary.resolve("input", "test_value")
        assert result == "test_value"

    def test_resolve_unknown_code_returns_value(self):
        result = VariableLibrary.resolve("nonexistent_code", "original")
        assert result == "original"

    def test_get_all_variables_returns_summary(self):
        all_vars = VariableLibrary.get_all_variables()
        assert "input" in all_vars
        assert all_vars["input"]["type"] == "general"

    def test_get_by_tag(self):
        klass = VariableLibrary.get_by_tag("input.input")
        assert klass is not None
        assert klass.code == "input"

    def test_get_by_meta_tag(self):
        klass = VariableLibrary.get_by_tag("select.select_meta")
        assert klass is not None
        assert klass.code == "select"


class TestLazyVariable(TestCase):
    """LazyVariable get_value() 自定义转换"""

    def test_password_passthrough(self):
        var = VariableLibrary.get_var("password", value="secret123")
        assert var is not None
        assert var.get_value() == "secret123"

    def test_current_time_returns_string(self):
        var = VariableLibrary.get_var("current_time")
        assert var is not None
        result = var.get_value()
        assert isinstance(result, str)
        assert len(result) >= 16  # "2026-06-01 01:23:45"

    def test_format_support_current_time(self):
        var = VariableLibrary.get_var("format_support_current_time",
                                      value="%Y")
        assert var is not None
        result = var.get_value()
        assert result == "2026"

    def test_int_variable_passthrough(self):
        var = VariableLibrary.get_var("int", value=42)
        assert var is not None
        assert var.get_value() == 42

    def test_select_split_string(self):
        var = VariableLibrary.get_var("select", value="a,b,c")
        assert var is not None
        result = var.get_value()
        assert isinstance(result, list)
        assert result == ["a", "b", "c"]

    def test_select_single_value(self):
        var = VariableLibrary.get_var("select", value="single")
        assert var is not None
        result = var.get_value()
        assert result == "single"

    def test_select_none_value(self):
        var = VariableLibrary.get_var("select", value=None)
        assert var is not None
        assert var.get_value() is None
