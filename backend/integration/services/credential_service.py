# -*- coding: utf-8 -*-
"""Credential encryption/decryption service for Integration Hub

凭证加密服务 — 基于 Django SECRET_KEY 派生 AES-256 密钥，
使用 Fernet (AES-128-CBC + HMAC) 对称加密。
"""

import base64
import hashlib
import logging

from django.conf import settings

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

logger = logging.getLogger(__name__)

_fernet = None  # cached Fernet instance


def _get_fernet() -> "Fernet":
    """获取（或创建）Fernet 加密实例"""
    global _fernet
    if _fernet is not None:
        return _fernet

    # Derive a 32-byte key from Django SECRET_KEY using PBKDF2
    secret = settings.SECRET_KEY.encode('utf-8')
    salt = b'opsflow-integration-credential-v1'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    _fernet = Fernet(key)
    return _fernet


def encrypt_credential(plain_text: str) -> str:
    """加密凭证明文 → 返回加密后的字符串"""
    if not HAS_CRYPTOGRAPHY:
        logger.warning("cryptography 未安装，使用 base64 编码（非加密！）")
        if isinstance(plain_text, str):
            return base64.b64encode(plain_text.encode()).decode()
        return plain_text

    if not plain_text:
        return plain_text
    cipher = _get_fernet()
    return cipher.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_credential(cipher_text: str) -> str:
    """解密凭证密文 → 返回明文"""
    if not HAS_CRYPTOGRAPHY:
        logger.warning("cryptography 未安装，使用 base64 解码（非加密！）")
        try:
            return base64.b64decode(cipher_text).decode()
        except Exception:
            return cipher_text

    if not cipher_text:
        return cipher_text
    cipher = _get_fernet()
    try:
        return cipher.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"凭证解密失败: {e}")
        return ""
