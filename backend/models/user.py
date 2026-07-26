from app.extensions import db
from utils.time_utils import utcnow


class User(db.Model):
    """用户表（微信体系）。

    考研 11408 学习助手的用户主体。登录方式以微信扫码 / 小程序 code 登录为主，
    因此以 openid 作为唯一身份标识，unionid 用于跨应用（公众号 / 小程序）关联。
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    unionid = db.Column(db.String(64), nullable=True, index=True)
    nickname = db.Column(db.String(64), default='')
    avatar = db.Column(db.String(512), default='')
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.SmallInteger, default=0)  # 0 未知 / 1 男 / 2 女
    country = db.Column(db.String(64), default='')
    province = db.Column(db.String(64), default='')
    city = db.Column(db.String(64), default='')

    last_login_at = db.Column(db.DateTime, nullable=True)
    create_time = db.Column(db.DateTime, default=utcnow)
    update_time = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow
    )

    # 关联
    tasks = db.relationship('StudyTask', backref='user', lazy='dynamic')
    records = db.relationship('StudyRecord', backref='user', lazy='dynamic')

    def to_dict(self, private=False):
        """序列化为对外用户信息。

        private=True 时额外返回 openid / unionid（仅用于用户本人或内部场景）。
        """
        data = {
            'id': self.id,
            'nickname': self.nickname,
            'avatar': self.avatar,
            'phone': self.phone,
            'gender': self.gender,
            'country': self.country,
            'province': self.province,
            'city': self.city,
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
        if private:
            data['openid'] = self.openid
            data['unionid'] = self.unionid
        return data

    def __repr__(self):
        return f'<User {self.id} openid={self.openid}>'
