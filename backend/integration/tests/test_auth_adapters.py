"""Integration auth adapter tests — LDAPConnector, SAMLConnector

Uses mocked connections to test health_check logic without real servers.
"""
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase


class TestLDAPConnector(SimpleTestCase):
    """LDAPConnector health_check 测试"""

    def setUp(self):
        self.mock_instance = MagicMock()
        self.mock_instance.config = {
            "host": "ldap.example.com",
            "port": 389,
            "use_ssl": False,
            "base_dn": "dc=example,dc=com",
        }
        self.mock_instance.credentials.filter.return_value.first.return_value = None

    @patch('integration.adapters.auth.ldap.LDAPConnector._bind')
    def test_health_check_success(self, mock_bind):
        """Bind 成功时应返回 healthy"""
        mock_conn = MagicMock()
        mock_conn.bound = True
        mock_bind.return_value = mock_conn

        from integration.adapters.auth.ldap import LDAPConnector
        connector = LDAPConnector(self.mock_instance)
        result = connector.health_check()
        self.assertTrue(result.is_healthy)

    @patch('integration.adapters.auth.ldap.LDAPConnector._bind')
    def test_health_check_bind_failure(self, mock_bind):
        """Bind 失败时应返回 unhealthy"""
        mock_conn = MagicMock()
        mock_conn.bound = False
        mock_bind.return_value = mock_conn

        from integration.adapters.auth.ldap import LDAPConnector
        connector = LDAPConnector(self.mock_instance)
        result = connector.health_check()
        self.assertFalse(result.is_healthy)

    @patch('integration.adapters.auth.ldap.LDAPConnector._bind')
    def test_health_check_exception(self, mock_bind):
        """Bind 抛出异常时应返回 unhealthy"""
        mock_bind.side_effect = Exception("Connection refused")

        from integration.adapters.auth.ldap import LDAPConnector
        connector = LDAPConnector(self.mock_instance)
        result = connector.health_check()
        self.assertFalse(result.is_healthy)
        self.assertIn("Connection refused", result.message)

    def test_no_credentials_returns_none_bind(self):
        """无凭证时 _bind 应返回 None"""
        self.mock_instance.credentials.filter.return_value.first.return_value = None

        from integration.adapters.auth.ldap import LDAPConnector
        connector = LDAPConnector(self.mock_instance)
        result = connector._bind()
        self.assertIsNone(result)


class TestSAMLConnector(SimpleTestCase):
    """SAMLConnector health_check 测试"""

    def setUp(self):
        self.mock_instance = MagicMock()

    def test_no_entity_id_returns_unhealthy(self):
        """无 entity_id 和 metadata_url 时返回 unhealthy"""
        self.mock_instance.config = {}

        from integration.adapters.auth.saml import SAMLConnector
        connector = SAMLConnector(self.mock_instance)
        result = connector.health_check()
        self.assertFalse(result.is_healthy)

    def test_entity_id_only_returns_healthy(self):
        """仅有 entity_id 时返回 healthy（跳过验证）"""
        self.mock_instance.config = {"entity_id": "https://idp.example.com"}

        from integration.adapters.auth.saml import SAMLConnector
        connector = SAMLConnector(self.mock_instance)
        result = connector.health_check()
        self.assertTrue(result.is_healthy)

    @patch('requests.get')
    def test_metadata_url_success(self, mock_get):
        """metadata_url 可访问且返回有效 XML 时返回 healthy"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'<?xml version="1.0"?><md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"/>'
        mock_get.return_value = mock_resp

        self.mock_instance.config = {
            "entity_id": "test",
            "metadata_url": "https://idp.example.com/metadata",
        }

        from integration.adapters.auth.saml import SAMLConnector
        connector = SAMLConnector(self.mock_instance)
        result = connector.health_check()
        self.assertTrue(result.is_healthy)

    @patch('requests.get')
    def test_metadata_url_http_error(self, mock_get):
        """metadata_url 返回非 200 时返回 unhealthy"""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        self.mock_instance.config = {
            "entity_id": "test",
            "metadata_url": "https://idp.example.com/metadata",
        }

        from integration.adapters.auth.saml import SAMLConnector
        connector = SAMLConnector(self.mock_instance)
        result = connector.health_check()
        self.assertFalse(result.is_healthy)
        self.assertIn("404", result.message)

    @patch('requests.get')
    def test_metadata_url_connection_error(self, mock_get):
        """metadata_url 连接失败时返回 unhealthy"""
        import requests
        mock_get.side_effect = requests.RequestException("Connection timeout")

        self.mock_instance.config = {
            "entity_id": "test",
            "metadata_url": "https://idp.example.com/metadata",
        }

        from integration.adapters.auth.saml import SAMLConnector
        connector = SAMLConnector(self.mock_instance)
        result = connector.health_check()
        self.assertFalse(result.is_healthy)
