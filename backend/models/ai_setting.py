from flask import current_app

from app.extensions import db
from utils.time_utils import utcnow
from utils.crypto import encrypt_value, decrypt_value

# 默认各厂商 OpenAI 兼容端点与模型（学生首次使用时作为占位提示）
DEFAULT_API_BASE = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-chat'


def _encrypt_enabled() -> bool:
    """是否对存储的 API Key 做静态加密（由配置 AI_KEY_ENCRYPT 控制）。"""
    try:
        return bool(current_app.config.get('AI_KEY_ENCRYPT', False))
    except RuntimeError:
        return False


class UserAISetting(db.Model):
    """每位学生的 AI 接入设置（本地存储，开发者不持有密钥）。

    学生自己填自己的 OpenAI 兼容 Key（DeepSeek / 通义 / 智谱 / 月之暗面 均兼容）。
    api_base / model 留空时回退到默认值。enabled=False 时 RAG 走纯检索降级。

    api_key 列在 ``AI_KEY_ENCRYPT=True`` 时存储为加密字符串（带 ``fernet:`` 前缀）；
    读取通过 ``decrypted_key`` 属性透明解密。关闭加密时行为与桌面版一致（明文）。
    """

    __tablename__ = 'user_ai_settings'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    api_key = db.Column(db.String(512), nullable=True, comment='学生自己的 API Key（开启 AI_KEY_ENCRYPT 时加密存储）')
    api_base = db.Column(db.String(256), nullable=True, comment='OpenAI 兼容 Base URL')
    model = db.Column(db.String(128), nullable=True, comment='模型名')
    enabled = db.Column(db.Boolean, default=True, comment='是否启用 AI 生成（关闭则仅检索）')
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    @property
    def decrypted_key(self) -> str:
        """透明解密后的原始 Key；未配置返回空串。"""
        return decrypt_value(self.api_key) if self.api_key else ''

    def to_dict(self, mask_key=True):
        """对外序列化；默认脱敏 api_key（仅回显后四位），避免明文泄露。"""
        raw = self.decrypted_key
        masked = None
        if raw:
            masked = f'{"*" * max(0, len(raw) - 4)}{raw[-4:]}' if len(raw) > 4 else '****'
        return {
            'api_base': self.api_base or DEFAULT_API_BASE,
            'model': self.model or DEFAULT_MODEL,
            'enabled': self.enabled,
            'has_key': bool(raw),
            'api_key_masked': masked,
        }

    @classmethod
    def get_for_user(cls, user_id):
        return cls.query.get(user_id)

    @classmethod
    def save_for_user(cls, user_id, api_key=None, api_base=None, model=None, enabled=None):
        s = cls.query.get(user_id)
        if s is None:
            s = cls(user_id=user_id)
            db.session.add(s)
        if api_key is not None:
            # 守卫：前端展示用的掩码串（形如 sk-7b516*****2e91）绝不能当成真实 Key 存库，
            # 否则会永久覆盖有效 Key 并导致后续所有 AI 调用 401。含 '*' 一律视为「未修改」。
            if '*' in api_key:
                pass  # 跳过写入，保留原有 Key
            else:
                # 仅在真正提供了 Key 且开启加密时加密；空串视为清空。
                s.api_key = (
                    encrypt_value(api_key) if (api_key and _encrypt_enabled()) else (api_key or None)
                )
        if api_base is not None:
            s.api_base = api_base or None
        if model is not None:
            s.model = model or None
        if enabled is not None:
            s.enabled = bool(enabled)
        s.updated_at = utcnow()
        db.session.commit()
        return s
