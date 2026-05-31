"""表单配置协议 — 定义插件入参的描述模型

后端用 Pydantic 定义 form schema，前端 RenderForm 通用渲染引擎解析。
支持字段类型：input / select / textarea / checkbox / radio / int /
                code_editor / datetime / host_selector / datatable
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from enum import Enum


class ValidationType(str, Enum):
    REQUIRED = "required"
    REGEX = "regex"
    CUSTOM = "custom"


class ValidationRule(BaseModel):
    type: ValidationType
    args: Optional[Any] = None  # regex → pattern, custom → 函数名
    error_message: str = ""


class FormEvent(BaseModel):
    """跨字段联动事件"""
    source: str       # 监听哪个 tag_code
    event_type: str   # change / init / click
    action: str       # 前端 Tag 组件上的方法名


class FormItem(BaseModel):
    """单个表单字段"""
    tag_code: str                      # 字段唯一标识，对应 execute() 的形参名
    type: str                          # input / select / textarea / ...
    name: str                          # 前端标签名
    attrs: Dict[str, Any] = {}         # placeholder, options, multiple, min, max ...
    default: Any = None
    hidden: bool = False
    hookable: bool = False             # 是否可提升为全局变量
    validation: List[ValidationRule] = []
    events: List[FormEvent] = []
    col: int = 12                      # 栅格宽度 1-12


class FormGroup(BaseModel):
    """分组/组合 — 递归包含 FormItem 或其他 FormGroup"""
    type: str = "combine"
    name: str
    tag_code: str
    items: List[Union['FormItem', 'FormGroup']]


# 顶层配置：字段列表，可包含分组
FormConfig = List[Union[FormItem, FormGroup]]
