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
    """扫描并生成即将开始任务的提醒。幂等：同一任务已有提醒则跳过。返回新建数量。"""
    from utils.time_utils import utcnow

    now = utcnow()
    horizon = now + timedelta(minutes=REMINDER_MAX_LOOKAHEAD)

    tasks = (
        StudyTask.query
        .filter(StudyTask.status == StudyTask.STATUS_PENDING)
        .filter(StudyTask.start_time.isnot(None))
        .all()
    )

    created = 0
    for t in tasks:
        task_dt = datetime.combine(t.date, t.start_time)
        if task_dt > horizon:
            continue
        setting = get_setting(t.user_id)
        if not setting.enabled:
            continue
        lead = timedelta(minutes=setting.lead_minutes)
        grace = timedelta(minutes=REMINDER_GRACE_MINUTES)
        # 提醒窗口：[开始时间 - 提前量, 开始时间 + 宽限]，进入窗口即生成一次
        if not (task_dt - lead <= now <= task_dt + grace):
            continue
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
            fire_at=task_dt,
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
