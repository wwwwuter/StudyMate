"""学习统计接口（Route 层，仅负责接口，计算交给 stat_service）。

GET /api/stat/today   今日学习执行情况
GET /api/stat/all     长期学习情况统计
"""
from flask import Blueprint, jsonify

from utils.local_auth import login_required
from services.stat_service import today_stat, all_stat

stat_bp = Blueprint('stat', __name__)


@stat_bp.route('/today', methods=['GET'])
@login_required
def stat_today(current_user):
    return jsonify({'code': 200, 'data': today_stat(current_user)})


@stat_bp.route('/all', methods=['GET'])
@login_required
def stat_all(current_user):
    return jsonify({'code': 200, 'data': all_stat(current_user)})
