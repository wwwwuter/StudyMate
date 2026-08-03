from datetime import datetime
from app.extensions import db


class StudyRecord(db.Model):
    __tablename__ = 'study_records'

    # 计时模式（record_type 同时作为模式字段）
    MODE_POMODORO = 'pomodoro'      # 番茄钟（专注段）
    MODE_TASK = 'task'              # 任务计时（绑定 study_tasks）
    MODE_COUNTUP = 'countup'        # 正计时 / 自由计时
    MODE_COUNTDOWN = 'countdown'    # 倒计时
    MODE_FOCUS = 'focus'            # 历史兼容别名（同正计时）
    VALID_MODES = (MODE_POMODORO, MODE_TASK, MODE_COUNTUP, MODE_COUNTDOWN, MODE_FOCUS)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('study_tasks.id'), nullable=True, index=True)
    start_time = db.Column(db.DateTime, nullable=False, comment='实际开始时间（用户点击开始）')
    end_time = db.Column(db.DateTime, nullable=True, comment='实际结束时间（用户点击结束）')
    # 真实计时时长（秒）：actual_end - actual_start（含计划外部分，用于行为分析）
    duration = db.Column(db.Integer, default=0, comment='真实计时时长(秒)：actual_end-actual_start')
    # 计划有效学习时长（秒）：min(actual_end, plan_end) - actual_start，统计/完成度用
    effective_duration = db.Column(db.Integer, default=0, comment='计划有效学习时长(秒)，统计用')
    # 计划外额外学习时长（秒）：actual_end - plan_end（正向行为，单独统计）
    extra_duration = db.Column(db.Integer, default=0, comment='计划外额外学习时长(秒)')
    # 模式：pomodoro / countup / countdown / focus
    record_type = db.Column(db.String(16), default=MODE_COUNTUP, comment='计时模式')
    subject = db.Column(db.String(32), nullable=True, comment='关联科目（冗余存储便于统计）')
    # 计划安排时长（秒）：task 模式 = plan_end-plan_start；countdown = 目标倒计时时长
    planned_duration = db.Column(db.Integer, nullable=True, comment='计划安排时长(秒)')
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
            'effective_duration': self.effective_duration,
            'extra_duration': self.extra_duration,
            'mode': self.record_type,
            'subject': self.subject,
            'planned_duration': self.planned_duration,
            'note': self.note,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }

    @classmethod
    def is_valid_mode(cls, mode):
        return mode in cls.VALID_MODES
