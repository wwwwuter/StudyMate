"""僵尸计时清理（Phase 6-5）。

场景：用户开始计时后直接关闭电脑/浏览器，TimerSession 永远停在 running，
重启后前端会「恢复」出一个从未结束的会话（如学习 72 小时）。

规则（幂等，可重复调用）：
- 任意模式：running 持续超过 MAX_RUNNING_HOURS（12 小时）→ 自动结束并落库；
- task 模式：超过计划结束时间 MAX_OVERTIME_HOURS（24 小时）→ 自动结束并落库。

结束路径与用户手动结束一致（_sync_session_to_record），保证统计口径统一。
"""
from datetime import timedelta

from app.extensions import db
from models.timer_session import TimerSession
from utils.time_utils import utcnow

MAX_RUNNING_HOURS = 12
MAX_OVERTIME_HOURS = 24


def cleanup_stale_sessions(app, max_running_hours=MAX_RUNNING_HOURS,
                           max_overtime_hours=MAX_OVERTIME_HOURS) -> int:
    """关闭超时的 running 会话并写入 StudyRecord，返回清理数量。"""
    with app.app_context():
        # 函数内 import：避免 reminder_service → scheduler → routes.plan → reminder_service 循环
        from routes.plan import _effective_duration, _sync_session_to_record

        now = utcnow()
        running = TimerSession.query.filter_by(status=TimerSession.STATUS_RUNNING).all()
        closed = 0
        for s in running:
            overdue = False
            if s.started_at and (now - s.started_at) > timedelta(hours=max_running_hours):
                overdue = True
            if (not overdue and s.mode == TimerSession.MODE_TASK
                    and s.plan_end_time
                    and (now - s.plan_end_time) > timedelta(hours=max_overtime_hours)):
                overdue = True
            if not overdue:
                continue
            s.ended_at = now
            s.status = TimerSession.STATUS_DONE
            s.duration_seconds = _effective_duration(s)
            _sync_session_to_record(s)
            closed += 1
        if closed:
            db.session.commit()
        return closed
