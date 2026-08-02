from app.extensions import db
from utils.time_utils import utcnow


class AuthSession(db.Model):
    """本地登录会话：用户登录成功后签发，前端凭令牌访问受保护接口。

    单机场景：令牌存于本机数据库，不联网；过期时间默认 30 天，可续期。
    """

    __tablename__ = 'auth_sessions'

    SESSION_DAYS = 30

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<AuthSession {self.id} user={self.user_id}>'
