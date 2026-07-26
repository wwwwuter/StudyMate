from datetime import datetime, date, timedelta

from flask import Blueprint, request, jsonify
from models.record import StudyRecord
from app.extensions import db
from utils.jwt_utils import login_required

record_bp = Blueprint('record', __name__)


@record_bp.route('', methods=['POST'])
@login_required
def start_record(current_user):
    """开始一次计时（番茄钟 / 正计时 / 倒计时）。

    可选字段：mode(pomodoro|countup|countdown)、subject、task_id、planned_duration(秒)、note。
    """
    data = request.get_json(silent=True) or {}
    mode = data.get('mode', StudyRecord.MODE_COUNTUP)
    if not StudyRecord.is_valid_mode(mode):
        return jsonify({'code': 400, 'message': f'非法 mode: {mode}'}), 400

    record = StudyRecord(
        user_id=current_user.id,
        task_id=data.get('task_id'),
        subject=data.get('subject'),
        start_time=datetime.now(),
        record_type=mode,
        planned_duration=data.get('planned_duration'),
        note=(data.get('note') or '')[:255] or None,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({'code': 200, 'data': record.to_dict()}), 201


@record_bp.route('/<int:record_id>/stop', methods=['PUT'])
@login_required
def stop_record(current_user, record_id):
    """停止计时并计算时长（秒）。"""
    record = StudyRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在'}), 404

    record.end_time = datetime.now()
    record.duration = int((record.end_time - record.start_time).total_seconds())
    db.session.commit()
    return jsonify({'code': 200, 'data': record.to_dict()})


@record_bp.route('/<int:record_id>', methods=['DELETE'])
@login_required
def delete_record(current_user, record_id):
    """删除一条计时记录。"""
    record = StudyRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    if not record:
        return jsonify({'code': 404, 'message': '记录不存在'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'code': 200, 'message': '已删除'})


@record_bp.route('/history', methods=['GET'])
@login_required
def get_history(current_user):
    """获取历史记录，支持 mode/subject/date/task_id 过滤与分页。"""
    query = StudyRecord.query.filter_by(user_id=current_user.id)

    if request.args.get('mode'):
        query = query.filter_by(record_type=request.args['mode'])
    if request.args.get('subject'):
        query = query.filter_by(subject=request.args['subject'])
    if request.args.get('task_id'):
        query = query.filter_by(task_id=request.args['task_id'])

    date_str = request.args.get('date')
    if date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(
                StudyRecord.start_time >= datetime.combine(d, datetime.min.time()),
                StudyRecord.start_time < datetime.combine(d, datetime.max.time()),
            )
        except ValueError:
            return jsonify({'code': 400, 'message': '日期格式错误'}), 400

    query = query.order_by(StudyRecord.start_time.desc())

    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
    except ValueError:
        page, page_size = 1, 50
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 50

    total = query.count()
    records = query.offset((page - 1) * page_size).limit(page_size).all()
    return jsonify({
        'code': 200,
        'data': [r.to_dict() for r in records],
        'total': total,
        'page': page,
        'page_size': page_size,
    })


@record_bp.route('/stats', methods=['GET'])
@login_required
def records_stats(current_user):
    """计时统计：总时长、按模式、按科目、按日聚合（用于图表）。

    range 参数：day(今天) / week(本周) / month(本月) / all(全部)，默认 week。
    """
    range_type = request.args.get('range', 'week')

    query = StudyRecord.query.filter_by(user_id=current_user.id)
    now = datetime.now()

    if range_type == 'day':
        start = datetime.combine(now.date(), datetime.min.time())
        query = query.filter(StudyRecord.start_time >= start)
    elif range_type == 'week':
        monday = now.date() - timedelta(days=now.weekday())
        start = datetime.combine(monday, datetime.min.time())
        query = query.filter(StudyRecord.start_time >= start)
    elif range_type == 'month':
        first = now.date().replace(day=1)
        start = datetime.combine(first, datetime.min.time())
        query = query.filter(StudyRecord.start_time >= start)

    records = query.all()

    total_seconds = sum((r.duration or 0) for r in records)
    by_mode: dict[str, int] = {}
    by_subject: dict[str, int] = {}
    daily: dict[str, int] = {}

    for r in records:
        sec = r.duration or 0
        by_mode[r.record_type] = by_mode.get(r.record_type, 0) + sec
        if r.subject:
            by_subject[r.subject] = by_subject.get(r.subject, 0) + sec
        day = r.start_time.strftime('%Y-%m-%d')
        daily[day] = daily.get(day, 0) + sec

    daily_list = [{'date': k, 'seconds': v} for k, v in sorted(daily.items())]

    return jsonify({
        'code': 200,
        'data': {
            'range': range_type,
            'total_seconds': total_seconds,
            'total_hours': round(total_seconds / 3600, 2),
            'session_count': len(records),
            'by_mode': by_mode,
            'by_subject': by_subject,
            'daily': daily_list,
        },
    })


@record_bp.route('/stats/weekly', methods=['GET'])
@login_required
def weekly_stats(current_user):
    """获取本周统计（向后兼容旧接口）。"""
    from datetime import timedelta as _td
    today = date.today()
    monday = today - _td(days=today.weekday())

    week_records = StudyRecord.query.filter(
        StudyRecord.user_id == current_user.id,
        StudyRecord.start_time >= datetime.combine(monday, datetime.min.time()),
        StudyRecord.start_time < datetime.combine(today + _td(days=1), datetime.min.time()),
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
