"""排程相关路由（M2）。

- POST /api/schedule/generate  按清单整体排程（首次学习 + 艾宾浩斯复习）
- GET  /api/schedule/chain/<id> 取某内容的完整复习链
- GET  /api/schedule/upcoming   取某区间内的复习任务（课表/提醒用）
"""
from flask import Blueprint, request, jsonify
from datetime import date

from utils.local_auth import login_required
from services.scheduler import (
    generate_schedule,
    get_review_chain,
    get_upcoming_reviews,
    EBBINGHAUS_INTERVALS,
    round_label,
)
from services.plan_service import _parse_date

schedule_bp = Blueprint('schedule', __name__)


@schedule_bp.route('/generate', methods=['POST'])
@login_required
def generate(current_user):
    """按清单整体排程；body: { items: [{subject,content,priority?}], study_date?: 'YYYY-MM-DD' }。"""
    body = request.get_json(silent=True) or {}
    items = body.get('items')
    if not isinstance(items, list) or not items:
        return jsonify({'code': 400, 'message': 'items 应为非空数组'}), 400
    study_date = body.get('study_date')
    try:
        created, skipped = generate_schedule(current_user.id, items, study_date)
    except Exception as e:
        return jsonify({'code': 500, 'message': f'排程失败: {e}'}), 500
    return jsonify({
        'code': 200,
        'message': f'已排程 {len(created)} 条任务（跳过 {skipped} 条无效）',
        'data': {
            'count': len(created),
            'skipped': skipped,
            'intervals': EBBINGHAUS_INTERVALS,
            'tasks': [t.to_dict() for t in created],
        },
    }), 201


@schedule_bp.route('/chain/<int:root_task_id>', methods=['GET'])
@login_required
def chain(current_user, root_task_id):
    """取某内容的完整复习链。"""
    tasks = get_review_chain(current_user.id, root_task_id)
    if not tasks:
        return jsonify({'code': 404, 'message': '复习链不存在'}), 404
    return jsonify({
        'code': 200,
        'data': {
            'root_task_id': root_task_id,
            'tasks': [t.to_dict() for t in tasks],
        },
    })


@schedule_bp.route('/upcoming', methods=['GET'])
@login_required
def upcoming(current_user):
    """区间内（含）的复习任务；查询参数 start / end（YYYY-MM-DD）。"""
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    start = _parse_date(start_str) if start_str else date.today()
    end = _parse_date(end_str) if end_str else start
    if start is None or end is None:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400
    tasks = get_upcoming_reviews(current_user.id, start, end)
    return jsonify({
        'code': 200,
        'data': {
            'start': start.strftime('%Y-%m-%d'),
            'end': end.strftime('%Y-%m-%d'),
            'count': len(tasks),
            # 附轮次标签，前端直接取用
            'tasks': [{**t.to_dict(), 'round_label': round_label(t.review_round)} for t in tasks],
        },
    })
