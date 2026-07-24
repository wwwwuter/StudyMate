from datetime import datetime
from app.extensions import db


class StudyTask(db.Model):
    __tablename__ = 'study_tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    subject = db.Column(db.String(32), nullable=False, comment='科目：数学/英语/政治/408')
    content = db.Column(db.String(512), nullable=False, comment='任务内容')
    start_time = db.Column(db.Time, nullable=True, comment='开始时间')
    end_time = db.Column(db.Time, nullable=True, comment='结束时间')
    status = db.Column(db.String(16), default='pending', comment='pending/done/cancelled')
    plan_source = db.Column(db.String(16), default='manual', comment='manual/excel/json/pdf')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }