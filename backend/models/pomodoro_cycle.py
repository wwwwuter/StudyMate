from app.extensions import db
from utils.time_utils import utcnow


class PomodoroCycle(db.Model):
    """番茄钟轮次明细：一次番茄计时（TimerSession）可由多轮组成。

    每一轮记录「专注时长」与「休息时长」。统计学习时长时只累加 focus_duration，
    严禁把 break_duration 计入有效学习时间。
    """

    __tablename__ = 'pomodoro_cycles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timer_session_id = db.Column(
        db.Integer, db.ForeignKey('timer_sessions.id'), nullable=False, index=True,
        comment='所属计时会话',
    )
    cycle_number = db.Column(db.Integer, default=1, comment='第几轮（从 1 开始）')
    focus_duration = db.Column(db.Integer, nullable=False, default=0, comment='专注时长（秒）')
    break_duration = db.Column(db.Integer, nullable=False, default=0, comment='休息时长（秒）')
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'timer_session_id': self.timer_session_id,
            'cycle_number': self.cycle_number,
            'focus_duration': self.focus_duration,
            'break_duration': self.break_duration,
        }
