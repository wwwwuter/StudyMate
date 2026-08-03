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

    # 当前任务：今日最早未完成（pending/doing）的任务
    current_task = next((t for t in task_list if t['status'] in ('pending', 'doing')), None)

    return {
        'date': today_iso,
        'study_time': study_time,
        'task_total': task_total,
        'task_completed': task_completed,
        'completion_rate': completion_rate,
        'current_task': current_task,
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
    # 计划执行率：完成任务数 / 计划任务总数（与完成率同源，语义上强调「计划执行」）
    plan_execution_rate = completion_rate

    # 按计划版本（StudyPlan）聚合执行情况
    from models.plan import StudyPlan
    plan_stats = []
    for p in StudyPlan.query.filter_by(user_id=user.id, status=StudyPlan.STATUS_ACTIVE).all():
        pts = StudyTask.query.filter_by(user_id=user.id, plan_id=p.id).all()
        ptot = len(pts)
        pdone = sum(1 for x in pts if x.status == StudyTask.STATUS_DONE)
        plan_stats.append({
            'plan_id': p.id,
            'plan_name': p.name,
            'version': p.version,
            'total': ptot,
            'done': pdone,
            'rate': round(pdone / ptot * 100) if ptot else 0,
        })

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
        'plan_execution_rate': plan_execution_rate,
        'plan_stats': plan_stats,
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


def build_template_advice(stat: dict) -> dict:
    """基于今日统计的规则模板建议（无 AI Key / AI 调用失败时的降级路径）。

    输入为 today_stat() 的返回值，输出 {summary, problems, suggestions}。
    只做确定性规则判断，不依赖任何外部服务，便于单测。
    """
    study_time = stat.get('study_time') or 0
    total = stat.get('task_total') or 0
    done = stat.get('task_completed') or 0
    rate = stat.get('completion_rate') or 0
    subjects = stat.get('subjects') or []
    pomo_time = stat.get('pomodoro_time') or 0

    minutes = round(study_time / 60)

    if study_time == 0 and total == 0:
        return {
            'summary': '今天还没有学习记录。',
            'problems': '暂无任务与计时数据，今日复习尚未开始。',
            'suggestions': '先给自己安排 2-3 项小任务并打开计时器，让复习进入正轨。',
        }

    problems: list[str] = []
    suggestions: list[str] = []

    # 完成率维度
    if total > 0:
        if rate >= 70:
            if rate < 100:
                suggestions.append(f'今天完成率 {rate}%，把剩余任务按优先级快速收尾。')
        elif rate >= 50:
            problems.append(f'任务完成率仅 {rate}%，已过半未完成。')
            suggestions.append('挑 1-2 个最关键的任务优先补完，避免积压到明天。')
        else:
            problems.append(f'任务完成率偏低（{rate}%），大量计划未执行。')
            suggestions.append('今晚补 30 分钟攻克 1 个高优先任务；明天适当减少计划量，先保证完成。')

    # 时长维度
    if study_time == 0:
        problems.append('今天还没有有效的学习时长记录。')
        suggestions.append('打开计时器（任务计时 / 番茄钟）开始学习，数据才会进入统计。')
    elif minutes < 60:
        problems.append(f'今日学习时长仅 {minutes} 分钟，明显偏少。')
        suggestions.append('建议再安排 1-2 个 25-45 分钟的专注块（可开启番茄钟）。')
    elif minutes < 180:
        suggestions.append(f'今日累计 {minutes} 分钟，保持节奏，可再补一个专注块到 3 小时。')
    else:
        suggestions.append(f'今日累计 {minutes} 分钟，时长充足，注意劳逸结合。')

    # 科目均衡维度
    if study_time > 0 and len(subjects) > 1:
        top = subjects[0]
        top_ratio = top.get('time', 0) / study_time
        if top_ratio >= 0.7:
            problems.append(f'学习时间过于集中在「{top["name"]}」（占比 {round(top_ratio * 100)}%）。')
            suggestions.append('明天给薄弱 / 未覆盖科目预留至少一个专注块，保持科目均衡。')

    # 模式维度：没用过番茄钟时给一条引导
    if study_time > 0 and pomo_time == 0:
        suggestions.append('番茄钟专注模式尚未使用，可尝试 25+5 循环提升专注效率。')

    if not problems:
        problems.append('今日执行情况总体良好，暂无明显问题。')
    if not suggestions:
        suggestions.append('保持当前节奏，明日可适当增加一个薄弱科目模块。')

    summary = (
        f'今日复习 {minutes} 分钟，完成任务 {done}/{total}（完成率 {rate}%）。'
        if total
        else f'今日复习 {minutes} 分钟，暂无计划任务。'
    )
    return {
        'summary': summary,
        'problems': '；'.join(problems),
        'suggestions': '；'.join(suggestions),
    }
