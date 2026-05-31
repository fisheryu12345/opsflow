"""变量解析引擎测试 — resolve_variables / resolve_with_type / resolve_params / build_execution_context"""

import pytest
from unittest.mock import Mock, patch
from opsflow.core.variable_resolver import (
    resolve_variables,
    split_value,
    resolve_with_type,
    resolve_params,
    _deep_get,
    get_variable_reference_details,
    build_execution_context,
)


class TestResolveVariables:
    """resolve_variables 核心替换逻辑"""

    def test_simple_key_replacement(self):
        result = resolve_variables("hello ${name}", {"name": "world"})
        assert result == "hello world"

    def test_multiple_replacements(self):
        result = resolve_variables("${a} + ${b} = ${c}", {"a": 1, "b": 2, "c": 3})
        assert result == "1 + 2 = 3"

    def test_dot_path_resolution(self):
        ctx = {"node_1": {"stdout": "hello", "rc": 0}}
        result = resolve_variables("${node_1.stdout}", ctx)
        assert result == "hello"

    def test_missing_key_preserved(self):
        result = resolve_variables("${missing_key}", {"other": "val"})
        assert result == "${missing_key}"

    def test_no_variable_pattern(self):
        result = resolve_variables("plain text", {"a": "b"})
        assert result == "plain text"

    def test_empty_string(self):
        result = resolve_variables("", {"a": "b"})
        assert result == ""

    def test_none_template(self):
        result = resolve_variables(None, {"a": "b"})
        assert result is None

    def test_deep_nested_path(self):
        ctx = {"x": {"y": {"z": "deep_value"}}}
        result = resolve_variables("${x.y.z}", ctx)
        assert result == "deep_value"

    def test_string_without_dollar_brace(self):
        result = resolve_variables("just $money", {"money": "100"})
        assert result == "just $money"  # 没有 {} 不替换

    def test_target_hosts_context(self,):
        ctx = {"target_hosts": ["host1", "host2"]}
        result = resolve_variables("deploy to ${target_hosts}", ctx)
        # target_hosts 是 list, str() 后是 "['host1', 'host2']"
        assert "host1" in result

    def test_partial_missing(self):
        result = resolve_variables("${a} and ${b}", {"a": 1})
        assert result == "1 and ${b}"


class TestSplitValue:
    """split_value 字符串分割"""

    def test_comma_delimiter(self):
        assert split_value("a,b,c") == ["a", "b", "c"]

    def test_with_spaces(self):
        assert split_value(" a , b , c ") == ["a", "b", "c"]

    def test_empty_string(self):
        assert split_value("") == []

    def test_single_item(self):
        assert split_value("single") == ["single"]

    def test_none_input(self):
        assert split_value(None) == []

    def test_list_input_passthrough(self):
        assert split_value(["a", "b", "c"]) == ["a", "b", "c"]

    def test_custom_delimiter(self):
        assert split_value("a|b|c", delimiter="|") == ["a", "b", "c"]


class TestResolveWithType:
    """resolve_with_type 按类型解析"""

    def test_plain_returns_as_is(self):
        result = resolve_with_type("${key}", "plain", {"key": "val"})
        assert result == "${key}"

    def test_splice_replaces_variables(self):
        result = resolve_with_type("hello ${name}", "splice", {"name": "world"})
        assert result == "hello world"

    def test_split_returns_list(self):
        result = resolve_with_type("a,b,c", "split", {"x": "y"})
        assert result == ["a", "b", "c"]

    def test_lazy_calls_resolver(self):
        resolver = MockResolver()
        result = resolve_with_type("raw", "lazy", {"a": 1}, lazy_resolver=resolver.resolve)
        assert resolver.called_with == ("raw", {"a": 1})
        assert result == "lazy_result"

    def test_splice_no_var_passthrough(self):
        result = resolve_with_type("no variables", "splice", {"a": "b"})
        assert result == "no variables"

    def test_plain_with_variable(self):
        """plain 类型不做替换"""
        result = resolve_with_type("${ignore_me}", "plain", {"ignore_me": "val"})
        assert result == "${ignore_me}"


class MockResolver:
    def __init__(self):
        self.called_with = None

    def resolve(self, value, context):
        self.called_with = (value, context)
        return "lazy_result"


class TestResolveParams:
    """resolve_params 递归参数解析"""

    def test_flat_dict(self):
        result = resolve_params({"host": "${ip}", "port": 8080}, {"ip": "10.0.0.1"})
        assert result == {"host": "10.0.0.1", "port": 8080}

    def test_nested_dict(self):
        result = resolve_params(
            {"server": {"host": "${ip}", "port": 8080}},
            {"ip": "10.0.0.1"},
        )
        assert result == {"server": {"host": "10.0.0.1", "port": 8080}}

    def test_list_with_variables(self):
        result = resolve_params(
            {"hosts": ["${host1}", "${host2}"]},
            {"host1": "10.0.0.1", "host2": "10.0.0.2"},
        )
        assert result == {"hosts": ["10.0.0.1", "10.0.0.2"]}

    def test_mixed_types(self):
        result = resolve_params(
            {"name": "${n}", "count": 42, "active": True, "tags": ["${t}"]},
            {"n": "test", "t": "tag1"},
        )
        assert result == {"name": "test", "count": 42, "active": True, "tags": ["tag1"]}

    def test_with_var_types_plain(self):
        result = resolve_params(
            {"dont_touch": "${keep}"},
            {"keep": "changed"},
            var_types={"dont_touch": "plain"},
        )
        assert result == {"dont_touch": "${keep}"}  # plain 类型不做替换

    def test_with_var_types_split(self):
        result = resolve_params(
            {"hosts": "a,b,c"},
            {},
            var_types={"hosts": "split"},
        )
        assert result == {"hosts": ["a", "b", "c"]}

    def test_with_var_types_lazy(self):
        lazy = MockResolver()
        result = resolve_params(
            {"val": "test"},
            {"x": 1},
            var_types={"val": "lazy"},
            lazy_resolver=lazy.resolve,
        )
        assert result["val"] == "lazy_result"
        assert lazy.called_with == ("test", {"x": 1})

    def test_empty_dict(self):
        assert resolve_params({}, {"a": 1}) == {}

    def test_none_values(self):
        result = resolve_params({"key": None}, {"a": 1})
        assert result["key"] is None


class TestDeepGet:
    """_deep_get 嵌套路径查找"""

    def test_simple_key(self):
        assert _deep_get({"a": 1}, "a") == 1

    def test_nested_two_levels(self):
        assert _deep_get({"a": {"b": 2}}, "a.b") == 2

    def test_nested_three_levels(self):
        assert _deep_get({"a": {"b": {"c": 3}}}, "a.b.c") == 3

    def test_missing_key_returns_none(self):
        assert _deep_get({"a": 1}, "b") is None

    def test_partial_path_returns_none(self):
        assert _deep_get({"a": 1}, "a.b") is None

    def test_non_dict_mid_path(self):
        assert _deep_get({"a": "string"}, "a.b") is None


class TestBuildExecutionContext:
    """build_execution_context 上下文构建 (mock execution)"""

    def _make_mock_execution(self, **snapshot_overrides):
        """创建 Mock execution 避免数据库"""
        template = Mock(spec=["name", "hook_variables"])
        template.name = "test"
        template.hook_variables = {}
        exec_mock = Mock(spec=["id", "template", "template_snapshot"])
        exec_mock.id = 999
        exec_mock.template = template
        exec_mock.template_snapshot = {
            "global_vars": {},
            "target_hosts": [],
            **snapshot_overrides,
        }
        return exec_mock

    def test_global_vars_included(self):
        exec_mock = self._make_mock_execution(global_vars={"key": "val"})
        with patch("opsflow.models.NodeExecutionTrace") as mock_trace:
            mock_trace.objects.filter.return_value.exclude.return_value.values.return_value = []
            ctx = build_execution_context(exec_mock)
            assert ctx["key"] == "val"

    def test_target_hosts_included(self):
        exec_mock = self._make_mock_execution(target_hosts=["h1", "h2"])
        with patch("opsflow.models.NodeExecutionTrace") as mock_trace:
            mock_trace.objects.filter.return_value.exclude.return_value.values.return_value = []
            ctx = build_execution_context(exec_mock)
            assert ctx["target_hosts"] == ["h1", "h2"]

    def test_node_outputs_included(self):
        exec_mock = self._make_mock_execution()
        fake_traces = [
            {"node_id": "node_1", "outputs": {"stdout": "hello"}},
        ]
        with patch("opsflow.models.NodeExecutionTrace") as mock_trace:
            mock_trace.objects.filter.return_value.exclude.return_value.values.return_value = fake_traces
            ctx = build_execution_context(exec_mock)
            assert ctx["node_1"]["stdout"] == "hello"

    def test_empty_template_snapshot(self):
        exec_mock = self._make_mock_execution()
        with patch("opsflow.models.NodeExecutionTrace") as mock_trace:
            mock_trace.objects.filter.return_value.exclude.return_value.values.return_value = []
            ctx = build_execution_context(exec_mock)
            assert isinstance(ctx, dict)


class TestGetVariableReferenceDetails:
    """get_variable_reference_details — 变量引用明细追踪"""

    def test_single_reference(self):
        tree = {
            "nodes": [
                {"id": "node_1", "node_type": "atom", "label": "SSH",
                 "params": {"command": "${my_var} -h", "host": "localhost"}},
            ],
            "edges": [],
        }
        refs = get_variable_reference_details(tree, "my_var")
        assert len(refs) == 1
        assert refs[0]["node_id"] == "node_1"
        assert refs[0]["node_label"] == "SSH"
        assert "params.command" in refs[0]["field_path"]
        assert "${my_var}" in refs[0]["message"]

    def test_multiple_references(self):
        tree = {
            "nodes": [
                {"id": "n1", "label": "Node1", "params": {"cmd": "${x} start", "args": "-a ${x}"}},
                {"id": "n2", "label": "Node2", "params": {"script": "run ${x}"}},
            ],
            "edges": [],
        }
        refs = get_variable_reference_details(tree, "x")
        assert len(refs) == 3  # 两次在 n1, 一次在 n2

    def test_no_reference(self):
        tree = {
            "nodes": [
                {"id": "n1", "label": "Node1", "params": {"cmd": "echo hello"}},
            ],
            "edges": [],
        }
        refs = get_variable_reference_details(tree, "my_var")
        assert refs == []

    def test_empty_tree(self):
        assert get_variable_reference_details({}, "x") == []
        assert get_variable_reference_details(None, "x") == []

    def test_nested_config_refs(self):
        """node_config 中的引用也应检出"""
        tree = {
            "nodes": [
                {"id": "n1", "node_type": "atom", "label": "HTTP",
                 "params": {"url": "http://example.com"},
                 "node_config": {"headers": {"Authorization": "Bearer ${token}"}}},
            ],
            "edges": [],
        }
        refs = get_variable_reference_details(tree, "token")
        assert len(refs) == 1
        assert "node_config" in refs[0]["field_path"]
