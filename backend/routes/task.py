from datetime import datetime, date
from flask import Blueprint, request, jsonify
from models.task import StudyTask
from app.extensions import db
from utils.jwt_utils import login_required
from parser.excel_parser import parse_excel_tasks
from parser.json_parser import parse_json_tasks
from parser.pdf_parser import parse_pdf_tasks

task_bp = Blueprint('task', __name__)


@task_bp.route('', methods=['GET'])
@login_required
def get_tasks(current_user):
    """获取任务列表，支持按日期筛选"""
    date_str = request.args.get('date')
    query = StudyTask.query.filter_by(user_id=current_user.id)

    if date_str:
        try:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(date=query_date)
        except ValueError:
            return jsonify({'code': 400, 'message': '日期格式错误，应为 YYYY-MM-DD'}), 400

    tasks = query.order_by(StudyTask.date, StudyTask.start_time).all()
    return jsonify({
        'code': 200,
        'data': [t.to_dict() for t in tasks],
    })


@task_bp.route('', methods=['POST'])
@login_required
def create_task(current_user):
    """手动创建任务"""
    data = request.get_json()
    required = ['date', 'subject', 'content']
    for field in required:
        if field not in data:
            return jsonify({'code': 400, 'message': f'缺少必填字段: {field}'}), 400

    try:
        task_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    task = StudyTask(
        user_id=current_user.id,
        date=task_date,
        subject=data['subject'],
        content=data['content'],
        start_time=datetime.strptime(data.get('start_time', ''), '%H:%M').time() if data.get('start_time') else None,
        end_time=datetime.strptime(data.get('end_time', ''), '%H:%M').time() if data.get('end_time') else None,
        status='pending',
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'code': 200, 'message': '创建成功', 'data': task.to_dict()}), 201


@task_bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(current_user, task_id):
    """更新任务状态"""
    task = StudyTask.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    data = request.get_json()
    if 'status' in data:
        task.status = data['status']
    if 'content' in data:
        task.content = data['content']
    db.session.commit()
    return jsonify({'code': 200, 'data': task.to_dict()})


@task_bp.route('/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(current_user, task_id):
    """删除任务"""
    task = StudyTask.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'code': 404, 'message': '任务不存在'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'code': 200, 'message': '删除成功'})


@task_bp.route('/import/excel', methods=['POST'])
@login_required
def import_excel(current_user):
    """导入 Excel 计划"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400

    file = request.files['file']
    try:
        tasks = parse_excel_tasks(file, current_user.id)
        for task in tasks:
            db.session.add(task)
        db.session.commit()
        return jsonify({'code': 200, 'message': f'成功导入 {len(tasks)} 条任务', 'count': len(tasks)})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {str(e)}'}), 500


@task_bp.route('/import/json', methods=['POST'])
@login_required
def import_json(current_user):
    """导入 JSON 计划"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400

    file = request.files['file']
    try:
        tasks = parse_json_tasks(file, current_user.id)
        for task in tasks:
            db.session.add(task)
        db.session.commit()
        return jsonify({'code': 200, 'message': f'成功导入 {len(tasks)} 条任务', 'count': len(tasks)})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {str(e)}'}), 500


@task_bp.route('/import/pdf', methods=['POST'])
@login_required
def import_pdf(current_user):
    """导入 PDF 计划"""
    if 'file' not in request.files:
        return jsonify({'code': 400, 'message': '请上传文件'}), 400

    file = request.files['file']
    try:
        tasks = parse_pdf_tasks(file, current_user.id)
        for task in tasks:
            db.session.add(task)
        db.session.commit()
        return jsonify({'code': 200, 'message': f'成功导入 {len(tasks)} 条任务', 'count': len(tasks)})
    except Exception as e:
        return jsonify({'code': 500, 'message': f'导入失败: {str(e)}'}), 500


@task_bp.route('/stats/daily', methods=['GET'])
@login_required
def daily_stats(current_user):
    """获取每日统计"""
    from sqlalchemy import func

    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    tasks = StudyTask.query.filter_by(user_id=current_user.id, date=query_date).all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == 'done')

    return jsonify({
        'code': 200,
        'data': {
            'date': date_str,
            'total': total,
            'done': done,
            'completion_rate': round(done / total * 100, 1) if total > 0 else 0,
            'subjects': list(set(t.subject for t in tasks)),
        }
    })