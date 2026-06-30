# -*- coding: utf-8 -*-
"""LDAP/AD Bind authentication backend

Authenticates users against LDAP/AD by trying all active LDAP ConnectorInstances.
If Bind succeeds and user mapping exists, returns the local user.
If no mapping exists, JIT-creates the user from LDAP attributes.

Integrated into Django's AUTHENTICATION_BACKENDS chain.
"""

import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone

from integration.models.connector import ConnectorInstance
from integration.adapters.auth.ldap import LDAPConnector
from integration.services.credential_service import decrypt_credential
from iam.sync.models import UserMapping

logger = logging.getLogger(__name__)
UserModel = get_user_model()


class LDAPBackend(ModelBackend):
    """LDAP/AD Bind 认证后端

    依次尝试每个启用的 LDAP/AD ConnectorInstance 做 Bind 认证。
    Bind 成功后查找或 JIT 创建本地 User 记录。

    Usage:
        # 在 AUTHENTICATION_BACKENDS 中添加此路径:
        # "iam.sync.backends.LDAPBackend"
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or not password:
            return None

        logger.info("LDAPBackend: attempting LDAP Bind for %s", username)

        # 遍历所有启用的 LDAP/AD 连接器实例
        for inst in ConnectorInstance.objects.filter(
            definition__code='ldap',
            is_active=True,
        ).select_related('definition'):
            try:
                result = self._bind_and_auth(inst, username, password)
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    "LDAPBackend: instance %s error: %s", inst.name, e
                )
                continue

        logger.info("LDAPBackend: no LDAP source matched for %s", username)
        return None

    def _bind_and_auth(self, inst, username, password):
        """尝试对一个 LDAP 实例做 Bind 认证"""
        connector = LDAPConnector(inst)
        ldap_conn = None

        try:
            ldap_conn = connector._bind()
            if not ldap_conn or not ldap_conn.bound:
                return None

            # 解析用户名属性和搜索过滤
            config = inst.config or {}
            username_attr = config.get("username_attr", "sAMAccountName")
            base_dn = config.get("base_dn", "")
            search_filter = config.get("user_search_filter", "(objectClass=person)")

            # 查找匹配的用户条目
            ldap_conn.search(
                search_base=base_dn,
                search_filter=f"(&{search_filter}({username_attr}={username}))",
                attributes=[username_attr, "displayName", "mail", "telephoneNumber", "department"],
            )

            if not ldap_conn.entries:
                logger.debug("LDAPBackend: user %s not found in %s", username, inst.name)
                return None

            entry = ldap_conn.entries[0]
            remote_dn = entry.entry_dn

            # 收集属性
            attrs = {}
            for attr in entry.entry_attributes:
                val = entry[attr].value if hasattr(entry[attr], "value") else entry[attr]
                attrs[attr] = str(val) if val is not None else ""

            # 查找已有映射
            mapping = UserMapping.objects.filter(
                source_instance=inst,
                remote_dn=remote_dn,
            ).select_related("user").first()

            if mapping:
                user = mapping.user
                if not self.user_can_authenticate(user):
                    logger.warning("LDAPBackend: user %s is disabled", username)
                    return None
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                return user

            # JIT 创建用户
            user = self._jit_create_user(inst, remote_dn, username, attrs, config)
            if user:
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
            return user

        finally:
            if ldap_conn:
                try:
                    ldap_conn.unbind()
                except Exception:
                    pass

    def _jit_create_user(self, inst, remote_dn, username, attrs, config):
        """Just-In-Time 创建用户 — Bind 成功后为用户在本地创建记录"""
        field_mapping = config.get("field_mapping", {})

        # 映射字段
        def _map(local_field, default=""):
            attr_name = field_mapping.get(local_field)
            if attr_name and attr_name in attrs:
                return attrs[attr_name]
            return default

        # 检查是否已存在同用户名的记录（可能来自其他来源）
        existing = UserModel.objects.filter(username=username).first()
        if existing:
            # 创建一个映射关联到已有用户
            UserMapping.objects.create(
                source_instance=inst,
                user=existing,
                remote_dn=remote_dn,
                remote_attrs=attrs,
            )
            return existing

        user = UserModel.objects.create(
            username=username,
            name=_map("name", username),
            email=_map("email", ""),
            mobile=_map("mobile", ""),
            is_active=True,
        )
        UserMapping.objects.create(
            source_instance=inst,
            user=user,
            remote_dn=remote_dn,
            remote_attrs=attrs,
        )
        logger.info("LDAPBackend: JIT created user %s from %s", username, inst.name)
        return user

    def get_user(self, user_id):
        """Standard Django auth backend interface"""
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
