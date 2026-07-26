from app.extensions import db
from utils.time_utils import utcnow


class LoginTicket(db.Model):
    """扫码登录票据表。

    桌面端生成二维码时写入一条 pending 票据；配套微信小程序扫码并上报 code 后
    标记为 confirmed 并绑定用户；轮询接口在 confirmed 时返回 JWT。
    状态机：pending -> confirmed / expired。
    """

    __tablename__ = 'login_tickets'

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_EXPIRED = 'expired'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket = db.Column(db.String(64), unique=True, nullable=False, index=True)
    openid = db.Column(db.String(64), nullable=True, index=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
    )
    status = db.Column(db.String(16), default=STATUS_PENDING, nullable=False)
    expire_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    def is_expired(self):
        return utcnow() > self.expire_at

    def confirm(self, user_id, openid=None):
        """标记为已确认并绑定用户。"""
        self.user_id = user_id
        if openid is not None:
            self.openid = openid
        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = utcnow()

    def expire(self):
        self.status = self.STATUS_EXPIRED

    def to_dict(self):
        return {
            'ticket': self.ticket,
            'status': self.status,
            'expire_at': self.expire_at.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def __repr__(self):
        return f'<LoginTicket {self.ticket} status={self.status}>'
