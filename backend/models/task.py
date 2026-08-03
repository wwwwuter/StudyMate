from app.extensions import db
from utils.time_utils import utcnow


class StudyTask(db.Model):
    __tablename__ = 'study_tasks'

    # 任务状态枚举
    STATUS_PENDING = 'pending'      # 未开始
    STATUS_RUNNING = 'running'      # 学习中（已开始计时）
    STATUS_DONE = 'done'            # 已完成
    STATUS_CANCELLED = 'cancelled'  # 已取消
    STATUS_EXPIRED = 'expired'      # 超过计划时间段（未按时完成）
    VALID_STATUSES = (STATUS_PENDING, STATUS_RUNNING, STATUS_DONE, STATUS_CANCELLED, STATUS_EXPIRED)

    # 计划来源枚举（用于区分手动录入与各类导入）
    SOURCE_MANUAL = 'manual'
    SOURCE_EXCEL = 'excel'
    SOURCE_JSON = 'json'
    SOURCE_PDF = 'pdf'
    SOURCE_DOCX = 'docx'
    SOURCE_PARSED = 'parsed'
    SOURCE_AUTO = 'auto'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # 所属计划版本（study_plans.id）；手动录入/旧数据为 null
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plans.id'), nullable=True, index=True,
                        comment='所属计划版本（study_plans.id）')
    date = db.Column(db.Date, nullable=False, index=True)
    subject = db.Column(db.String(32), nullable=False, comment='科目：数学/英语/政治/408')
    content = db.Column(db.String(512), nullable=False, comment='任务内容')
    start_time = db.Column(db.Time, nullable=True, comment='开始时间')
    end_time = db.Column(db.Time, nullable=True, comment='结束时间')
    status = db.Column(db.String(16), default=STATUS_PENDING, comment='pending/done/cancelled')
    plan_source = db.Column(db.String(16), default=SOURCE_MANUAL, comment='manual/excel/json/pdf/docx/parsed/auto')
    # 字段扩展（Phase 5 升级方向 U5）
    priority = db.Column(db.Integer, default=0, comment='优先级：0 普通 / 1 高 / 2 紧急')
    estimated_minutes = db.Column(db.Integer, nullable=True, comment='预估时长（分钟）')
    tags = db.Column(db.String(128), nullable=True, comment='标签，逗号分隔')
    # 艾宾浩斯智能排程（M2）
    # review_round: 0=首次学习, 1..N=第 N 次复习（按间隔自动生成）
    review_round = db.Column(db.Integer, default=0, nullable=False, index=True,
                             comment='0=首次学习；1..N=第 N 次复习')
    # root_task_id: 指向同一内容的首次学习任务（round 0），用于串联复习链
    root_task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'),
                             nullable=True, index=True, comment='复习链的首次任务 id')
    create_time = db.Column(db.DateTime, default=utcnow)
    update_time = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
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
            'review_round': self.review_round,
            'root_task_id': self.root_task_id,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }

    @classmethod
    def is_valid_status(cls, status):
        return status in cls.VALID_STATUSES
