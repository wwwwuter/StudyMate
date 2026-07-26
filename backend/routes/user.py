"""用户路由：资料查询与更新。

URL 前缀：/api/user（在 create_app 中注册）
"""
from flask import Blueprint, jsonify, request

from app.extensions import db
from utils.jwt_utils import login_required
from models.user import User

user_bp = Blueprint('user', __name__)

# 允许客户端更新的字段（白名单，防止越权写入 openid 等内部字段）
_EDITABLE_FIELDS = {'nickname', 'avatar', 'phone', 'gender', 'country', 'province', 'city'}


@user_bp.route('/info', methods=['GET'])
@login_required
def get_user_info(current_user):
    """获取当前用户信息。"""
    return jsonify({'code': 200, 'data': current_user.to_dict()})


@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile(current_user):
    """更新当前用户资料（昵称 / 头像 / 手机号 / 性别 / 地区）。"""
    data = request.get_json(silent=True) or {}
    changed = False
    for key, value in data.items():
        if key in _EDITABLE_FIELDS and value is not None:
            setattr(current_user, key, value)
            changed = True
    if changed:
        db.session.commit()
    return jsonify({'code': 200, 'message': '资料已更新', 'data': current_user.to_dict()})
