from app.extensions import db
from utils.time_utils import utcnow


class StudyTask(db.Model):
    __tablename__ = 'study_tasks'

    # 任务状态枚举
    STATUS_PENDING = 'pending'
    STATUS_DONE = 'done'
    STATUS_CANCELLED = 'cancelled'
    VALID_STATUSES = (STATUS_PENDING, STATUS_DONE, STATUS_CANCELLED)

    # 计划来源枚举（用于区分手动录入与各类导入）
    SOURCE_MANUAL = 'manual'
    SOURCE_EXCEL = 'excel'
    SOURCE_JSON = 'json'
    SOURCE_PDF = 'pdf'
    SOURCE_AUTO = 'auto'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    subject = db.Column(db.String(32), nullable=False, comment='科目：数学/英语/政治/408')
    content = db.Column(db.String(512), nullable=False, comment='任务内容')
    start_time = db.Column(db.Time, nullable=True, comment='开始时间')
    end_time = db.Column(db.Time, nullable=True, comment='结束时间')
    status = db.Column(db.String(16), default=STATUS_PENDING, comment='pending/done/cancelled')
    plan_source = db.Column(db.String(16), default=SOURCE_MANUAL, comment='manual/excel/json/pdf/auto')
    # 字段扩展（Phase 5 升级方向 U5）
    priority = db.Column(db.Integer, default=0, comment='优先级：0 普通 / 1 高 / 2 紧急')
    estimated_minutes = db.Column(db.Integer, nullable=True, comment='预估时长（分钟）')
    tags = db.Column(db.String(128), nullable=True, comment='标签，逗号分隔')
    create_time = db.Column(db.DateTime, default=utcnow)
    update_time = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date.strftime('%Y-%m-%d') if self.date else None,
            'subject': self.subject,
            'content': self.content,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'status': self.status,
            'plan_source': self.plan_source,
            'priority': self.priority,
            'estimated_minutes': self.estimated_minutes,
            'tags': self.tags,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }

    @classmethod
    def is_valid_status(cls, status):
        return status in cls.VALID_STATUSES
