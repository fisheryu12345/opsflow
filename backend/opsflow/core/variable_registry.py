"""变量注册表系统 — 适配自 bk_sops LazyVariable + VariableLibrary 模式

提供:
  - SpliceVariable: 支持 ${key} 模板替换的变量基类
  - LazyVariable: 在模板替换后执行 get_value() 自定义转换
  - VariableLibrary: 全局变量注册表（自动发现）
  - RegisterVariableMeta: 元类，子类创建时自动注册
"""

import logging
import re
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

# 全局变量注册表
VARIABLE_REGISTRY: Dict[str, Type['LazyVariable']] = {}


class RegisterVariableMeta(type):
    """元类 — 在子类创建时自动注册到 VariableLibrary"""

    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if not name.startswith('_') and hasattr(cls, 'code') and cls.code:
            if cls.code in VARIABLE_REGISTRY:
                logger.warning("变量 code 重复: %s", cls.code)
            VARIABLE_REGISTRY[cls.code] = cls
        return cls


class SpliceVariable(metaclass=RegisterVariableMeta):
    """支持 ${key} 模板替换的变量基类

    子类可设置:
      code: str         — 变量唯一标识（如 "input"）
      name: str         — 显示名称（如 "文本输入"）
      type: str         — "general" | "meta" | "dynamic"
      tag: str          — 前端标签（如 "input.input"）
      meta_tag: str     — 元数据配置标签（可选，如 "select.select_meta"）
      description: str  — 描述文本
    """
    code: str = ""
    name: str = ""
    type: str = "general"
    tag: str = ""
    meta_tag: str = ""
    description: str = ""

    def __init__(self, value: Any = None, context: dict = None):
        self.value = value
        self.context = context or {}

    def get_value(self) -> Any:
        """子类覆盖 — 执行自定义转换后返回值"""
        return self.value


class LazyVariable(SpliceVariable):
    """延迟计算变量 — 在模板替换后执行 get_value()

    与 bk_sops LazyVariable 等价:
      1. 父类 SpliceVariable 完成 ${key} 替换
      2. 本类 get_value() 对替换后的值做自定义转换
    """
    pass


class VariableLibrary:
    """变量库 — 按 code 检索变量类"""

    @classmethod
    def get_var_class(cls, code: str) -> Optional[Type[LazyVariable]]:
        return VARIABLE_REGISTRY.get(code)

    @classmethod
    def get_var(cls, code: str, value: Any = None,
                context: dict = None) -> Optional[LazyVariable]:
        klass = cls.get_var_class(code)
        if klass:
            return klass(value=value, context=context)
        return None

    @classmethod
    def resolve(cls, code: str, value: Any, context: dict = None) -> Any:
        """按 code 获取变量类并执行解析

        Args:
            code: 变量类型 code
            value: 原始值
            context: 解析上下文

        Returns:
            解析后的值
        """
        var = cls.get_var(code, value=value, context=context)
        if var:
            return var.get_value()
        return value

    @classmethod
    def get_all_variables(cls) -> Dict[str, dict]:
        """返回所有注册变量的摘要信息"""
        result = {}
        for code, klass in VARIABLE_REGISTRY.items():
            result[code] = {
                "code": klass.code,
                "name": klass.name,
                "type": klass.type,
                "tag": klass.tag,
                "meta_tag": klass.meta_tag,
                "description": klass.description,
            }
        return result

    @classmethod
    def get_by_tag(cls, tag: str) -> Optional[Type[LazyVariable]]:
        """按 tag 查找变量类"""
        for klass in VARIABLE_REGISTRY.values():
            if klass.tag == tag or klass.meta_tag == tag:
                return klass
        return None
