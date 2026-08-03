from app.extensions import db
from utils.time_utils import utcnow


class Reminder(db.Model):
    """任务提醒：开始前提醒（task）+ 结束时间提醒（task_end）。由 APScheduler 扫描生成，
    前端轮询后弹出系统通知。"""

    __tablename__ = 'reminders'

    TYPE_TASK = 'task'          # 任务开始前提醒（含提前量）
    TYPE_TASK_END = 'task_end'  # 任务结束时间提醒

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'), nullable=True, index=True)
    type = db.Column(db.String(16), default=TYPE_TASK, comment='提醒类型：task=任务开始前')
    subject = db.Column(db.String(32), nullable=False, comment='科目')
    content = db.Column(db.String(512), nullable=False, comment='任务内容')
    fire_at = db.Column(db.DateTime, nullable=False, comment='任务开始时间（提醒指向的时刻）')
    lead_minutes = db.Column(db.Integer, default=10, comment='提前提醒分钟数')
    delivered = db.Column(db.Boolean, default=False, index=True, comment='是否已送达（前端已弹通知）')
    delivered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'type': self.type,
            'subject': self.subject,
            'content': self.content,
            'fire_at': self.fire_at.strftime('%Y-%m-%d %H:%M') if self.fire_at else None,
            'lead_minutes': self.lead_minutes,
            'delivered': self.delivered,
        }


class ReminderSetting(db.Model):
    """每位用户的提醒偏好（全局唯一一行）。"""

    __tablename__ = 'reminder_settings'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    enabled = db.Column(db.Boolean, default=True, comment='是否开启任务开始前提醒')
    lead_minutes = db.Column(db.Integer, default=10, comment='提前提醒分钟数（任务开始前 N 分钟）')
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
