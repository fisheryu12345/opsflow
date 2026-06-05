# -*- coding: utf-8 -*-
"""Tests for job_platform models

数据模型测试：创建、状态转换、链表操作、字符串表示
"""

from django.test import TestCase
from ..models import (
    Account, FileSource, DangerousCmdRule, DangerousCheckLog,
    Script, ScriptVersion, ScriptReference,
    Template, Plan, Variable,
    Step, ScriptStep, FileStep, ApprovalStep,
    JobExecution, StepExecution,
    CronJob, CronJobExecution,
)


class AccountModelTest(TestCase):
    """账号模型测试"""

    def setUp(self):
        self.account = Account.objects.create(
            name='prod-root',
            username='root',
            protocol='ssh',
            password='enc:xxxx',
            port=22,
            credential_type='password',
            category='system',
            scope='global',
        )

    def test_account_creation(self):
        self.assertEqual(str(self.account), 'prod-root (root@ssh)')
        self.assertTrue(self.account.is_active)

    def test_account_fields(self):
        self.assertEqual(self.account.protocol, 'ssh')
        self.assertEqual(self.account.port, 22)
        self.assertEqual(self.account.category, 'system')
        self.assertEqual(self.account.scope, 'global')


class ScriptModelTest(TestCase):
    """脚本模型测试"""

    def setUp(self):
        self.script = Script.objects.create(
            name='Disk Check',
            script_type='shell',
            content='df -h',
            category='public',
            status='online',
            current_version='1.0.0',
        )

    def test_script_creation(self):
        self.assertEqual(str(self.script), 'Disk Check v1.0.0')
        self.assertEqual(self.script.script_type, 'shell')

    def test_script_version(self):
        version = ScriptVersion.objects.create(
            script=self.script,
            version='2.0.0',
            content='df -h --total',
            changelog='Add total',
            status='draft',
        )
        self.assertEqual(str(version), 'Disk Check v2.0.0')
        self.assertEqual(version.script.id, self.script.id)

    def test_script_reference(self):
        ref = ScriptReference.objects.create(
            script=self.script,
            reference_type='template',
            reference_id=1,
            reference_name='Test Template',
        )
        self.assertIn('Disk Check', str(ref))
        self.assertIn('Test Template', str(ref))


class TemplatePlanModelTest(TestCase):
    """模板/方案模型测试"""

    def setUp(self):
        self.template = Template.objects.create(
            name='Deploy App',
            status='draft',
            category='deploy',
        )
        self.plan = Plan.objects.create(
            template=self.template,
            name='Deploy App Plan',
            enable_step_ids=[],
        )

    def test_template_creation(self):
        self.assertEqual(str(self.template), 'Deploy App (draft)')
        self.assertEqual(self.template.status, 'draft')

    def test_plan_creation(self):
        self.assertIn('Deploy App Plan', str(self.plan))
        self.assertEqual(self.plan.template.id, self.template.id)

    def test_variable(self):
        var = Variable.objects.create(
            template=self.template,
            name='APP_PORT',
            var_type='string',
            default_value='8080',
            required=True,
        )
        self.assertEqual(str(var), 'APP_PORT (string)')


class StepChainModelTest(TestCase):
    """步骤链表模型测试"""

    def setUp(self):
        self.template = Template.objects.create(name='Chain Test')
        self.step1 = Step.objects.create(template=self.template, type='script', name='Step 1')
        self.step2 = Step.objects.create(template=self.template, type='script', name='Step 2')
        self.step3 = Step.objects.create(template=self.template, type='approval', name='Step 3')
        # Link: step1 <-> step2 <-> step3
        self.step1.next_step = self.step2
        self.step2.previous_step = self.step1
        self.step2.next_step = self.step3
        self.step3.previous_step = self.step2
        self.step1.save()
        self.step2.save()
        self.step3.save()
        self.template.first_step = self.step1
        self.template.last_step = self.step3
        self.template.save()

    def test_chain_forward(self):
        self.assertEqual(self.step1.next_step, self.step2)
        self.assertEqual(self.step2.next_step, self.step3)
        self.assertIsNone(self.step3.next_step)

    def test_chain_backward(self):
        self.assertIsNone(self.step1.previous_step)
        self.assertEqual(self.step2.previous_step, self.step1)
        self.assertEqual(self.step3.previous_step, self.step2)

    def test_template_pointers(self):
        self.assertEqual(self.template.first_step, self.step1)
        self.assertEqual(self.template.last_step, self.step3)

    def test_step_types(self):
        self.assertEqual(self.step1.type, 'script')
        self.assertEqual(self.step3.type, 'approval')

    def test_step_detail_creation(self):
        ScriptStep.objects.create(
            step=self.step1,
            content='echo hello',
            timeout=60,
        )
        script_step = ScriptStep.objects.get(step=self.step1)
        self.assertEqual(script_step.content, 'echo hello')
        self.assertEqual(script_step.timeout, 60)

    def test_ref_variables(self):
        self.step1.ref_variables = ['HOST_IP', 'PORT']
        self.step1.save()
        step = Step.objects.get(id=self.step1.id)
        self.assertEqual(step.ref_variables, ['HOST_IP', 'PORT'])


class JobExecutionModelTest(TestCase):
    """执行实例模型测试"""

    def setUp(self):
        self.template = Template.objects.create(name='Exec Test')
        self.execution = JobExecution.objects.create(
            template=self.template,
            status='running',
            triggered_by='manual',
            variables={'key': 'value'},
        )

    def test_execution_creation(self):
        self.assertIn('running', str(self.execution))
        self.assertEqual(self.execution.triggered_by, 'manual')

    def test_execution_status_transition(self):
        self.execution.status = 'success'
        self.execution.end_time = None
        from django.utils import timezone
        self.execution.end_time = timezone.now()
        self.execution.save()
        loaded = JobExecution.objects.get(id=self.execution.id)
        self.assertEqual(loaded.status, 'success')
        self.assertIsNotNone(loaded.end_time)

    def test_step_execution(self):
        step = Step.objects.create(template=self.template, type='script')
        step_exec = StepExecution.objects.create(
            execution=self.execution,
            step=step,
            step_type='script',
            step_name='Step 1',
            status='success',
            host_results={'127.0.0.1': {'exit_code': 0, 'stdout': 'ok'}},
        )
        self.assertEqual(step_exec.success_hosts, 1)
        self.assertEqual(step_exec.total_hosts, 1)
        self.assertEqual(step_exec.status, 'success')


class DangerousCmdRuleModelTest(TestCase):
    """高危命令规则模型测试"""

    def setUp(self):
        self.rule = DangerousCmdRule.objects.create(
            name='rm-root',
            pattern='rm -rf /',
            action='reject',
            severity='critical',
            script_type='all',
        )

    def test_rule_creation(self):
        self.assertEqual(str(self.rule), 'rm-root [reject]')
        self.assertEqual(self.rule.severity, 'critical')

    def test_check_log(self):
        log = DangerousCheckLog.objects.create(
            script_content='rm -rf /tmp',
            script_type='shell',
            rule_hits=[{'rule_id': self.rule.id, 'name': 'rm-root', 'action': 'reject'}],
            final_action='reject',
        )
        self.assertEqual(str(log)[:5], 'Check')
        self.assertEqual(log.final_action, 'reject')


class CronJobModelTest(TestCase):
    """定时作业模型测试"""

    def setUp(self):
        self.cron = CronJob.objects.create(
            name='Nightly Backup',
            cron_expression='0 2 * * *',
            timezone='Asia/Shanghai',
            is_active=True,
        )

    def test_cron_creation(self):
        self.assertIn('Nightly Backup', str(self.cron))
        self.assertTrue(self.cron.is_active)

    def test_cron_execution_history(self):
        hist = CronJobExecution.objects.create(
            cron_job=self.cron,
            status='success',
            scheduled_time='2026-06-05 02:00:00',
        )
        self.assertEqual(hist.status, 'success')


class FileSourceModelTest(TestCase):
    """文件源模型测试"""

    def setUp(self):
        self.fs = FileSource.objects.create(
            name='Backup S3',
            source_type='s3',
            config={'bucket': 'opsflow-backup', 'region': 'cn-north-1'},
        )

    def test_file_source_creation(self):
        self.assertEqual(str(self.fs), 'Backup S3 (s3)')
        self.assertEqual(self.fs.config['bucket'], 'opsflow-backup')
