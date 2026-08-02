"""学习统计计算层（Service）。

只负责统计计算，不处理 HTTP；Route 层调用这些方法后包装成响应信封。

数据源（以当前项目为准）：
- 学习行为时长：StudyRecord（study_records.duration，单位秒）
- 计划 / 任务：StudyTask（study_tasks）

围绕核心闭环：
    AI 解析计划 → 生成每日任务 → 任务提醒 → 启动计时 → 记录学习行为(StudyRecord) → 统计分析
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask
from models.timer_session import TimerSession


def _today() -> date:
    """统计使用的「今天」= UTC 日期，与项目其它统计保持一致。"""
    return date.today()


def _subject_of_record(rec: StudyRecord, cache: dict) -> str:
    """StudyRecord 的科目：优先用冗余字段，否则回查关联任务。"""
    if rec.subject:
        return rec.subject
    if rec.task_id:
        task = cache.get(rec.task_id)
        if task is None:
            task = StudyTask.query.get(rec.task_id)
            cache[rec.task_id] = task
        if task:
            return task.subject
    return '未关联'


def _group_by_subject(records, cache: dict | None = None) -> list[dict]:
    """按科目聚合学习秒数，返回 [{name, time}]，按时间降序。"""
    cache = cache or {}
    by_subject: dict[str, int] = {}
    for r in records:
        name = _subject_of_record(r, cache)
        by_subject[name] = by_subject.get(name, 0) + (r.duration or 0)
    return [
        {'name': k, 'time': v}
        for k, v in sorted(by_subject.items(), key=lambda x: -x[1])
    ]


# 计时模式 → 中文标签（用于前端环形图展示）
_MODE_LABELS = {
    StudyRecord.MODE_POMODORO: '番茄钟',
    StudyRecord.MODE_TASK: '任务计时',
    StudyRecord.MODE_COUNTUP: '自由计时',
    StudyRecord.MODE_COUNTDOWN: '倒计时',
    StudyRecord.MODE_FOCUS: '自由计时',  # 历史别名，并入自由计时
}


def _split_by_mode(records) -> tuple[dict, dict]:
    """按计时模式聚合：返回 (各模式时长 dict, 各模式次数 dict)。

    历史 'focus' 视为 'countup'（自由计时）统计口径，但 key 保留原始值以兼容旧数据。
    """
    time_by_mode: dict[str, int] = {}
    count_by_mode: dict[str, int] = {}
    for r in records:
        m = r.record_type or StudyRecord.MODE_COUNTUP
        time_by_mode[m] = time_by_mode.get(m, 0) + (r.duration or 0)
        count_by_mode[m] = count_by_mode.get(m, 0) + 1
    return time_by_mode, count_by_mode


def _calc_streak(user_id: int) -> int:
    """连续学习天数：从今天往前，逐日检查是否有 StudyRecord。"""
    streak = 0
    cur = _today()
    while True:
        cnt = StudyRecord.query.filter(
            StudyRecord.user_id == user_id,
            func.date(StudyRecord.start_time) == cur.isoformat(),
        ).count()
        if cnt == 0:
            break
        streak += 1
        cur = cur - timedelta(days=1)
    return streak


def today_stat(user) -> dict:
    """今日学习执行情况。"""
    today = _today()
    today_iso = today.isoformat()

    records = StudyRecord.query.filter(
        StudyRecord.user_id == user.id,
        func.date(StudyRecord.start_time) == today_iso,
    ).all()
    study_time = sum((r.duration or 0) for r in records)
    subjects = _group_by_subject(records)
    mode_time, mode_sessions = _split_by_mode(records)
    # 自由计时口径合并历史 'focus'
    free_time = mode_time.get(StudyRecord.MODE_COUNTUP, 0) + mode_time.get(StudyRecord.MODE_FOCUS, 0)
    free_sessions = mode_sessions.get(StudyRecord.MODE_COUNTUP, 0) + mode_sessions.get(StudyRecord.MODE_FOCUS, 0)

    tasks = (
        StudyTask.query.filter_by(user_id=user.id, date=today)
        .order_by(StudyTask.start_time, StudyTask.id)
        .all()
    )
    task_total = len(tasks)
    task_completed = sum(1 for t in tasks if t.status == StudyTask.STATUS_DONE)
    completion_rate = round(task_completed / task_total * 100) if task_total else 0

    running_ids = {
        s.task_id
        for s in TimerSession.query.filter_by(
            user_id=user.id, status=TimerSession.STATUS_RUNNING
        ).all()
        if s.task_id
    }

    task_list = []
    for t in tasks:
        if t.status == StudyTask.STATUS_DONE:
            status = 'done'
        elif t.id in running_ids:
            status = 'doing'
        elif t.date < today:
            status = 'overdue'
        else:
            status = 'pending'
        task_list.append({
            'id': t.id,
            'subject': t.subject,
            'content': t.content,
            'start_time': t.start_time.strftime('%H:%M') if t.start_time else None,
            'end_time': t.end_time.strftime('%H:%M') if t.end_time else None,
            'status': status,
        })

    return {
        'date': today_iso,
        'study_time': study_time,
        'task_total': task_total,
        'task_completed': task_completed,
        'completion_rate': completion_rate,
        'subjects': subjects,
        'tasks': task_list,
        # 计时模式维度
        'pomodoro_time': mode_time.get(StudyRecord.MODE_POMODORO, 0),
        'task_time': mode_time.get(StudyRecord.MODE_TASK, 0),
        'free_time': free_time,
        'sessions': {
            'pomodoro': mode_sessions.get(StudyRecord.MODE_POMODORO, 0),
            'task': mode_sessions.get(StudyRecord.MODE_TASK, 0),
            'countup': free_sessions,
            'countdown': mode_sessions.get(StudyRecord.MODE_COUNTDOWN, 0),
        },
    }


def all_stat(user) -> dict:
    """长期学习情况统计。"""
    records = StudyRecord.query.filter_by(user_id=user.id).all()
    total_time = sum((r.duration or 0) for r in records)
    total_sessions = len(records)
    subjects = _group_by_subject(records)

    tasks = StudyTask.query.filter_by(user_id=user.id).all()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == StudyTask.STATUS_DONE)
    completion_rate = round(completed_tasks / total_tasks * 100) if total_tasks else 0

    continuous_days = _calc_streak(user.id)
    mode_time, mode_sessions = _split_by_mode(records)
    free_time = mode_time.get(StudyRecord.MODE_COUNTUP, 0) + mode_time.get(StudyRecord.MODE_FOCUS, 0)

    # 最近 30 天每日学习分钟（趋势）
    end = _today()
    start = end - timedelta(days=29)
    rows = db.session.query(
        func.date(StudyRecord.start_time),
        func.coalesce(func.sum(StudyRecord.duration), 0),
    ).filter(
        StudyRecord.user_id == user.id,
        StudyRecord.start_time >= datetime.combine(start, datetime.min.time()),
    ).group_by(func.date(StudyRecord.start_time)).all()
    by_day = {str(r[0]): round(r[1] or 0) for r in rows}

    trend = []
    cur = start
    while cur <= end:
        trend.append({'date': cur.strftime('%m-%d'), 'time': by_day.get(cur.isoformat(), 0)})
        cur += timedelta(days=1)

    return {
        'total_time': total_time,
        'total_sessions': total_sessions,
        'completed_tasks': completed_tasks,
        'completion_rate': completion_rate,
        'continuous_days': continuous_days,
        'trend': trend,
        'subjects': subjects,
        # 计时模式维度
        'pomodoro_total': mode_time.get(StudyRecord.MODE_POMODORO, 0),
        'task_total': mode_time.get(StudyRecord.MODE_TASK, 0),
        'countup_total': free_time,
        'countdown_total': mode_time.get(StudyRecord.MODE_COUNTDOWN, 0),
        'mode_distribution': [
            {
                'name': _MODE_LABELS.get(k, k),
                'mode': k,
                'value': v,
                'count': mode_sessions.get(k, 0),
            }
            for k, v in sorted(mode_time.items(), key=lambda x: -x[1])
            if v > 0
        ],
    }
