"""学习任务 CRUD 与统计路由。

计划文件的导入统一走 `/api/plans/parse` + `/api/plans/confirm`（AI 解析，
使用用户在「设置」页配置的 Key）。这里不再提供任何绕过 AI 的本地导入入口。
"""
from flask import Blueprint, request, jsonify

from utils.local_auth import login_required
from services.plan_service import (
    create_task,
    bulk_create,
    get_task,
    list_tasks,
    update_task,
    delete_task,
    count_by_criteria,
    delete_by_criteria,
)

task_bp = Blueprint('task', __name__)


@task_bp.route('', methods=['GET'])
@login_required
def get_tasks(current_user):
    """列出学习任务，支持过滤与分页。

    查询参数：date / start_date / end_date / subject / status / keyword
              page / page_size（同时提供时启用分页）
    """
    raw = {
        'date': request.args.get('date'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'subject': request.args.get('subject'),
        'status': request.args.get('status'),
        'keyword': request.args.get('keyword'),
    }
    filters = {k: v for k, v in raw.items() if v}
    try:
        if request.args.get('page'):
            filters['page'] = int(request.args.get('page'))
        if request.args.get('page_size'):
            filters['page_size'] = int(request.args.get('page_size'))
    except (TypeError, ValueError):
        pass

    items, total = list_tasks(current_user.id, filters)
    payload = {'code': 200, 'data': [t.to_dict() for t in items], 'total': total}
    if 'page' in filters and 'page_size' in filters:
        payload['page'] = filters['page']
        payload['page_size'] = filters['page_size']
    return jsonify(payload)


@task_bp.route('', methods=['POST'])
@login_required
def create(current_user):
    """手动创建一条任务（完整字段）。"""
    try:
        task = create_task(current_user.id, request.get_json() or {})
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    return jsonify({'code': 200, 'message': '创建成功', 'data': task.to_dict()}), 201


@task_bp.route('/batch', methods=['POST'])
@login_required
def batch_create(current_user):
    """批量创建任务（JSON 数组）。"""
    items = request.get_json()
    if not isinstance(items, list) or not items:
        return jsonify({'code': 400, 'message': 'body 应为非空任务数组'}), 400
    try:
        tasks = bulk_create(current_user.id, items)
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    return jsonify({
        'code': 200,
        'message': f'成功创建 {len(tasks)} 条',
        'data': [t.to_dict() for t in tasks],
    }), 201


@task_bp.route('/<int:task_id>', methods=['GET'])
@login_required
def get_one(current_user, task_id):
    """获取单条任务详情。"""
    task = get_task(current_user.id, task_id)
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404
    return jsonify({'code': 200, 'data': task.to_dict()})


@task_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update(current_user, task_id):
    """更新任务（date/subject/content/start_time/end_time/status 均可改）。"""
    try:
        task = update_task(current_user.id, task_id, request.get_json() or {})
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404
    return jsonify({'code': 200, 'data': task.to_dict()})


@task_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete(current_user, task_id):
    """删除任务。"""
    if not delete_task(current_user.id, task_id):
        return jsonify({'code': 404, 'message': '任务不存在'}), 404
    return jsonify({'code': 200, 'message': '删除成功'})


@task_bp.route('/batch', methods=['DELETE'])
@login_required
def batch_delete(current_user):
    """批量删除任务。body: {ids:[...]}；仅删除属于当前用户的任务。"""
    data = request.get_json(silent=True) or {}
    ids = data.get('ids')
    if not isinstance(ids, list) or not ids:
        return jsonify({'code': 400, 'message': '请提供要删除的任务 id 数组'}), 400
    ids = [int(i) for i in ids if str(i).isdigit()]
    if not ids:
        return jsonify({'code': 400, 'message': 'ids 格式错误'}), 400
    from services.plan_service import bulk_delete
    deleted = bulk_delete(current_user.id, ids)
    return jsonify({
        'code': 200,
        'message': f'已删除 {deleted} 条计划',
        'data': {'deleted': deleted},
    })


@task_bp.route('/delete-by-criteria/preview', methods=['POST'])
@login_required
def preview_delete_by_criteria(current_user):
    """预览按条件删除将影响的任务数量。body: {subject?, start_date?, end_date?, start_time?, end_time?, status?, plan_source?}"""
    criteria = request.get_json(silent=True) or {}
    try:
        count = count_by_criteria(current_user.id, criteria)
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    return jsonify({'code': 200, 'data': {'count': count}})


@task_bp.route('/delete-by-criteria', methods=['POST'])
@login_required
def delete_by_criteria_route(current_user):
    """按条件批量删除任务。body 同 preview。至少需要一个条件，防止误删全部。"""
    criteria = request.get_json(silent=True) or {}
    try:
        deleted = delete_by_criteria(current_user.id, criteria)
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400
    return jsonify({
        'code': 200,
        'message': f'已删除 {deleted} 条计划',
        'data': {'deleted': deleted},
    })


@task_bp.route('/stats/daily', methods=['GET'])
@login_required
def daily_stats(current_user):
    """某日学习统计（总数/完成数/完成率/涉及科目）。"""
    from datetime import datetime as _dt

    date_str = request.args.get('date', _dt.now().strftime('%Y-%m-%d'))
    try:
        _dt.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    items, _ = list_tasks(current_user.id, {'date': date_str})
    total = len(items)
    done = sum(1 for t in items if t.status == 'done')

    return jsonify({
        'code': 200,
        'data': {
            'date': date_str,
            'total': total,
            'done': done,
            'completion_rate': round(done / total * 100, 1) if total > 0 else 0,
            'subjects': sorted(set(t.subject for t in items)),
        },
    })
