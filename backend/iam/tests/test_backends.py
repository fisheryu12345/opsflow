"""LDAPBackend 认证后端测试 — mock LDAP 连接器实例

LDAPBackend 依赖 LDAP 服务器连接，本测试使用 mock 模拟 ldap3 行为。
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestLDAPBackend(TestCase):
    """LDAPBackend 认证后端测试"""

    def setUp(self):
        """准备测试数据 — 创建 mock ConnectorInstance 和 UserMapping"""
        self.username = "ldap_user"
        self.password = "secret123"

    @patch('iam.sync.backends.ConnectorInstance.objects.filter')
    @patch('iam.sync.backends.LDAPBackend._bind_and_auth')
    def test_authenticate_delegates_to_bind(self, mock_bind, mock_filter):
        """authenticate 应该调用 _bind_and_auth 遍历 LDAP 实例"""
        mock_filter.return_value.select_related.return_value = []
        from iam.sync.backends import LDAPBackend
        backend = LDAPBackend()

        mock_bind.return_value = None
        result = backend.authenticate(None, username=self.username, password=self.password)
        self.assertIsNone(result)

    @patch('iam.sync.backends.ConnectorInstance.objects.filter')
    def test_no_ldap_sources_returns_none(self, mock_filter):
        """没有配置 LDAP 源时应返回 None"""
        mock_filter.return_value.select_related.return_value = []
        from iam.sync.backends import LDAPBackend
        backend = LDAPBackend()
        result = backend.authenticate(None, username=self.username, password=self.password)
        self.assertIsNone(result)

    @patch('iam.sync.backends.ConnectorInstance.objects.filter')
    def test_empty_password_returns_none(self, mock_filter):
        """空密码应返回 None"""
        from iam.sync.backends import LDAPBackend
        backend = LDAPBackend()
        result = backend.authenticate(None, username=self.username, password="")
        self.assertIsNone(result)

    def test_get_user_returns_none_for_invalid_id(self):
        """不存在的 user_id 应返回 None"""
        from iam.sync.backends import LDAPBackend
        backend = LDAPBackend()
        result = backend.get_user(99999)
        self.assertIsNone(result)

    def test_get_user_returns_valid_user(self):
        """存在的 user_id 应返回 User 对象"""
        user = User.objects.create(username="test_get_user", name="Test")
        from iam.sync.backends import LDAPBackend
        backend = LDAPBackend()
        result = backend.get_user(user.id)
        self.assertIsNotNone(result)
        self.assertEqual(result.username, "test_get_user")
