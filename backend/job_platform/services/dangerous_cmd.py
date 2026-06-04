"""Dangerous command detection service

高危命令过滤：基于关键词/正则匹配，支持直接拦截、需要审批、仅警告
"""

import re
import logging

logger = logging.getLogger(__name__)

FSM = 'dangerous_cmd_detection'

# 内置高危命令关键词
BUILTIN_DANGEROUS_KEYWORDS = [
    'rm -rf /', 'rm -rf /*', 'mkfs.', 'dd if=', ':(){ :|:& };:', # 系统破坏
    'chmod -R 000', 'chown -R',                                   # 权限破坏
    'mv / /tmp', 'cp /dev/null',                                  # 文件破坏
    'wget ', 'curl ',                                              # 下载执行（部分情况）
    '> /dev/sda', '> /dev/sdb',                                    # 磁盘写入
    'shutdown -h now', 'reboot', 'halt', 'poweroff',               # 重启/关机（批量时高危）
    'passwd root',                                                  # 密码修改
]


def check_dangerous_command(command: str) -> dict:
    """检查命令是否高危，返回 {safe, blocked, action, reason}"""
    if not command:
        return {'safe': True, 'blocked': False, 'action': 'allow', 'reason': ''}

    from ..models.models import DangerousCmdRule
    rules = DangerousCmdRule.objects.filter(is_active=True)

    # 1. 先检查数据库规则
    for rule in rules:
        matched = False
        if rule.is_regex:
            try:
                matched = bool(re.search(rule.pattern, command, re.IGNORECASE))
            except re.error:
                continue
        else:
            matched = rule.pattern.lower() in command.lower()

        if matched:
            if rule.action == 'reject':
                return {
                    'safe': False, 'blocked': True,
                    'action': 'reject', 'reason': rule.description or f'匹配高危规则: {rule.name}',
                }
            elif rule.action == 'approval':
                return {
                    'safe': True, 'blocked': False,
                    'action': 'approval', 'reason': f'需要审批: {rule.name}',
                }
            elif rule.action == 'warn':
                return {
                    'safe': True, 'blocked': False,
                    'action': 'warn', 'reason': f'警告: {rule.name}',
                }

    # 2. 再检查内置关键词
    cmd_lower = command.lower()
    for kw in BUILTIN_DANGEROUS_KEYWORDS:
        if kw.lower() in cmd_lower:
            return {
                'safe': False, 'blocked': True,
                'action': 'reject', 'reason': f'内建高危关键词匹配: {kw}',
            }

    return {'safe': True, 'blocked': False, 'action': 'allow', 'reason': ''}
