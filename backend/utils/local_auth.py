"""本地鉴权工具：基于 AuthSession 的会话令牌，替代原 JWT 双令牌。

单机桌面场景：用户在本机登录后签发一个随机令牌，存于本地 auth_sessions 表；
前端在 Authorization: Bearer <token> 中携带，login_required 据此注入 current_user。
完全离线，不依赖任何外部服务。
"""
import secrets

from flask import request, jsonify
from functools import wraps

from app.extensions import db
from models.user import User
from models.auth_session import AuthSession
from utils.time_utils import utcnow


def create_session(user_id) -> str:
    """为用户创建一条登录会话，返回令牌。"""
    token = secrets.token_hex(32)
    expires = utcnow() + __import__('datetime').timedelta(days=AuthSession.SESSION_DAYS)
    sess = AuthSession(user_id=user_id, token=token, expires_at=expires)
    db.session.add(sess)
    db.session.commit()
    return token


def destroy_session(token: str):
    if not token:
        return
    sess = AuthSession.query.filter_by(token=token).first()
    if sess:
        db.session.delete(sess)
        db.session.commit()


def get_user_by_token(token: str):
    """校验令牌有效性，返回 User 或 None。"""
    if not token:
        return None
    sess = AuthSession.query.filter_by(token=token).first()
    if sess is None:
        return None
    if sess.expires_at < utcnow():
        db.session.delete(sess)
        db.session.commit()
        return None
    return db.session.get(User, sess.user_id)


def _extract_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return None


def login_required(f):
    """本地会话鉴权装饰器：将当前用户注入视图函数首参。"""

    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_user_by_token(_extract_token())
        if user is None:
            return jsonify({'code': 401, 'message': '未登录或登录已失效'}), 401
        return f(user, *args, **kwargs)

    return decorated
