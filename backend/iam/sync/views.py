# -*- coding: utf-8 -*-
"""Identity sync API views — sync trigger, status, SAML ACS

Registers endpoints under /api/iam/sync/ and SAML endpoints.
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from dvadmin.utils.json_response import DetailResponse, ErrorResponse
from integration.models.connector import ConnectorInstance
from integration.models.integration_log import IntegrationLog

from iam.sync.provider import LDAPSyncProvider, SyncResult
from iam.sync.serializers import SyncResultSerializer, SyncStatusSerializer
from iam.sync.models import DeptMapping, UserMapping

logger = logging.getLogger(__name__)


# ── Sync trigger ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync(request, instance_id):
    """手动触发指定连接器实例的全量同步"""
    inst = get_object_or_404(
        ConnectorInstance.objects.filter(definition__code='ldap'),
        id=instance_id,
    )

    if not inst.is_active:
        return ErrorResponse(msg="连接器实例未启用", code=4000)

    # 记录同步日志起始
    log_entry = IntegrationLog.objects.create(
        instance=inst,
        definition_code='ldap',
        action='identity_sync',
        status='success',  # will update on failure
    )

    try:
        provider = LDAPSyncProvider(inst)
        result = provider.sync_full()

        # 更新同步日志
        log_entry.response_data = {
            'dept_added': result.stats.dept_added,
            'dept_updated': result.stats.dept_updated,
            'dept_disabled': result.stats.dept_disabled,
            'user_added': result.stats.user_added,
            'user_updated': result.stats.user_updated,
            'user_disabled': result.stats.user_disabled,
            'errors': result.errors,
        }
        if not result.success:
            log_entry.status = 'failed'
            log_entry.error_message = result.error
        log_entry.save(update_fields=['response_data', 'status', 'error_message'])

        serializer = SyncResultSerializer(data={
            'success': result.success,
            'instance_id': inst.id,
            'instance_name': inst.name,
            'dept_added': result.stats.dept_added,
            'dept_updated': result.stats.dept_updated,
            'dept_disabled': result.stats.dept_disabled,
            'user_added': result.stats.user_added,
            'user_updated': result.stats.user_updated,
            'user_disabled': result.stats.user_disabled,
            'errors': result.errors,
            'error': result.error,
        })
        serializer.is_valid()

        return DetailResponse(data=serializer.data, msg="同步完成")

    except Exception as e:
        log_entry.status = 'failed'
        log_entry.error_message = str(e)
        log_entry.save(update_fields=['status', 'error_message'])
        logger.exception("Sync failed for instance %s: %s", inst.name, e)
        return ErrorResponse(msg=f"同步失败: {e}", code=5000)


# ── Sync status ─────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_status(request):
    """返回所有启用的 LDAP/AD 连接器实例的同步概览"""
    instances = ConnectorInstance.objects.filter(
        definition__code='ldap',
    ).select_related('definition')

    results = []
    for inst in instances:
        dept_count = DeptMapping.objects.filter(source_instance=inst).count()
        user_count = UserMapping.objects.filter(source_instance=inst).count()

        last_log = IntegrationLog.objects.filter(
            instance=inst,
            action='identity_sync',
        ).order_by('-create_datetime').first()

        results.append({
            'instance_id': inst.id,
            'instance_name': inst.name,
            'definition_code': 'ldap',
            'status': inst.status,
            'dept_count': dept_count,
            'user_count': user_count,
            'last_sync_at': last_log.create_datetime if last_log else None,
        })

    serializer = SyncStatusSerializer(data=results, many=True)
    serializer.is_valid()
    return DetailResponse(data=serializer.data, msg="OK")


# ── Connection test ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_connection(request, instance_id):
    """测试 LDAP 连接器实例的连接"""
    inst = get_object_or_404(ConnectorInstance, id=instance_id)

    try:
        from integration.adapters.auth.ldap import LDAPConnector
        from integration.services.health_service import run_health_check
        healthy, msg = run_health_check(inst)

        # 更新实例状态
        from django.utils import timezone
        inst.status = 'online' if healthy else 'error'
        inst.last_health_check = timezone.now()
        inst.last_health_message = msg
        inst.save(update_fields=['status', 'last_health_check', 'last_health_message'])

        return DetailResponse(data={
            'status': inst.status,
            'message': msg,
        }, msg="测试完成")
    except Exception as e:
        return ErrorResponse(msg=f"连接测试失败: {e}", code=5000)


# ── Sync history ────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_history(request, instance_id):
    """获取指定实例的同步历史记录"""
    inst = get_object_or_404(ConnectorInstance, id=instance_id)
    logs = IntegrationLog.objects.filter(
        instance=inst,
        action='identity_sync',
    ).order_by('-create_datetime')[:50]

    data = [{
        'id': log.id,
        'status': log.status,
        'started_at': log.create_datetime,
        'total': (log.response_data or {}).get('user_added', 0)
                + (log.response_data or {}).get('user_updated', 0)
                + (log.response_data or {}).get('dept_added', 0),
        'error_count': len((log.response_data or {}).get('errors', [])),
        'error_message': log.error_message,
        'triggered_by': 'manual',  # simplified
    } for log in logs]

    return DetailResponse(data=data, msg="OK")


# ── SAML ACS ────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def saml_login(request, instance_id):
    """SAML SP-initiated login — 生成 AuthnRequest 并重定向到 IdP

    GET /api/iam/saml/login/{id}/ → redirect to IdP SSO URL
    """
    try:
        inst = get_object_or_404(
            ConnectorInstance.objects.filter(definition__code='saml', is_active=True),
            id=instance_id,
        )
    except Exception as e:
        return ErrorResponse(msg=f"SAML 实例未找到或未启用: {e}", code=4000)

    config = inst.config or {}
    entity_id = config.get('entity_id', f'opsflow-saml-{inst.id}')
    acs_url = config.get('acs_url', request.build_absolute_uri(
        f'/api/iam/sync/saml/acs/{instance_id}/'
    ))
    idp_sso_url = config.get('metadata_url', '')

    if not idp_sso_url:
        return ErrorResponse(msg="IdP SSO URL 未配置", code=4000)

    # 生成 SAML AuthnRequest
    import base64
    from urllib.parse import quote

    import xml.etree.ElementTree as ET

    authn_request = ET.Element('{urn:oasis:names:tc:SAML:2.0:protocol}AuthnRequest', {
        'xmlns:samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
        'xmlns:saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
        'ID': f'_{request.build_absolute_uri()}_{instance_id}_{timezone.now().timestamp()}',
        'Version': '2.0',
        'IssueInstant': timezone.now().isoformat(),
        'ProtocolBinding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
        'AssertionConsumerServiceURL': acs_url,
    })
    issuer = ET.SubElement(authn_request, '{urn:oasis:names:tc:SAML:2.0:assertion}Issuer')
    issuer.text = entity_id

    xml_str = ET.tostring(authn_request, encoding='utf-8', xml_declaration=True)
    encoded = base64.b64encode(xml_str).decode('utf-8')
    relay_state = request.build_absolute_uri('/')

    redirect_url = (
        f"{idp_sso_url}?SAMLRequest={quote(encoded)}"
        f"&RelayState={quote(relay_state)}"
    )

    return DetailResponse(data={
        'redirect_url': redirect_url,
    }, msg="SAML 登录跳转")


@api_view(['POST'])
@permission_classes([AllowAny])
def saml_acs(request, instance_id):
    """SAML Assertion Consumer Service — 接收 IdP 的 SAML Response

    从断言中提取用户属性，查找或创建 UserMapping，
    返回 JWT token（与正常登录响应一致）。
    """
    try:
        inst = get_object_or_404(
            ConnectorInstance.objects.filter(definition__code='saml', is_active=True),
            id=instance_id,
        )

        # 解析 SAML Response
        saml_response = request.data.get('SAMLResponse', '')
        if not saml_response:
            return ErrorResponse(msg="缺少 SAMLResponse", code=4000)

        # 使用 python3-saml 解析断言
        from onelogin.saml2.response import OneLogin_Saml2_Response
        from onelogin.saml2.authn_request import OneLogin_Saml2_Authn_Request
        from onelogin.saml2.settings import OneLogin_Saml2_Settings

        # 构建 SP 设置
        config = inst.config or {}
        from urllib.parse import urljoin
        from django.http import HttpRequest

        # 获取 SP 配置
        sp_entity_id = config.get('entity_id', f'opsflow-saml-{inst.id}')
        acs_url = config.get('acs_url', request.build_absolute_uri())

        # 构建 saml2 settings
        import json
        saml_settings = {
            'sp': {
                'entityId': sp_entity_id,
                'assertionConsumerService': {
                    'url': acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
                },
            },
            'idp': {
                'entityId': config.get('entity_id', ''),
                'singleSignOnService': {
                    'url': config.get('metadata_url', ''),
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect',
                },
                'x509cert': '',  # Will attempt to load from metadata or credential
            },
        }

        # 尝试加载 IdP 证书
        cred = inst.credentials.filter(cred_type='certificate').first()
        if cred:
            from integration.services.credential_service import decrypt_credential
            saml_settings['idp']['x509cert'] = decrypt_credential(
                cred.encrypted_value
            )

        # 解析 SAML Response
        req = One_Saml2_Response(settings=json.dumps(saml_settings), response=saml_response)
        if not req.is_valid():
            return ErrorResponse(msg="SAML Response 验证失败", code=4000)

        # 提取属性
        attrs = req.get_attributes()
        name_id = req.get_nameid()

        attr_username = config.get('attr_username', 'nameId')
        attr_name = config.get('attr_name', 'displayName')
        attr_email = config.get('attr_email', 'email')

        username = attrs.get(attr_username, [name_id])[0] if isinstance(
            attrs.get(attr_username), list
        ) else attrs.get(attr_username, name_id)

        # 查找映射
        mapping = UserMapping.objects.filter(
            source_instance=inst,
            remote_dn=name_id,
        ).select_related('user').first()

        if mapping:
            user = mapping.user
        else:
            # JIT 创建用户
            from system.models import Users
            user = Users.objects.create(
                username=username,
                name=attrs.get(attr_name, [username])[0] if isinstance(
                    attrs.get(attr_name), list
                ) else attrs.get(attr_name, username),
                email=attrs.get(attr_email, [''])[0] if isinstance(
                    attrs.get(attr_email), list
                ) else attrs.get(attr_email, ''),
                is_active=True,
            )
            UserMapping.objects.create(
                source_instance=inst,
                user=user,
                remote_dn=name_id,
                remote_attrs=attrs,
            )

        if not user.is_active:
            return ErrorResponse(msg="用户已被禁用", code=4000)

        # 签发 JWT token（与正常登录一致）
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        # 返回 HTML 页面，自动将 token POST 回前端
        frontend_url = request.build_absolute_uri('/')
        html = f"""<!DOCTYPE html>
<html><head><title>登录成功</title></head><body>
<script>
  (function() {{
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = '{frontend_url}api/login/callback/';
    var access = document.createElement('input');
    access.type = 'hidden';
    access.name = 'access';
    access.value = '{str(refresh.access_token)}';
    form.appendChild(access);
    var refreshField = document.createElement('input');
    refreshField.type = 'hidden';
    refreshField.name = 'refresh';
    refreshField.value = '{str(refresh)}';
    form.appendChild(refreshField);
    document.body.appendChild(form);
    form.submit();
  }})();
</script>
<p>登录成功，正在跳转...</p>
</body></html>"""
        from django.http import HttpResponse
        return HttpResponse(html)

    except ImportError:
        return ErrorResponse(msg="python3-saml 或依赖未安装", code=5000)
    except Exception as e:
        logger.exception("SAML ACS error: %s", e)
        return ErrorResponse(msg=f"SAML 处理失败: {e}", code=5000)


@api_view(['GET'])
@permission_classes([AllowAny])
def saml_metadata(request, instance_id):
    """返回 SAML SP metadata XML（供 IdP 配置使用）"""
    inst = get_object_or_404(
        ConnectorInstance.objects.filter(definition__code='saml'),
        id=instance_id,
    )

    config = inst.config or {}
    sp_entity_id = config.get('entity_id', f'opsflow-saml-{inst.id}')
    acs_url = config.get('acs_url', request.build_absolute_uri(
        request.path.replace('/metadata/', '/acs/')
    ))

    # 生成 SP metadata XML
    from onelogin.saml2.constants import OneLogin_Saml2_Constants

    metadata_xml = f"""<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{sp_entity_id}">
  <md:SPSSODescriptor protocolSupportEnumeration="{OneLogin_Saml2_Constants.NS_SAMLP}">
    <md:AssertionConsumerService
        Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        Location="{acs_url}"
        index="1"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>"""

    return Response(content=metadata_xml, content_type='application/xml')
