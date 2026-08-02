"""用户路由：资料查询与更新。

URL 前缀：/api/user（在 create_app 中注册）
"""
from flask import Blueprint, jsonify, request

from app.extensions import db
from utils.local_auth import login_required
from models.user import User

user_bp = Blueprint('user', __name__)


@user_bp.route('/info', methods=['GET'])
@login_required
def get_user_info(current_user):
    """获取当前用户信息。"""
    return jsonify({'code': 200, 'data': current_user.to_dict()})


@user_bp.route('/password', methods=['PUT'])
@login_required
def change_password(current_user):
    """修改本地账号密码。body: { old_password, new_password }。"""
    data = request.get_json(silent=True) or {}
    old_p = data.get('old_password', '')
    new_p = data.get('new_password', '')
    if not current_user.check_password(old_p):
        return jsonify({'code': 400, 'message': '原密码错误'}), 400
    if len(new_p) < 6:
        return jsonify({'code': 400, 'message': '新密码至少 6 位'}), 400
    current_user.password_hash, current_user.salt = User.hash_password(new_p)
    db.session.commit()
    return jsonify({'code': 200, 'message': '密码已修改'})
