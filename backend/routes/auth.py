import requests
from flask import Blueprint, request, jsonify, current_app
from models.user import User
from app.extensions import db
from utils.jwt_utils import generate_token

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/wechat', methods=['POST'])
def wechat_login():
    """微信登录"""
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'code': 400, 'message': '缺少授权码'}), 400

    code = data['code']
    app_id = current_app.config['WECHAT_APP_ID']
    app_secret = current_app.config['WECHAT_APP_SECRET']

    # 向微信服务器换取 openid
    wx_url = (
        f"https://api.weixin.qq.com/sns/jscode2session"
        f"?appid={app_id}&secret={app_secret}&js_code={code}&grant_type=authorization_code"
    )

    try:
        resp = requests.get(wx_url, timeout=10)
        wx_data = resp.json()
    except Exception as e:
        current_app.logger.error(f"微信登录请求失败: {e}")
        return jsonify({'code': 502, 'message': '微信服务请求失败'}), 502

    if 'openid' not in wx_data:
        return jsonify({'code': 401, 'message': '微信授权失败', 'detail': wx_data}), 401

    openid = wx_data['openid']
    # 查找或创建用户
    user = User.query.filter_by(openid=openid).first()
    if not user:
        user = User(openid=openid)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"新用户注册: {openid}")

    token = generate_token(user.id, current_app.config['JWT_SECRET'],
                           current_app.config['JWT_EXPIRATION_HOURS'])

    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': user.to_dict(),
        }
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """退出登录（客户端清除 token 即可）"""
    return jsonify({'code': 200, 'message': '已退出登录'})