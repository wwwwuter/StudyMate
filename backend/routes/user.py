from flask import Blueprint, jsonify
from utils.jwt_utils import login_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/info', methods=['GET'])
@login_required
def get_user_info(current_user):
    """获取当前用户信息"""
    return jsonify({
        'code': 200,
        'data': current_user.to_dict(),
    })