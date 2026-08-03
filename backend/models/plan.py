"""学习计划（版本化）模型。

StudyPlan 记录「一份上传/创建的学习计划」及其版本：
- 同一份计划文件（同名）多次上传 → version 递增（v1/v2/v3…），旧版本标记 superseded 保留，
  不直接删除，任务历史（StudyTask）始终挂在各自 plan_id 上。
- 新计划确认后，StudyTask.plan_id 指向对应 StudyPlan。
"""
from app.extensions import db
from utils.time_utils import utcnow


class StudyPlan(db.Model):
    __tablename__ = 'study_plans'

    STATUS_ACTIVE = 'active'
    STATUS_SUPERSEDED = 'superseded'
    VALID_STATUSES = (STATUS_ACTIVE, STATUS_SUPERSEDED)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False, comment='计划名称（如 数学强化计划）')
    version = db.Column(db.Integer, default=1, nullable=False, comment='版本号：同名计划 v1/v2…')
    status = db.Column(db.String(16), default=STATUS_ACTIVE, nullable=False, index=True,
                       comment='active / superseded')
    source = db.Column(db.String(16), default='manual', comment='来源：pdf/docx/excel/json/image/manual')
    task_count = db.Column(db.Integer, default=0, comment='该版本任务数快照')
    note = db.Column(db.String(256), nullable=True, comment='备注')
    create_time = db.Column(db.DateTime, default=utcnow)
    update_time = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'version': self.version,
            'status': self.status,
            'source': self.source,
            'task_count': self.task_count,
            'note': self.note,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
            'update_time': self.update_time.strftime('%Y-%m-%d %H:%M:%S') if self.update_time else None,
        }

    @classmethod
    def next_version(cls, user_id: int, name: str) -> int:
        """同名计划的下一个版本号（无同名计划则为 1）。"""
        last = cls.query.filter_by(user_id=user_id, name=name).order_by(cls.version.desc()).first()
        return (last.version + 1) if last else 1

    @classmethod
    def supersede_older(cls, user_id: int, name: str, keep_version: int):
        """把同名计划中非 keep_version 的 active 版本标记为 superseded（历史保留不删除）。"""
        for p in cls.query.filter_by(user_id=user_id, name=name, status=cls.STATUS_ACTIVE).all():
            if p.version != keep_version:
                p.status = cls.STATUS_SUPERSEDED
