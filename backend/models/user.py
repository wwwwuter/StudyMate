from app.extensions import db
from utils.time_utils import utcnow

import hashlib
import os


def _hash_password(password: str, salt: str = None) -> tuple:
    """PBKDF2 本地密码哈希（无外部依赖，离线可用）。返回 (hash_hex, salt)。"""
    if salt is None:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return dk.hex(), salt


class User(db.Model):
    """本地账号表（单机桌面：用户名 + 密码，数据存本机）。

    不再依赖微信 openid / unionid；登录态由本地会话令牌（AuthSession）维护。
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    salt = db.Column(db.String(64), nullable=False)

    last_login_at = db.Column(db.DateTime, nullable=True)
    create_time = db.Column(db.DateTime, default=utcnow)
    update_time = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow
    )

    # 关联
    tasks = db.relationship('StudyTask', backref='user', lazy='dynamic')
    records = db.relationship('StudyRecord', backref='user', lazy='dynamic')

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        return _hash_password(password, salt)

    def check_password(self, password: str) -> bool:
        h, _ = _hash_password(password, self.salt)
        return h == self.password_hash

    def to_dict(self, private=False):
        data = {
            'id': self.id,
            'username': self.username,
            'last_login_at': (
                self.last_login_at.strftime('%Y-%m-%d %H:%M:%S')
                if self.last_login_at
                else None
            ),
            'create_time': (
                self.create_time.strftime('%Y-%m-%d %H:%M:%S')
                if self.create_time
                else None
            ),
        }
        return data

    def __repr__(self):
        return f'<User {self.id} username={self.username}>'
