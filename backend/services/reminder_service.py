"""提醒调度服务（Phase 6）。

APScheduler 在后台线程周期性运行 sweep_due_reminders：扫描「即将开始、未取消、有开始时间」
的任务，按每位用户的提前量偏好生成 Reminder 记录（幂等去重）。前端轮询 /api/reminders/pending
拿到未送达提醒后弹出系统通知并回执。
"""
import atexit
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.extensions import db
from app.config import (
    REMINDER_LEAD_MINUTES,
    REMINDER_SWEEP_INTERVAL,
    REMINDER_GRACE_MINUTES,
    REMINDER_MAX_LOOKAHEAD,
    REMINDER_DEFAULT_HOUR,
)
from models.task import StudyTask
from models.reminder import Reminder, ReminderSetting

_scheduler = None


def get_setting(user_id):
    """读取用户提醒设置；无记录时返回默认（开启、提前 10 分钟）。"""
    s = db.session.get(ReminderSetting, user_id)
    if s is None:
        return ReminderSetting(user_id=user_id, enabled=True, lead_minutes=REMINDER_LEAD_MINUTES)
    return s


from utils.time_utils import utcnow


# 中国时区（UTC+8）：StudyTask.date+time 为用户本地时间，sweep 与 now(UTC) 比较前需换算
_LOCAL_UTC_DELTA = timedelta(hours=8)


def _local_to_utc(dt: datetime) -> datetime:
    """本地 naive datetime → UTC naive datetime（按中国时区）。"""
    return dt - _LOCAL_UTC_DELTA


def _create_reminder(task, setting, fire_at_local, rtype: str) -> bool:
    """幂等创建一条提醒；已存在同任务同类型则跳过。返回是否新建。"""
    exists = Reminder.query.filter_by(
        user_id=task.user_id, task_id=task.id, type=rtype
    ).first()
    if exists:
        return False
    db.session.add(Reminder(
        user_id=task.user_id,
        task_id=task.id,
        type=rtype,
        subject=task.subject,
        content=task.content,
        fire_at=fire_at_local,
        lead_minutes=setting.lead_minutes if rtype == Reminder.TYPE_TASK else 0,
    ))
    return True


def sweep_due_reminders():
    """扫描并生成即将开始/即将结束任务的提醒。幂等：同一任务同类型已有提醒则跳过。返回新建数量。

    三类提醒：
    1) 带 start_time 的任务：开始时间 - 提前量 ~ 开始时间 + 宽限 窗口内 → 开始前提醒(task)
    2) 带 end_time 的任务：结束时间 - 5 分钟 ~ 结束时间 + 宽限 窗口内 → 结束时间提醒(task_end)
    3) 仅日期型任务（无具体时刻）：当天整点(REMINDER_DEFAULT_HOUR) 生成一次提醒(task)
    """
    now = utcnow()
    horizon = now + timedelta(minutes=REMINDER_MAX_LOOKAHEAD)

    tasks = (
        StudyTask.query
        .filter(StudyTask.status == StudyTask.STATUS_PENDING)
        .all()
    )

    created = 0
    for t in tasks:
        setting = get_setting(t.user_id)
        if not setting.enabled:
            continue

        if t.start_time is not None:
            local_dt = datetime.combine(t.date, t.start_time)
            task_dt = _local_to_utc(local_dt)  # 与 now(UTC) 同口径比较
            if task_dt > horizon:
                continue
            lead = timedelta(minutes=setting.lead_minutes)
            grace = timedelta(minutes=REMINDER_GRACE_MINUTES)
            if task_dt - lead <= now <= task_dt + grace:
                if _create_reminder(t, setting, local_dt, Reminder.TYPE_TASK):
                    created += 1

        # 结束时间提醒：进入结束前 5 分钟窗口
        if t.end_time is not None:
            local_end = datetime.combine(t.date, t.end_time)
            end_dt = _local_to_utc(local_end)
            grace = timedelta(minutes=REMINDER_GRACE_MINUTES)
            if end_dt - timedelta(minutes=5) <= now <= end_dt + grace:
                if _create_reminder(t, setting, local_end, Reminder.TYPE_TASK_END):
                    created += 1

        # 日期型任务（无 start_time）：当天整点提醒
        if t.start_time is None:
            task_day_start = datetime.combine(t.date, datetime.min.time())
            if not (task_day_start <= now < task_day_start + timedelta(days=1)):
                continue
            local_fire = datetime.combine(t.date, datetime.min.time().replace(hour=REMINDER_DEFAULT_HOUR))
            if _create_reminder(t, setting, local_fire, Reminder.TYPE_TASK):
                created += 1

    if created:
        db.session.commit()
    return created


def _scheduled_job(app):
    with app.app_context():
        try:
            sweep_due_reminders()
        except Exception as e:  # 单轮失败不应拖垮调度器
            app.logger.error(f'提醒扫描失败: {e}')


def start_scheduler(app):
    """启动后台调度器（周期扫描）。进程内单例，重入安全。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _scheduled_job,
        IntervalTrigger(seconds=REMINDER_SWEEP_INTERVAL),
        args=[app],
        id='reminder_sweep',
        replace_existing=True,
    )
    _scheduler.start()
    atexit.register(stop_scheduler)
    return _scheduler


def stop_scheduler():
    """停止并释放调度器。"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
