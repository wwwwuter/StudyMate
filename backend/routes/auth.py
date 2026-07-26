"""鉴权路由：微信扫码登录、小程序 code 登录、令牌刷新、当前用户。

URL 前缀：/api/auth（在 create_app 中注册）
"""
import requests

from flask import Blueprint, request, jsonify, current_app

from services.auth_service import (
    issue_tokens,
    refresh_tokens,
    find_or_create_user,
    create_qr_ticket,
    confirm_qr_login,
    get_ticket_status,
    AuthError,
)
from services.wechat_service import get_wechat_service, WeChatAPIError
from utils.jwt_utils import login_required

auth_bp = Blueprint('auth', __name__)


def _json():
    return request.get_json(silent=True) or {}


# ---- 小程序 code 直接登录（无需扫码）----
@auth_bp.route('/wechat/login', methods=['POST'])
def wechat_login():
    """小程序 wx.login 拿到 code 直接换令牌。"""
    data = _json()
    code = data.get('code')
    if not code:
        return jsonify({'code': 400, 'message': '缺少授权码 code'}), 400

    wx = get_wechat_service()
    try:
        wx_data = wx.code2session(code)
    except WeChatAPIError as e:
        return jsonify({'code': 502, 'message': '微信授权失败', 'detail': e.detail}), 502
    except requests.RequestException:
        return jsonify({'code': 502, 'message': '微信服务请求失败'}), 502

    openid = wx_data.get('openid')
    user = find_or_create_user(openid, unionid=wx_data.get('unionid'))
    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {'token': issue_tokens(user), 'user': user.to_dict()},
    })


# ---- 桌面端扫码登录 ----
@auth_bp.route('/wechat/qr', methods=['POST'])
def create_qr():
    """生成登录二维码票据。返回 ticket 与二维码内容（前端据此渲染二维码）。"""
    lt, qr_content = create_qr_ticket()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'ticket': lt.ticket,
            'qr_content': qr_content,
            'expire_at': lt.expire_at.strftime('%Y-%m-%d %H:%M:%S'),
        },
    })


@auth_bp.route('/wechat/scan', methods=['POST'])
def scan():
    """配套小程序扫码回调：携带 ticket 与 wx.login 的 code。"""
    data = _json()
    ticket = data.get('ticket')
    code = data.get('code')
    if not ticket or not code:
        return jsonify({'code': 400, 'message': '缺少 ticket 或 code'}), 400
    try:
        confirm_qr_login(ticket, code)
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code
    return jsonify({'code': 200, 'message': '已确认扫码'})


@auth_bp.route('/wechat/qr/status', methods=['GET'])
def qr_status():
    """轮询票据状态。confirmed 时返回令牌与用户信息。"""
    ticket = request.args.get('ticket')
    if not ticket:
        return jsonify({'code': 400, 'message': '缺少 ticket'}), 400
    try:
        result = get_ticket_status(ticket)
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code

    http_code = 200
    if result['status'] == 'expired':
        http_code = 410
    return jsonify({'code': http_code, 'message': 'ok', 'data': result}), http_code


# ---- 令牌刷新 ----
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = _json()
    refresh_token = data.get('refresh_token')
    if not refresh_token:
        return jsonify({'code': 400, 'message': '缺少 refresh_token'}), 400
    try:
        tokens = refresh_tokens(refresh_token)
    except AuthError as e:
        return jsonify({'code': e.code, 'message': e.message}), e.code
    return jsonify({'code': 200, 'message': 'ok', 'data': {'token': tokens}})


# ---- 当前用户 ----
@auth_bp.route('/me', methods=['GET'])
@login_required
def me(current_user):
    return jsonify({'code': 200, 'data': current_user.to_dict()})


# ---- 退出登录（客户端清除本地令牌即可；服务端黑名单留待 Redis 阶段）----
@auth_bp.route('/logout', methods=['POST'])
def logout():
    return jsonify({'code': 200, 'message': '已退出登录（客户端请清除本地 token）'})
