"""本地鉴权路由：账号初始化、登录、获取当前用户、退出。

URL 前缀：/api/auth（在 create_app 中注册）。完全离线，不依赖微信。
"""
from flask import Blueprint, request, jsonify

from services.auth_service import setup_account, register, login, account_exists, AuthError
from utils.local_auth import login_required, destroy_session, create_session
from app.extensions import limiter

auth_bp = Blueprint('auth', __name__)


def _json():
    return request.get_json(silent=True) or {}


@auth_bp.route('/status', methods=['GET'])
def status():
    """前端用于判断该显示「初始化」还是「登录」页。"""
    return jsonify({'code': 200, 'data': {'setup_done': account_exists()}})


@auth_bp.route('/setup', methods=['POST'])
def setup():
    """首次初始化本地账号。"""
    data = _json()
    try:
        user = setup_account(data.get('username', ''), data.get('password', ''))
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code
    return jsonify({
        'code': 200,
        'message': '账号初始化成功',
        'data': {'user': user.to_dict()},
    }), 201


@auth_bp.route('/login', methods=['POST'])
def do_login():
    data = _json()
    try:
        token = login(data.get('username', ''), data.get('password', ''))
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {'token': token, 'user': {'username': data.get('username', '')}},
    })


@auth_bp.route('/register', methods=['POST'])
@limiter.limit('10 per minute')  # 防垃圾注册：单 IP 每分钟最多 10 次
def do_register():
    """开放注册（网站多用户）。成功后直接返回登录令牌。"""
    data = _json()
    try:
        user = register(data.get('username', ''), data.get('password', ''))
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code
    token = create_session(user.id)
    return jsonify({
        'code': 200,
        'message': '注册成功',
        'data': {'token': token, 'user': user.to_dict()},
    }), 201


@auth_bp.route('/me', methods=['GET'])
@login_required
def me(current_user):
    return jsonify({'code': 200, 'data': current_user.to_dict()})


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout(current_user):
    from utils.local_auth import _extract_token
    destroy_session(_extract_token())
    return jsonify({'code': 200, 'message': '已退出登录'})
