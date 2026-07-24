import jwt
import time
from functools import wraps
from flask import request, jsonify, current_app
from models.user import User


def generate_token(user_id, secret, hours=72):
    """生成 JWT token"""
    payload = {
        'user_id': user_id,
        'exp': int(time.time()) + hours * 3600,
        'iat': int(time.time()),
    }
    return jwt.encode(payload, secret, algorithm='HS256')


def login_required(f):
    """JWT 认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({'code': 401, 'message': '未提供认证令牌'}), 401

        try:
            secret = current_app.config['JWT_SECRET']
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            if not current_user:
                return jsonify({'code': 401, 'message': '用户不存在'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': '令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': '无效令牌'}), 401

        return f(current_user, *args, **kwargs)

    return decorated