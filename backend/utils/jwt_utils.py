"""JWT 工具：双令牌（access / refresh）+ 认证装饰器。

token 载荷约定：
    {
        "sub": <user_id>,
        "type": "access" | "refresh",
        "iat": <issued at>,
        "exp": <expires at>
    }
"""
import time

import jwt
from flask import request, jsonify, current_app
from functools import wraps

from app.extensions import db
from models.user import User


# ---- 令牌生成 ----
def create_access_token(user_id, secret=None, hours=None):
    secret = secret or current_app.config['JWT_SECRET']
    hours = hours if hours is not None else current_app.config.get(
        'JWT_ACCESS_EXPIRATION_HOURS', 2
    )
    now = int(time.time())
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': now,
        'exp': now + int(hours) * 3600,
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def create_refresh_token(user_id, secret=None, days=None):
    secret = secret or current_app.config['JWT_SECRET']
    days = days if days is not None else current_app.config.get(
        'JWT_REFRESH_EXPIRATION_DAYS', 30
    )
    now = int(time.time())
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': now,
        'exp': now + int(days) * 86400,
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def decode_token(token, expected_type=None, secret=None):
    """解码并校验 token。expected_type 用于约束 access/refresh。

    失败抛出 jwt.InvalidTokenError 系列异常。
    """
    secret = secret or current_app.config['JWT_SECRET']
    payload = jwt.decode(token, secret, algorithms=['HS256'])
    if expected_type and payload.get('type') != expected_type:
        raise jwt.InvalidTokenError('unexpected token type')
    return payload


# ---- 向后兼容：保留旧调用方式 ----
def generate_token(user_id, secret=None, hours=None):
    return create_access_token(user_id, secret=secret, hours=hours)


def _extract_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None


def login_required(f):
    """JWT 认证装饰器：仅接受 access token，将当前用户注入视图函数首参。"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({'code': 401, 'message': '未提供认证令牌'}), 401
        try:
            payload = decode_token(token, expected_type='access')
            user_id = payload.get('sub')
            current_user = db.session.get(User, int(user_id)) if user_id is not None else None
            if current_user is None:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效令牌'}), 401

        return f(current_user, *args, **kwargs)

    return decorated
