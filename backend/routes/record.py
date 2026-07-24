from datetime import datetime
from flask import Blueprint, request, jsonify
from models.record import StudyRecord
from app.extensions import db
from utils.jwt_utils import login_required

record_bp = Blueprint('record', __name__)


@record_bp.route('', methods=['POST'])
@login_required
def start_record(current_user):
    """开始计时"""
    data = request.get_json()
    record = StudyRecord(
        user_id=current_user.id,
        task_id=data.get('task_id'),
        start_time=datetime.now(),
        record_type=data.get('record_type', 'focus'),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'code': 200, 'data': record.to_dict()}), 201


@record_bp.route('/<int:record_id>/stop', methods=['PUT'])
@login_required
def stop_record(current_user, record_id):
    """停止计时"""
    record = StudyRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在'}), 404

    record.end_time = datetime.now()
    record.duration = int((record.end_time - record.start_time).total_seconds())
    db.session.commit()
    return jsonify({'code': 200, 'data': record.to_dict()})


@record_bp.route('/history', methods=['GET'])
@login_required
def get_history(current_user):
    """获取历史记录"""
    date_str = request.args.get('date')
    query = StudyRecord.query.filter_by(user_id=current_user.id)

    if date_str:
        try:
            from datetime import date
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(
                StudyRecord.start_time >= datetime.combine(query_date, datetime.min.time()),
                StudyRecord.start_time < datetime.combine(query_date, datetime.max.time()),
            )
        except ValueError:
            return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    records = query.order_by(StudyRecord.start_time.desc()).all()
    return jsonify({
        'code': 200,
        'data': [r.to_dict() for r in records],
    })


@record_bp.route('/stats/weekly', methods=['GET'])
@login_required
def weekly_stats(current_user):
    """获取本周统计"""
    from datetime import date, timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    week_records = StudyRecord.query.filter(
        StudyRecord.user_id == current_user.id,
        StudyRecord.start_time >= datetime.combine(monday, datetime.min.time()),
        StudyRecord.start_time < datetime.combine(today + timedelta(days=1), datetime.min.time()),
    ).all()

    total_seconds = sum(r.duration for r in week_records if r.duration)
    daily_data = {}
    for r in week_records:
        day = r.start_time.strftime('%Y-%m-%d')
        daily_data[day] = daily_data.get(day, 0) + (r.duration or 0)

    return jsonify({
        'code': 200,
        'data': {
            'total_hours': round(total_seconds / 3600, 1),
            'total_days': len(daily_data),
            'daily_seconds': daily_data,
        }
    })