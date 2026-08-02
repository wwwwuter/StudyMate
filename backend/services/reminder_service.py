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


def sweep_due_reminders():
    """扫描并生成即将开始任务的提醒。幂等：同一任务已有提醒则跳过。返回新建数量。

    两类任务都会生成提醒：
    1) 带 start_time 的：按「开始时间 - 提前量 ~ 开始时间 + 宽限」窗口触发。
    2) 仅日期型任务（如艾宾浩斯铺排的学习/复习任务，无具体时刻）：
       以 REMINDER_DEFAULT_HOUR 为触发整点，当天 0 点 ~ 次日 0 点之间均视为「今日待提醒」，
       进入该天即生成一次提醒。
    """
    from utils.time_utils import utcnow

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
            task_dt = datetime.combine(t.date, t.start_time)
            if task_dt > horizon:
                continue
            lead = timedelta(minutes=setting.lead_minutes)
            grace = timedelta(minutes=REMINDER_GRACE_MINUTES)
            if not (task_dt - lead <= now <= task_dt + grace):
                continue
            fire_at = task_dt
        else:
            # 日期型任务：仅当任务日 == 今天 时触发（当天 0 点后生效）
            task_day_start = datetime.combine(t.date, datetime.min.time())
            if not (task_day_start <= now < task_day_start + timedelta(days=1)):
                continue
            fire_at = datetime.combine(t.date, datetime.min.time().replace(hour=REMINDER_DEFAULT_HOUR))

        exists = Reminder.query.filter_by(
            user_id=t.user_id, task_id=t.id, type=Reminder.TYPE_TASK
        ).first()
        if exists:
            continue
        db.session.add(Reminder(
            user_id=t.user_id,
            task_id=t.id,
            type=Reminder.TYPE_TASK,
            subject=t.subject,
            content=t.content,
            fire_at=fire_at,
            lead_minutes=setting.lead_minutes,
        ))
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
