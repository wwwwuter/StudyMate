"""僵尸计时清理（Phase 6-5）。

场景：用户开始计时后直接关闭电脑/浏览器，TimerSession 永远停在 running，
重启后前端会「恢复」出一个从未结束的会话（如学习 72 小时）。

规则（幂等，可重复调用）：
- 任意模式：running 持续超过 MAX_RUNNING_HOURS（12 小时）→ 自动结束；
- task 模式：超过计划结束时间 MAX_OVERTIME_HOURS（24 小时）→ 自动结束。

**僵尸结束的会话不写入 StudyRecord**（避免污染「额外学习」/「有效学习」统计）——
用户已超过 12h/24h 仍没主动 stop 的话，其 `ended_at - plan_end` 会被错误地记成「额外学习」N 小时，
那不是用户真实投入。僵尸标记 done + duration_seconds=0，由用户的"开始计划"（StudyTask）落库结果为准。
"""
from datetime import timedelta

from app.extensions import db
from models.timer_session import TimerSession
from utils.time_utils import utcnow

MAX_RUNNING_HOURS = 12
MAX_OVERTIME_HOURS = 24


def cleanup_stale_sessions(app, max_running_hours=MAX_RUNNING_HOURS,
                           max_overtime_hours=MAX_OVERTIME_HOURS) -> int:
    """关闭超时的 running 会话（不写入 StudyRecord），返回清理数量。"""
    with app.app_context():
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
            # 仅标记完成，不调用 _sync_session_to_record，避免巨大 extra_duration 污染统计
            s.ended_at = now
            s.status = TimerSession.STATUS_DONE
            s.duration_seconds = 0
            closed += 1
        if closed:
            db.session.commit()
        return closed
