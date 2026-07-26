from datetime import datetime
from app.extensions import db


class StudyRecord(db.Model):
    __tablename__ = 'study_records'

    # 计时模式（record_type 同时作为模式字段）
    MODE_POMODORO = 'pomodoro'      # 番茄钟（专注段）
    MODE_COUNTUP = 'countup'        # 正计时
    MODE_COUNTDOWN = 'countdown'    # 倒计时
    MODE_FOCUS = 'focus'            # 历史兼容别名（同正计时）
    VALID_MODES = (MODE_POMODORO, MODE_COUNTUP, MODE_COUNTDOWN, MODE_FOCUS)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'), nullable=True, index=True)
    start_time = db.Column(db.DateTime, nullable=False, comment='开始时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='结束时间')
    duration = db.Column(db.Integer, default=0, comment='学习时长（秒）')
    # 模式：pomodoro / countup / countdown / focus
    record_type = db.Column(db.String(16), default=MODE_COUNTUP, comment='计时模式')
    subject = db.Column(db.String(32), nullable=True, comment='关联科目（冗余存储便于统计）')
    # 倒计时目标时长（秒）；正计时/番茄钟为 null
    planned_duration = db.Column(db.Integer, nullable=True, comment='计划时长（秒，倒计时用）')
    note = db.Column(db.String(255), nullable=True, comment='备注')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'duration': self.duration,
            'mode': self.record_type,
            'subject': self.subject,
            'planned_duration': self.planned_duration,
            'note': self.note,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }

    @classmethod
    def is_valid_mode(cls, mode):
        return mode in cls.VALID_MODES
