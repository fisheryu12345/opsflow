# -*- coding: utf-8 -*-
"""LDAP / Active Directory connector adapter for Integration Hub

LDAP/AD 连接器适配器 — 通过集成中心管理 LDAP/AD 连接测试和目录访问。

配置项（存储在 ConnectorInstance.config 中）:
  - host: 服务器地址
  - port: 端口 (default: 389)
  - use_ssl: 启用 SSL (default: false)
  - base_dn: Base DN
  - user_search_filter: 用户搜索过滤 (default: (objectClass=person))
  - dept_search_filter: 部门搜索过滤 (default: (objectClass=organizationalUnit))
  - username_attr: 用户名属性 (default: sAMAccountName)
  - sync_cron: 同步定时 cron 表达式
  - field_mapping: 字段映射表 {local_field: remote_attr}

凭证（存储在 ConnectorCredential 中）:
  - 类型 password: Bind DN 作为 name, password 作为 encrypted_value
  - 每个实例至少一条凭证

注意:
  - ldap3 是纯 Python 实现，跨平台兼容，无 C 扩展依赖
  - AD 兼容: Active Directory 也是 LDAP 协议，可通过此连接器接入
"""

import logging
from typing import Optional

import ldap3
from ldap3 import Connection, Server, ALL, core

from integration.adapters.base import BaseConnector, HealthResult
from integration.services.credential_service import decrypt_credential

logger = logging.getLogger(__name__)


class LDAPConnector(BaseConnector):
    """LDAP / Active Directory 连接器适配器

    提供连接测试 (health_check) 和 ldap3 Connection 获取。
    不包含同步逻辑 — 同步由 iam/sync/ 中的 SyncProvider 处理。
    """

    def health_check(self) -> HealthResult:
        """测试 LDAP Bind 连接 — 使用存储的 Bind DN + 密码"""
        try:
            conn = self._bind()
            if conn and conn.bound:
                return HealthResult(is_healthy=True, message="LDAP Bind 成功")
            return HealthResult(is_healthy=False, message=str(conn.result) if conn else "连接失败")
        except Exception as e:
            logger.warning("LDAP health_check failed: %s", e)
            return HealthResult(is_healthy=False, message=str(e))

    def get_client(self) -> Optional[Connection]:
        """获取已绑定的 ldap3 Connection 实例

        调用方使用完毕后应调用 conn.unbind() 释放连接。
        """
        return self._bind()

    def _make_server(self) -> Server:
        """根据配置创建 ldap3 Server 对象"""
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 389)
        use_ssl = self.config.get("use_ssl", False)

        logger.debug("LDAP server: %s:%s (ssl=%s)", host, port, use_ssl)
        return Server(
            host,
            port=int(port),
            use_ssl=bool(use_ssl),
            get_info=ALL,
        )

    def _bind(self) -> Optional[Connection]:
        """执行 LDAP Bind 认证，返回绑定的 Connection

        从 ConnectorCredential 中读取 Bind DN 和密码。
        """
        # 从凭证中读取 bind_dn 和 password
        bind_dn = ""
        password = ""
        try:
            # 取第一个 password 类型凭证作为 Bind DN + 密码
            cred = self.instance.credentials.filter(cred_type="password").first()
            if cred:
                bind_dn = cred.name  # Bind DN 存在 name 字段
                password = decrypt_credential(cred.encrypted_value)
        except Exception as e:
            logger.error("读取 LDAP 凭证失败: %s", e)
            return None

        if not bind_dn or not password:
            logger.warning("LDAP 凭证未配置（需要 bind_dn 和 password）")
            return None

        try:
            server = self._make_server()
            conn = Connection(
                server,
                user=bind_dn,
                password=password,
                auto_bind=True,
                raise_exceptions=False,
            )
            return conn
        except ldap3.core.exceptions.LDAPBindError as e:
            logger.warning("LDAP Bind 失败: %s", e)
            return None
        except Exception as e:
            logger.error("LDAP 连接异常: %s", e)
            return None

    def search(self, search_filter: str, attributes=None) -> list:
        """在 base_dn 下执行 LDAP 搜索

        Args:
            search_filter: LDAP 过滤表达式，如 (objectClass=person)
            attributes: 需要返回的属性列表，None=全部

        Returns:
            list of dict: 每个条目包含 dn 和 attributes
        """
        conn = self._bind()
        if not conn:
            return []

        base_dn = self.config.get("base_dn", "")
        try:
            conn.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=attributes or ldap3.ALL_ATTRIBUTES,
                size_limit=0,  # 无限制（LDAP 服务器可能有硬限制）
            )
            results = []
            for entry in conn.entries:
                attr_dict = {}
                for attr in entry.entry_attributes:
                    val = entry[attr].value if hasattr(entry[attr], "value") else entry[attr]
                    attr_dict[attr] = val
                results.append({
                    "dn": entry.entry_dn,
                    "attributes": attr_dict,
                })
            conn.unbind()
            return results
        except Exception as e:
            logger.error("LDAP 搜索失败: %s", e)
            try:
                conn.unbind()
            except Exception:
                pass
            return []

    def close(self):
        """释放连接资源"""
        self._client = None
