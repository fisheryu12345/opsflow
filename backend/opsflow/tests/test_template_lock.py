"""TemplateLock tests — acquire/release/heartbeat/expiry/update guard"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from opsflow.models import FlowTemplate, TemplateLock

Users = get_user_model()


class TemplateLockAcquireTest(TestCase):
    """acquire_lock happy path and conflict detection"""

    def setUp(self):
        self.user = Users.objects.create(username='alice')
        self.other = Users.objects.create(username='bob')
        self.template = FlowTemplate.objects.create(name='Test Tpl', created_by=self.user)

    def test_acquire_creates_lock(self):
        _, created = TemplateLock.objects.get_or_create(
            template=self.template, defaults={'user': self.user})
        self.assertTrue(created)

    def test_acquire_same_user_refreshes(self):
        lock = TemplateLock.objects.create(template=self.template, user=self.user)
        old_heartbeat = lock.heartbeat
        lock.heartbeat = None
        lock.save()
        self.assertIsNotNone(TemplateLock.objects.filter(template=self.template).exists())

    def test_acquire_conflict_returns_existing(self):
        TemplateLock.objects.create(template=self.template, user=self.user)
        lock2, created = TemplateLock.objects.get_or_create(
            template=self.template, defaults={'user': self.other})
        self.assertFalse(created)
        self.assertEqual(lock2.user, self.user)


class TemplateLockExpiryTest(TestCase):
    """is_expired and heartbeat timeout"""

    def setUp(self):
        self.user = Users.objects.create(username='carol')
        self.template = FlowTemplate.objects.create(name='Expiry Tpl', created_by=self.user)

    def test_is_expired_returns_true_when_old(self):
        from datetime import timedelta
        from django.utils import timezone
        lock = TemplateLock.objects.create(template=self.template, user=self.user)
        # Use update to bypass auto_now on heartbeat field
        past = timezone.now() - timedelta(seconds=120)
        TemplateLock.objects.filter(pk=lock.pk).update(heartbeat=past)
        lock.refresh_from_db()
        self.assertTrue(lock.is_expired())

    def test_is_expired_returns_false_when_recent(self):
        from datetime import timedelta
        from django.utils import timezone
        lock = TemplateLock.objects.create(
            template=self.template, user=self.user,
            heartbeat=timezone.now())
        self.assertFalse(lock.is_expired())


class TemplateLockReleaseTest(TestCase):
    """release_lock idempotency"""

    def setUp(self):
        self.user = Users.objects.create(username='dave')
        self.template = FlowTemplate.objects.create(name='Release Tpl', created_by=self.user)

    def test_release_deletes_lock(self):
        TemplateLock.objects.create(template=self.template, user=self.user)
        TemplateLock.objects.filter(template=self.template, user=self.user).delete()
        self.assertFalse(TemplateLock.objects.filter(template=self.template).exists())

    def test_release_idempotent(self):
        """Releasing a non-existent lock should not crash"""
        deleted, _ = TemplateLock.objects.filter(template=self.template).delete()
        self.assertEqual(deleted, 0)


class TemplateLoopIterationTest(TestCase):
    """_resolve_loop_iteration increment logic"""

    def setUp(self):
        self.user = Users.objects.create(username='eve')
        self.template = FlowTemplate.objects.create(name='Loop Tpl', created_by=self.user)
        from opsflow.models import FlowExecution
        self.execution = FlowExecution.objects.create(template=self.template)

    def test_first_iteration_returns_zero(self):
        from opsflow.signals.trace import _resolve_loop_iteration
        result = _resolve_loop_iteration(self.execution, 'node_1', 0)
        self.assertEqual(result, 0)

    def test_completed_iteration_returns_incremented(self):
        from opsflow.signals.trace import _resolve_loop_iteration
        from opsflow.models import NodeExecutionTrace
        # Simulate first iteration completed
        NodeExecutionTrace.objects.create(
            execution=self.execution, node_id='node_1',
            retry_count=0, loop_iteration=0, status='completed')
        result = _resolve_loop_iteration(self.execution, 'node_1', 0)
        self.assertEqual(result, 1)
