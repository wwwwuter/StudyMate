from app.extensions import db
from utils.time_utils import utcnow
from utils.crypto import encrypt_value, decrypt_value


class UserVisionSetting(db.Model):
    """视觉模型设置（图片/截图计划识别用），独立成表以避免改动 user_ai_settings 旧表。

    视觉模型需支持 OpenAI 兼容的 vision 接口（如 qwen-vl / glm-4v / gpt-4o 等）。
    未配置时回退到普通聊天 Key（多数聊天模型不支持图片，会返回明确错误）。
    api_key 在 AI_KEY_ENCRYPT=True 时加密存储。
    """

    __tablename__ = 'user_vision_settings'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    api_key = db.Column(db.String(512), nullable=True, comment='视觉模型 API Key')
    api_base = db.Column(db.String(256), nullable=True, comment='视觉模型 OpenAI 兼容 Base URL')
    model = db.Column(db.String(128), nullable=True, comment='视觉模型名')
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @property
    def decrypted_key(self) -> str:
        return decrypt_value(self.api_key) if self.api_key else ''

    def to_dict(self, mask_key=True):
        raw = self.decrypted_key
        masked = None
        if raw:
            masked = f'{"*" * max(0, len(raw) - 4)}{raw[-4:]}' if len(raw) > 4 else '****'
        return {
            'has_key': bool(raw),
            'api_key_masked': masked,
            'api_base': self.api_base or '',
            'model': self.model or '',
        }

    @classmethod
    def get_for_user(cls, user_id):
        return cls.query.get(user_id)

    @classmethod
    def save_for_user(cls, user_id, api_key=None, api_base=None, model=None):
        from app.extensions import db as _db
        from utils.crypto import _encrypt_enabled as _enc
        s = cls.query.get(user_id)
        if s is None:
            s = cls(user_id=user_id)
            _db.session.add(s)
        if api_key is not None:
            s.api_key = (
                encrypt_value(api_key) if (api_key and _enc()) else (api_key or None)
            )
        if api_base is not None:
            s.api_base = api_base or None
        if model is not None:
            s.model = model or None
        s.updated_at = utcnow()
        _db.session.commit()
        return s
