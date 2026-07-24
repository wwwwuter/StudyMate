from datetime import datetime
from app.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(64), default='')
    avatar = db.Column(db.String(256), default='')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    tasks = db.relationship('StudyTask', backref='user', lazy='dynamic')
    records = db.relationship('StudyRecord', backref='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'openid': self.openid,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }