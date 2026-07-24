from datetime import datetime
from app.extensions import db


class StudyRecord(db.Model):
    __tablename__ = 'study_records'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False, comment='开始时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='结束时间')
    duration = db.Column(db.Integer, default=0, comment='学习时长（秒）')
    record_type = db.Column(db.String(16), default='focus', comment='pomodoro/countdown/focus')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'duration': self.duration,
            'record_type': self.record_type,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }