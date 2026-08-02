"""AI Key 静态加密工具。

学生自己填的第三方 API Key（DeepSeek / 通义 / 智谱 等）属于敏感凭据。
多用户网站上若明文存库，一旦数据库泄露会暴露所有用户的密钥。
这里用 Fernet（AES-128-CBC + HMAC）对静态存储的 Key 做加密，密钥由应用
SECRET_KEY 派生，不单独落盘。

加密后的字符串带 ``fernet:`` 前缀标记，便于与历史明文数据兼容：
- 解密时遇到该前缀则解密，否则按明文返回（向后兼容桌面版存量数据）。
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app

MARKER = 'fernet:'


def _secret() -> str:
    """读取 SECRET_KEY；无应用上下文时回退默认值（仅测试用）。"""
    try:
        return current_app.config.get('SECRET_KEY') or 'dev-secret-key'
    except RuntimeError:
        return 'dev-secret-key'


def _fernet() -> Fernet:
    # Fernet 需要 32 字节 url-safe base64 密钥；用 SECRET_KEY 的 SHA256 派生。
    digest = hashlib.sha256(_secret().encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(plaintext: str) -> str:
    """加密明文，返回带标记的字符串。"""
    token = _fernet().encrypt(plaintext.encode('utf-8')).decode('utf-8')
    return MARKER + token


def decrypt_value(stored: str) -> str:
    """解密存储值；无前缀或非加密数据原样返回。

    解密失败（如 SECRET_KEY 轮换导致旧数据无法解密）时回退原文，避免直接抛错。
    """
    if not stored:
        return ''
    if stored.startswith(MARKER):
        try:
            token = stored[len(MARKER):]
            return _fernet().decrypt(token.encode('utf-8')).decode('utf-8')
        except Exception:
            return stored
    return stored
