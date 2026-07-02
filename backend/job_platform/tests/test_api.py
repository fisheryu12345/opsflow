# -*- coding: utf-8 -*-
"""Tests for job_platform API endpoints

API 测试：所有端点的基础 CRUD + 自定义操作
"""

import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from iam.models import IAMUsers as User  # TODO: migrate
from ..models import Script, Template, Plan, Step, JobExecution, DangerousCmdRule, Account


class BaseAPITest(TestCase):
    """API 测试基类 — 创建认证用户"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='testadmin',
            password='testpass123',
            email='test@opsflow.local',
        )
        # 获取 token
        response = self.client.post('/api/login/', {
            'username': 'testadmin',
            'password': 'testpass123',
        }, format='json')
        data = json.loads(response.content)
        self.token = data.get('access', data.get('token', ''))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')


class ScriptAPITest(BaseAPITest):
    """脚本管理 API 测试"""

    def test_list_scripts_empty(self):
        response = self.client.get('/api/job-platform/scripts/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_create_script(self):
        response = self.client.post('/api/job-platform/scripts/', {
            'name': 'Disk Check',
            'script_type': 'shell',
            'content': 'df -h',
            'category': 'public',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_create_and_retrieve(self):
        # Create
        self.client.post('/api/job-platform/scripts/', {
            'name': 'Mem Check',
            'script_type': 'shell',
            'content': 'free -m',
        }, format='json')
        # List
        response = self.client.get('/api/job-platform/scripts/')
        data = json.loads(response.content)
        scripts = data.get('data', [])
        self.assertGreaterEqual(len(scripts), 1)

    def test_script_publish(self):
        create_resp = self.client.post('/api/job-platform/scripts/', {
            'name': 'Test Script',
            'script_type': 'shell',
            'content': 'echo test',
        }, format='json')
        script_id = json.loads(create_resp.content)['data']['id']

        # Publish
        resp = self.client.post(f'/api/job-platform/scripts/{script_id}/publish/', {
            'content': 'echo v2',
            'changelog': 'Updated',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 2000)


class TemplateAPITest(BaseAPITest):
    """模板管理 API 测试"""

    def test_create_template(self):
        response = self.client.post('/api/job-platform/templates/', {
            'name': 'Deploy App',
            'description': 'Automated deployment',
            'category': 'deploy',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_publish_template(self):
        resp = self.client.post('/api/job-platform/templates/', {
            'name': 'Test Tpl',
        }, format='json')
        tpl_id = json.loads(resp.content)['data']['id']

        resp = self.client.post(f'/api/job-platform/templates/{tpl_id}/publish/')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 2000)

    def test_template_with_steps(self):
        # Create template
        resp = self.client.post('/api/job-platform/templates/', {
            'name': 'Multi Step',
        }, format='json')
        tpl_id = json.loads(resp.content)['data']['id']

        # Create steps
        for i in range(3):
            self.client.post('/api/job-platform/steps/', {
                'template': tpl_id,
                'type': 'script',
                'name': f'Step {i+1}',
            }, format='json')

        # Verify steps
        resp = self.client.get('/api/job-platform/steps/', {'template': tpl_id})
        data = json.loads(resp.content)
        steps = data.get('data', [])
        self.assertGreaterEqual(len(steps), 3)

    def test_create_plan_from_template(self):
        resp = self.client.post('/api/job-platform/templates/', {
            'name': 'Plan Source',
        }, format='json')
        tpl_id = json.loads(resp.content)['data']['id']

        resp = self.client.post('/api/job-platform/plans/', {
            'template': tpl_id,
            'name': 'My Plan',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data['code'], 2000)


class AccountAPITest(BaseAPITest):
    """账号管理 API 测试"""

    def test_create_account(self):
        response = self.client.post('/api/job-platform/accounts/', {
            'name': 'prod-root',
            'username': 'root',
            'protocol': 'ssh',
            'password': 'enc-test',
            'port': 22,
            'category': 'system',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_list_accounts(self):
        self.client.post('/api/job-platform/accounts/', {
            'name': 'test-acc', 'username': 'root', 'protocol': 'ssh',
            'password': 'enc', 'category': 'system',
        }, format='json')
        response = self.client.get('/api/job-platform/accounts/')
        data = json.loads(response.content)
        accounts = data.get('data', [])
        self.assertGreaterEqual(len(accounts), 1)


class ExecutionAPITest(BaseAPITest):
    """执行管理 API 测试"""

    def test_list_executions_empty(self):
        response = self.client.get('/api/job-platform/executions/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_stop_execution(self):
        # Create execution
        template = Template.objects.create(name='Test')
        execution = JobExecution.objects.create(
            template=template,
            status='running',
            triggered_by='manual',
        )
        response = self.client.post(
            f'/api/job-platform/executions/{execution.id}/stop/'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_stop_non_running_execution(self):
        execution = JobExecution.objects.create(
            status='success', triggered_by='manual',
        )
        response = self.client.post(
            f'/api/job-platform/executions/{execution.id}/stop/'
        )
        data = json.loads(response.content)
        self.assertEqual(data['code'], 4000)  # Error: not running


class DangerousRuleAPITest(BaseAPITest):
    """高危命令规则 API 测试"""

    def test_create_rule(self):
        response = self.client.post('/api/job-platform/dangerous-rules/', {
            'name': 'test-rule',
            'pattern': 'rm -rf',
            'action': 'reject',
            'severity': 'high',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_check_command(self):
        response = self.client.post('/api/job-platform/dangerous-rules/check/', {
            'command': 'rm -rf /',
            'script_type': 'shell',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)
        self.assertTrue(data['data']['blocked'])

    def test_toggle_rule(self):
        rule = DangerousCmdRule.objects.create(
            name='toggle-test', pattern='test', action='reject',
        )
        response = self.client.post(
            f'/api/job-platform/dangerous-rules/{rule.id}/toggle/'
        )
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)


class CronJobAPITest(BaseAPITest):
    """定时作业 API 测试"""

    def test_create_cron(self):
        response = self.client.post('/api/job-platform/cron-jobs/', {
            'name': 'Daily Backup',
            'cron_expression': '0 2 * * *',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_toggle_cron(self):
        from ..models import CronJob
        cron = CronJob.objects.create(
            name='Test Cron', cron_expression='0 * * * *',
        )
        response = self.client.post(
            f'/api/job-platform/cron-jobs/{cron.id}/toggle/'
        )
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)

    def test_cron_history(self):
        from ..models import CronJob, CronJobExecution, JobExecution
        cron = CronJob.objects.create(
            name='Hist Cron', cron_expression='0 * * * *',
        )
        exec_ = JobExecution.objects.create(status='success', triggered_by='cron')
        CronJobExecution.objects.create(
            cron_job=cron, execution=exec_, status='success',
            scheduled_time='2026-06-05 02:00:00',
        )
        response = self.client.get(
            f'/api/job-platform/cron-jobs/{cron.id}/history/'
        )
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)


class DashboardAPITest(BaseAPITest):
    """仪表盘 API 测试"""

    def test_dashboard(self):
        response = self.client.get('/api/job-platform/dashboard/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)
        self.assertIn('total_scripts', data['data'])
        self.assertIn('running_executions', data['data'])


class StepChainAPITest(BaseAPITest):
    """步骤链表操作 API 测试"""

    def test_move_step(self):
        tpl = Template.objects.create(name='Step Move Test')
        s1 = Step.objects.create(template=tpl, type='script', name='S1')
        s2 = Step.objects.create(template=tpl, type='script', name='S2')
        s3 = Step.objects.create(template=tpl, type='script', name='S3')

        # Link: s1 -> s2 -> s3
        Step.objects.filter(id=s1.id).update(next_step=s2)
        Step.objects.filter(id=s2.id).update(previous_step=s1, next_step=s3)
        Step.objects.filter(id=s3.id).update(previous_step=s2)

        # Move s3 before s1
        response = self.client.post(f'/api/job-platform/steps/{s3.id}/move/', {
            'previous_step_id': None,
            'next_step_id': s1.id,
        }, format='json')
        data = json.loads(response.content)
        self.assertEqual(data['code'], 2000)
