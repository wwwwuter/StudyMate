from flask import Blueprint, request, jsonify

from utils.jwt_utils import login_required
from services.plan_service import (
    create_task,
    bulk_create,
    get_task,
    list_tasks,
    update_task,
    delete_task,
    import_from_excel,
    import_from_json,
    import_from_pdf,
)

task_bp = Blueprint('task', __name__)


@task_bp.route('', methods=['GET'])
@login_required
def get_tasks(current_user):
    """列出学习任务，支持过滤。

    查询参数：date / start_date / end_date / subject / status / keyword
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
    tasks = list_tasks(current_user.id, filters)
    return jsonify({'code': 200, 'data': [t.to_dict() for t in tasks]})


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


@task_bp.route('/import/excel', methods=['POST'])
@login_required
def import_excel(current_user):
    """从 Excel 导入复习计划。"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400
    try:
        tasks = import_from_excel(current_user.id, request.files['file'])
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {e}'}), 500
    return jsonify({
        'code': 200,
        'message': f'成功导入 {len(tasks)} 条',
        'data': {'count': len(tasks), 'tasks': [t.to_dict() for t in tasks]},
    })


@task_bp.route('/import/json', methods=['POST'])
@login_required
def import_json(current_user):
    """从 JSON 导入复习计划。"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400
    try:
        tasks = import_from_json(current_user.id, request.files['file'])
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {e}'}), 500
    return jsonify({
        'code': 200,
        'message': f'成功导入 {len(tasks)} 条',
        'data': {'count': len(tasks), 'tasks': [t.to_dict() for t in tasks]},
    })


@task_bp.route('/import/pdf', methods=['POST'])
@login_required
def import_pdf(current_user):
    """从 PDF 导入复习计划（需安装 pdfminer.six）。"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400
    try:
        tasks = import_from_pdf(current_user.id, request.files['file'])
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {e}'}), 500
    return jsonify({
        'code': 200,
        'message': f'成功导入 {len(tasks)} 条',
        'data': {'count': len(tasks), 'tasks': [t.to_dict() for t in tasks]},
    })


@task_bp.route('/stats/daily', methods=['GET'])
@login_required
def daily_stats(current_user):
    """某日学习统计（总数/完成数/完成率/涉及科目）。"""
    from datetime import datetime as _dt
    from sqlalchemy import func

    date_str = request.args.get('date', _dt.now().strftime('%Y-%m-%d'))
    try:
        query_date = _dt.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    tasks = list_tasks(current_user.id, {'date': date_str})
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == StudyTask.STATUS_DONE)

    return jsonify({
        'code': 200,
        'data': {
            'date': date_str,
            'total': total,
            'done': done,
            'completion_rate': round(done / total * 100, 1) if total > 0 else 0,
            'subjects': sorted(set(t.subject for t in tasks)),
        },
    })
