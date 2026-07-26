"""Phase 7 数据分析：学习报告指标聚合。

从计时记录（StudyRecord）与学习计划（StudyTask）中，按时间范围聚合出
「学习报告」所需的全部指标：学习时长、模式/科目分布、每日趋势、时段分布、
任务完成率（计划 vs 实际）、连续打卡天数等。纯计算，不依赖 AI。
"""
from datetime import datetime, date, timedelta

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask


def _range_bounds(range_type, start, end):
    """返回 (start_dt, end_dt)；start=None 表示不限下界。"""
    now = datetime.now()
    if start and end:
        try:
            s = datetime.combine(datetime.strptime(start, '%Y-%m-%d').date(), datetime.min.time())
            e = datetime.combine(datetime.strptime(end, '%Y-%m-%d').date(), datetime.max.time())
            return s, e
        except ValueError:
            pass
    if range_type == 'day':
        return datetime.combine(now.date(), datetime.min.time()), now
    if range_type == 'week':
        monday = now.date() - timedelta(days=now.weekday())
        return datetime.combine(monday, datetime.min.time()), now
    if range_type == 'month':
        first = now.date().replace(day=1)
        return datetime.combine(first, datetime.min.time()), now
    # all
    return None, now


def _compute_streak(user_id):
    """连续打卡天数：以今天（或昨天，若今天尚未学习）为终点向前数连续有记录的天数。"""
    rows = db.session.query(StudyRecord.start_time).filter_by(user_id=user_id).all()
    days = {r[0].date() for r in rows}
    if not days:
        return 0
    d = date.today()
    if d not in days:
        d = d - timedelta(days=1)
        if d not in days:
            return 0
    streak = 0
    while d in days:
        streak += 1
        d = d - timedelta(days=1)
    return streak


def build_report(user_id, range_type='week', start=None, end=None):
    """聚合指定时间范围的学习报告指标。

    返回 dict，含：range/start/end、总时长与时长、模式/科目(实际)分布、
    每日序列、24 小时时段分布、任务完成情况（完成率、计划 vs 实际）、
    连续打卡天数、最佳学习日。
    """
    if range_type not in ('day', 'week', 'month', 'all'):
        range_type = 'week'
    s, e = _range_bounds(range_type, start, end)

    rec_q = StudyRecord.query.filter_by(user_id=user_id)
    if s:
        rec_q = rec_q.filter(StudyRecord.start_time >= s)
    if e:
        rec_q = rec_q.filter(StudyRecord.start_time <= e)
    records = rec_q.all()

    total_seconds = 0
    by_mode: dict[str, int] = {}
    by_subject_actual: dict[str, int] = {}
    daily: dict[str, int] = {}
    hour_dist = {h: 0 for h in range(24)}

    for r in records:
        sec = r.duration or 0
        total_seconds += sec
        by_mode[r.record_type] = by_mode.get(r.record_type, 0) + sec
        if r.subject:
            by_subject_actual[r.subject] = by_subject_actual.get(r.subject, 0) + sec
        day = r.start_time.strftime('%Y-%m-%d')
        daily[day] = daily.get(day, 0) + sec
        hour_dist[r.start_time.hour] = hour_dist.get(r.start_time.hour, 0) + sec

    daily_list = sorted(
        [{'date': k, 'seconds': v} for k, v in daily.items()],
        key=lambda x: x['date'],
    )

    # 同时间段内的任务
    task_q = StudyTask.query.filter_by(user_id=user_id)
    if s:
        task_q = task_q.filter(StudyTask.date >= s.date())
    if e:
        task_q = task_q.filter(StudyTask.date <= e.date())
    tasks = task_q.all()

    total_tasks = len(tasks)
    done_tasks = [t for t in tasks if t.status == StudyTask.STATUS_DONE]
    pending_tasks = [t for t in tasks if t.status != StudyTask.STATUS_DONE]
    completion_rate = round(len(done_tasks) / total_tasks * 100, 1) if total_tasks else 0.0
    planned_minutes = sum((t.estimated_minutes or 0) for t in tasks)

    by_subject_planned: dict[str, int] = {}
    for t in tasks:
        if t.estimated_minutes:
            by_subject_planned[t.subject] = by_subject_planned.get(t.subject, 0) + t.estimated_minutes

    streak = _compute_streak(user_id)
    best_day = max(daily_list, key=lambda x: x['seconds']) if daily_list else None
    avg_session_minutes = round((total_seconds / 60) / len(records), 1) if records else 0
    daily_avg_minutes = round((total_seconds / 60) / len(daily_list), 1) if daily_list else 0

    return {
        'range': range_type,
        'start': s.strftime('%Y-%m-%d') if s else None,
        'end': e.strftime('%Y-%m-%d') if e else None,
        'total_seconds': total_seconds,
        'total_hours': round(total_seconds / 3600, 2),
        'session_count': len(records),
        'avg_session_minutes': avg_session_minutes,
        'daily_avg_minutes': daily_avg_minutes,
        'by_mode': by_mode,
        'by_subject_actual': by_subject_actual,
        'by_subject_planned': by_subject_planned,
        'daily': daily_list,
        'hour_distribution': [{'hour': h, 'seconds': hour_dist[h]} for h in range(24)],
        'tasks': {
            'total': total_tasks,
            'done': len(done_tasks),
            'pending': len(pending_tasks),
            'completion_rate': completion_rate,
            'planned_minutes': planned_minutes,
            'actual_minutes': round(total_seconds / 60),
        },
        'streak': streak,
        'best_day': best_day,
    }
