# -*- coding: utf-8 -*-
"""Dangerous command detector — Rule engine + AI semantic analysis

高危命令双层检测：规则引擎（同步）+ AI 语义检测（异步）
"""

import logging
import re

from django.conf import settings

from ..models import DangerousCmdRule, DangerousCheckLog

logger = logging.getLogger(__name__)
FSM = 'dangerous_detector'

# 内置高危规则（通过 seed_job_platform 命令同步到 DB）
BUILTIN_RULES = [
    # 系统破坏
    {'name': 'rm-root', 'pattern': 'rm -rf /', 'action': 'reject',
     'severity': 'critical', 'description': '禁止递归删除根目录'},
    {'name': 'rm-root-star', 'pattern': 'rm -rf /*', 'action': 'reject',
     'severity': 'critical', 'description': '禁止递归删除根目录下所有文件'},
    {'name': 'mkfs', 'pattern': r'mkfs\.\w+', 'is_regex': True, 'action': 'reject',
     'severity': 'critical', 'description': '禁止格式化文件系统'},
    {'name': 'dd-write', 'pattern': r'dd\s+if=.*\s+of=', 'is_regex': True, 'action': 'reject',
     'severity': 'critical', 'description': '禁止直接磁盘写入'},
    {'name': 'fork-bomb', 'pattern': r':\(\s*\)\s*\{', 'is_regex': True, 'action': 'reject',
     'severity': 'critical', 'description': '禁止 fork 炸弹'},
    {'name': 'dev-sda-write', 'pattern': r'>\s*/dev/sd[a-z]', 'is_regex': True, 'action': 'reject',
     'severity': 'critical', 'description': '禁止直接写入块设备'},
    # 权限破坏
    {'name': 'chmod-777-root', 'pattern': r'chmod\s+(-R\s+)?777\s+/', 'is_regex': True,
     'action': 'warn', 'severity': 'high', 'description': '禁止将根目录设为 777'},
    {'name': 'chown-recursive', 'pattern': r'chown\s+-R\s+', 'is_regex': True,
     'action': 'warn', 'severity': 'high', 'description': '递归修改所有者需谨慎'},
    # 重启关机
    {'name': 'shutdown-now', 'pattern': r'shutdown\s+(-h\s+)?now', 'is_regex': True,
     'action': 'approval', 'severity': 'high', 'description': '批量关机需要审批'},
    {'name': 'reboot', 'pattern': r'^\s*reboot\s*$', 'is_regex': True,
     'action': 'approval', 'severity': 'high', 'description': '批量重启需要审批'},
    # 数据库危险操作
    {'name': 'drop-table', 'pattern': r'\bDROP\s+TABLE\b', 'is_regex': True,
     'action': 'approval', 'severity': 'critical', 'description': '删表操作需要审批'},
    {'name': 'truncate-table', 'pattern': r'\bTRUNCATE\b', 'is_regex': True,
     'action': 'approval', 'severity': 'high', 'description': '清表操作需要审批'},
    # 远程下载执行
    {'name': 'curl-pipe-bash', 'pattern': r'curl\s+.*\|\s*(ba)?sh',
     'is_regex': True, 'action': 'warn', 'severity': 'medium',
     'description': '远程下载并执行脚本需确认来源'},
    {'name': 'wget-pipe-sh', 'pattern': r'wget\s+.*\|\s*(ba)?sh',
     'is_regex': True, 'action': 'warn', 'severity': 'medium',
     'description': '远程下载并执行脚本需确认来源'},
]


def check_script_safety(content: str, script_type: str = 'shell') -> dict:
    """双层检测入口：规则引擎 → AI

    Returns:
        {safe, blocked, action, reason, risk_level, ai_suggestion}
    """
    if not content:
        return {'safe': True, 'blocked': False, 'action': 'allow',
                'reason': '', 'risk_level': 'none'}

    # Layer 1: 规则引擎
    rule_result = _check_rules(content, script_type)
    if rule_result.get('blocked'):
        _save_check_log(content, script_type, rule_result, {})
        return rule_result

    # Layer 2: AI 语义检测（异步）
    ai_task = None
    try:
        from .celery_tasks import ai_script_check
        ai_task = ai_script_check.delay(content, script_type)
    except Exception as e:
        logger.warning(f"AI 检测不可用（{e}），仅使用规则引擎结果")
        _save_check_log(content, script_type, rule_result, {})
        return {**rule_result, 'ai_available': False}

    # 返回规则引擎结果 + 标记 AI 正在运行
    result = {**rule_result, 'ai_available': True, 'ai_task_id': ai_task.id}
    _save_check_log(content, script_type, rule_result, {})
    return result


def _check_rules(content: str, script_type: str) -> dict:
    """规则引擎检测 — 先 DB 规则后内置规则"""
    # 1. DB 规则
    rules = DangerousCmdRule.objects.filter(is_active=True)
    for rule in rules:
        if rule.script_type != 'all' and rule.script_type != script_type:
            continue
        matched = _match_rule(content, rule)
        if matched:
            return _build_rule_result(rule)

    # 2. 内置规则
    for builtin in BUILTIN_RULES:
        if builtin.get('script_type') and builtin['script_type'] != script_type:
            continue
        matched = _match_builtin(content, builtin)
        if matched:
            return _build_builtin_result(builtin)

    return {'safe': True, 'blocked': False, 'action': 'allow',
            'reason': '', 'risk_level': 'none'}


def _match_rule(content: str, rule) -> bool:
    """匹配单条 DB 规则"""
    try:
        if rule.is_regex:
            return bool(re.search(rule.pattern, content, re.IGNORECASE))
        return rule.pattern.lower() in content.lower()
    except re.error:
        logger.error(f"高危规则正则错误: {rule.name} -> {rule.pattern}")
        return False


def _match_builtin(content: str, rule: dict) -> bool:
    """匹配内置规则"""
    try:
        if rule.get('is_regex'):
            return bool(re.search(rule['pattern'], content, re.IGNORECASE))
        return rule['pattern'].lower() in content.lower()
    except re.error:
        return False


def _build_rule_result(rule) -> dict:
    """构建规则命中结果"""
    result = {
        'safe': rule.action != 'reject',
        'blocked': rule.action == 'reject',
        'action': rule.action,
        'risk_level': rule.severity,
        'reason': rule.description or f'匹配高危规则: {rule.name}',
        'matched_rule': rule.name,
    }
    return result


def _build_builtin_result(rule: dict) -> dict:
    """构建内置规则命中结果"""
    result = {
        'safe': rule.get('action') != 'reject',
        'blocked': rule.get('action') == 'reject',
        'action': rule.get('action', 'reject'),
        'risk_level': rule.get('severity', 'high'),
        'reason': rule.get('description', ''),
        'matched_rule': rule.get('name', ''),
    }
    return result


def _save_check_log(content: str, script_type: str,
                    rule_result: dict, ai_result: dict):
    """保存检测日志"""
    try:
        DangerousCheckLog.objects.create(
            script_content=content[:2000],
            script_type=script_type,
            rule_hits=[{'action': rule_result.get('action'),
                        'reason': rule_result.get('reason')}],
            ai_result=ai_result,
            final_action=rule_result.get('action', 'allow'),
        )
    except Exception as e:
        logger.error(f"保存高危检测日志失败: {e}")


AI_CHECK_PROMPT = """分析以下脚本是否存在安全风险，返回 JSON:

脚本语言: {script_type}
脚本内容:
```
{content}
```

检查维度:
1. 数据破坏: 删除/格式化/覆写重要数据
2. 权限提升: 提权/越权操作
3. 信息泄露: 读取/外发敏感信息
4. 资源耗尽: fork 炸弹/死循环/大量磁盘 IO
5. 隐蔽持久化: 写启动项/定时任务后门/替换系统命令
6. 供应链风险: 从不可信源下载执行

返回格式: {{"risk_level": "none/low/medium/high/critical", "reason": "...", "suggestion": "..."}}
"""


def build_ai_check_prompt(script_content: str, script_type: str) -> str:
    """构建 AI 检测 Prompt"""
    return AI_CHECK_PROMPT.format(
        script_type=script_type,
        content=script_content[:3000],  # 限制长度
    )


def sync_builtin_rules():
    """将内置规则同步到数据库（启动时调用）"""
    for rule_def in BUILTIN_RULES:
        DangerousCmdRule.objects.get_or_create(
            name=rule_def['name'],
            defaults={
                'pattern': rule_def['pattern'],
                'is_regex': rule_def.get('is_regex', False),
                'action': rule_def['action'],
                'severity': rule_def.get('severity', 'high'),
                'description': rule_def.get('description', ''),
                'is_active': True,
                'script_type': rule_def.get('script_type', 'all'),
            },
        )
    logger.info(f"Built-in dangerous rules synced: {len(BUILTIN_RULES)} entries")
