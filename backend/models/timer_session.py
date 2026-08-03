from app.extensions import db
from utils.time_utils import utcnow


class TimerSession(db.Model):
    """计时会话：用户针对某条计划（study_tasks）开启的一次专注计时。

    状态：running=计时中 / done=已结束 / cancelled=已取消。
    到点自动开启计时由前端调度器触发（调用 /api/timer/start）。
    """

    __tablename__ = 'timer_sessions'

    STATUS_RUNNING = 'running'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'

    # 计时模式
    MODE_POMODORO = 'pomodoro'    # 番茄钟（只统计专注段）
    MODE_TASK = 'task'            # 任务计时（绑定 study_tasks）
    MODE_COUNTUP = 'countup'      # 自由正计时
    MODE_COUNTDOWN = 'countdown'  # 倒计时
    DEFAULT_MODE = MODE_COUNTUP
    VALID_MODES = (MODE_POMODORO, MODE_TASK, MODE_COUNTUP, MODE_COUNTDOWN)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'), nullable=True, index=True,
                        comment='关联计划（study_tasks.id），手动计时可为空')
    mode = db.Column(db.String(20), default=DEFAULT_MODE, nullable=False, index=True,
                     comment='计时模式：pomodoro/task/countup/countdown')
    # 计划时间段（task 模式：取自关联 StudyTask 的 start/end 时间，用于「计划倒计时」）
    plan_start_time = db.Column(db.DateTime, nullable=True, comment='计划开始时间（task 模式）')
    plan_end_time = db.Column(db.DateTime, nullable=True, comment='计划结束时间（task 模式）')
    started_at = db.Column(db.DateTime, nullable=False, comment='实际开始时刻')
    ended_at = db.Column(db.DateTime, nullable=True, comment='结束时刻（done/cancelled 时填充）')
    duration_seconds = db.Column(db.Integer, nullable=True, comment='时长（秒），结束时计算')
    status = db.Column(db.String(16), default=STATUS_RUNNING, comment='running/done/cancelled')
    note = db.Column(db.String(256), nullable=True, comment='备注（如手动计时主题）')
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'mode': self.mode,
            # 明确返回 UTC ISO-8601，避免前端把 naive 字符串当成本地时间
            'started_at': self.started_at.strftime('%Y-%m-%dT%H:%M:%SZ') if self.started_at else None,
            'ended_at': self.ended_at.strftime('%Y-%m-%dT%H:%M:%SZ') if self.ended_at else None,
            'plan_start_time': self.plan_start_time.strftime('%Y-%m-%dT%H:%M:%SZ') if self.plan_start_time else None,
            'plan_end_time': self.plan_end_time.strftime('%Y-%m-%dT%H:%M:%SZ') if self.plan_end_time else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status,
            'note': self.note,
        }

    @classmethod
    def is_valid_status(cls, status):
        return status in (cls.STATUS_RUNNING, cls.STATUS_DONE, cls.STATUS_CANCELLED)
