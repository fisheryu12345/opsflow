"""Mako 模板变量解析 — 安全沙箱封装

提供类 Mako 的表达式能力，支持：
  - #{ var_name }          直接变量取值
  - #{ 'hello ' + name }   字符串拼接
  - #{ a > 0 && b < 5 }    布尔表达式
  - #{ [x*2 for x in lst] } 列表推导

使用 Mako 引擎渲染 #{...} 表达式。
同时保持 ${key} 语法向后兼容（由上游 variable_resolver 处理）。

安全防护：
  - 拒绝黑名单模式（__import__, eval(, exec(, os. 等）
  - 仅暴露白名单内置函数
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# #{ 表达式 } 正则
MAKO_PATTERN = re.compile(r'#\{(.*?)\}')

# 安全检查黑名单
BLOCKED_PATTERNS = [
    '__import__', 'import ', 'eval(', 'exec(', 'open(',
    'os.', 'subprocess', 'sys.', '__builtins__',
    '__class__', '__base__', '__subclasses__',
]

# Mako 可用的安全内置函数
SAFE_BUILTINS = {
    'str': str, 'int': int, 'float': float, 'bool': bool,
    'len': len, 'range': range, 'min': min, 'max': max,
    'abs': abs, 'round': round, 'sorted': sorted,
    'True': True, 'False': False, 'None': None,
    'list': list, 'dict': dict, 'tuple': tuple,
    'enumerate': enumerate, 'zip': zip, 'reversed': reversed,
    'isinstance': isinstance, 'type': type,
    'split': str.split, 'join': ''.join,
    'upper': str.upper, 'lower': str.lower, 'strip': str.strip,
}


class MakoResolver:
    """安全的类 Mako 表达式解析器

    将 #{ expr } 转换为 Mako 原生 ${ expr } 语法后调用 Mako 模板引擎。
    渲染期间暂时转义已有 ${key} 以免冲突。
    """

    _ESCAPE_MARKER = '___MAKO_SAFE___'

    def resolve(self, template_str: str, context: dict) -> str:
        """解析 #{...} 表达式，返回渲染后的字符串"""
        if not template_str or '#{' not in template_str:
            return template_str

        # 安全检查恶意模式
        for pattern in BLOCKED_PATTERNS:
            if pattern in template_str:
                logger.warning("[MakoResolver] Blocked pattern '%s' in: %s",
                               pattern, template_str[:120])
                return template_str

        try:
            from mako.template import Template

            # 转义已有 ${key} → $___MAKO_SAFE___key}
            escaped, key_map = self._escape_existing_vars(template_str)
            # 转换 #{expr} → ${expr}
            converted = MAKO_PATTERN.sub(r'${\1}', escaped)

            t = Template(converted)
            # 合并 context + 安全内置函数
            render_ctx = {**context, **SAFE_BUILTINS}
            rendered = t.render(**render_ctx)
            # 还原转义的 ${key}
            restored = self._restore_vars(rendered, key_map)
            return restored

        except ImportError:
            logger.warning("[MakoResolver] Mako not installed")
            return template_str
        except Exception as e:
            logger.warning("[MakoResolver] Error: %s, template=%s",
                           e, template_str[:100])
            return template_str

    def _escape_existing_vars(self, s: str) -> tuple:
        """暂时转义已有 ${key} 避免被 Mako 解释"""
        key_map = {}
        def _escape(m):
            full = m.group(0)
            idx = len(key_map)
            placeholder = f"__MAKO_ESC_{idx}__"
            key_map[placeholder] = full
            return placeholder
        # VariableResolver 的 ${key} 正则
        var_pattern = re.compile(r'\$\{([^}]+)\}')
        escaped = var_pattern.sub(_escape, s)
        return escaped, key_map

    def _restore_vars(self, s: str, key_map: dict) -> str:
        """还原被转义的 ${key}"""
        for placeholder, original in key_map.items():
            s = s.replace(placeholder, original)
        return s


def resolve_with_mako(template_str: str, context: dict) -> str:
    """通用入口 — 检测 #{...} 走 Mako 路径，否则原样返回"""
    if not template_str or '#{' not in template_str:
        return template_str
    return MakoResolver().resolve(template_str, context)
