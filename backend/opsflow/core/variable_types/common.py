"""通用变量类型 — 适配自 bk_sops pipeline_plugins.variables.collections.common

所有变量类继承 SpliceVariable 或 LazyVariable，创建时通过 RegisterVariableMeta
自动注册到 VARIABLE_REGISTRY。
"""

import re
from datetime import datetime, date, time, timedelta

from opsflow.core.variable_registry import SpliceVariable, LazyVariable


# =============================================================================
# General 类型 — 简单值变量
# =============================================================================

class InputVariable(SpliceVariable):
    """文本输入变量"""
    code = "input"
    name = "文本输入"
    type = "general"
    tag = "input.input"
    description = "单行文本输入"


class TextareaVariable(SpliceVariable):
    """多行文本变量"""
    code = "textarea"
    name = "多行文本"
    type = "general"
    tag = "textarea.textarea"
    description = "多行文本输入"


class IntVariable(SpliceVariable):
    """整数变量"""
    code = "int"
    name = "整数"
    type = "general"
    tag = "int.int"
    description = "整数值输入"


class FloatVariable(SpliceVariable):
    """浮点数变量"""
    code = "float"
    name = "浮点数"
    type = "general"
    tag = "float.float"
    description = "浮点数值输入"


class DatetimeVariable(SpliceVariable):
    """日期时间变量"""
    code = "datetime"
    name = "日期时间"
    type = "general"
    tag = "datetime.datetime"
    description = "日期时间选择器"


class DateVariable(SpliceVariable):
    """日期变量"""
    code = "date"
    name = "日期"
    type = "general"
    tag = "date.date"
    description = "日期选择器"


class TimeVariable(SpliceVariable):
    """时间变量"""
    code = "time"
    name = "时间"
    type = "general"
    tag = "time.time"
    description = "时间选择器"


class PasswordVariable(LazyVariable):
    """密码变量 — LazyVariable 确保不在日志中明文输出"""
    code = "password"
    name = "密码"
    type = "general"
    tag = "password.password"
    description = "加密密码输入（运行时解析）"

    def get_value(self):
        # 密码类型：保持值不变但标记为敏感（日志脱敏依赖上层处理）
        return self.value


# =============================================================================
# Meta 类型 — 有元数据配置的变量
# =============================================================================

class SelectVariable(SpliceVariable):
    """下拉选择变量 — 单选或逗号分隔多选

    元数据(meta_tag=select.select_meta)定义选项列表:
      [{"label": "选项A", "value": "a"}, {"label": "选项B", "value": "b"}]
    值可以是单值或逗号分隔的多值:
      "a" 或 "a,b"
    """
    code = "select"
    name = "下拉框"
    type = "meta"
    tag = "select.select"
    meta_tag = "select.select_meta"
    description = "下拉选择框，支持单选和多选"

    def get_value(self):
        if not self.value:
            return self.value
        # 如果是字符串且包含逗号，分割为列表
        if isinstance(self.value, str) and ',' in self.value:
            return [v.strip() for v in self.value.split(',') if v.strip()]
        return self.value


class TextValueSelectVariable(SpliceVariable):
    """文本值映射选择器

    元数据(meta_tag=select.select_meta)定义:
      [{"label": "成功", "text": "success", "value": "0"},
       {"label": "失败", "text": "failed", "value": "1"}]
    运行时 value 是选中项的 value，输出的 {text, value} 可在下游节点使用。
    """
    code = "text_value_select"
    name = "文本值映射选择"
    type = "meta"
    tag = "select.select"
    meta_tag = "select.select_meta"
    description = "文本值映射选择器，选择项输出 text/value 二元组"

    def get_value(self):
        return self.value


class DataTableVariable(SpliceVariable):
    """表格变量 — 支持 ${KEY.column[0]} 和 ${KEY.flat__column} 引用

    值格式: [{"ip": "10.0.0.1", "hostname": "web-01"}, ...]
    引用格式:
      ${table_var.0.ip}       → 第0行的ip
      ${table_var.flat__ip}   → 所有ip值拼接为逗号分隔字符串
    """
    code = "datatable"
    name = "表格"
    type = "meta"
    tag = "datatable.datatable"
    meta_tag = "datatable.datatable_meta"
    description = "表格数据，支持行列引用"


class IpSelectorVariable(SpliceVariable):
    """IP 选择器变量 — 从预设列表中选择 IP 地址

    元数据定义可选的 IP 范围或主机列表。
    """
    code = "ip_selector"
    name = "IP选择器"
    type = "meta"
    tag = "ip_selector.ip_selector"
    meta_tag = "ip_selector.ip_selector_meta"
    description = "IP地址选择器，支持多选"


# =============================================================================
# Dynamic 类型 — 运行时动态计算的变量
# =============================================================================

class CurrentTimeVariable(LazyVariable):
    """当前时间变量 — 返回执行时刻的系统时间"""
    code = "current_time"
    name = "当前时间"
    type = "dynamic"
    tag = "current_time.current_time"
    description = "执行时的系统当前时间"

    def get_value(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class FormatSupportCurrentTimeVariable(LazyVariable):
    """自定义格式当前时间 — 通过 value 指定格式字符串

    value: "%Y-%m-%d" → "2026-06-01"
    """
    code = "format_support_current_time"
    name = "格式化当前时间"
    type = "dynamic"
    tag = "format_support_current_time.format_support_current_time"
    description = "支持自定义格式的当前时间"

    def get_value(self):
        fmt = str(self.value) if self.value else "%Y-%m-%d %H:%M:%S"
        return datetime.now().strftime(fmt)


class FormatSupportDatetimeVariable(LazyVariable):
    """自定义格式日期时间变量"""
    code = "format_support_datetime"
    name = "格式化日期时间"
    type = "dynamic"
    tag = "format_support_datetime.format_support_datetime"
    description = "支持自定义格式的日期时间"

    def get_value(self):
        fmt = str(self.value) if self.value else "%Y-%m-%d %H:%M:%S"
        return datetime.now().strftime(fmt)
