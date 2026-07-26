"""鉴权业务层。

将路由中的业务逻辑下沉到这里，使蓝图保持轻量、可单测。所有函数依赖 Flask
应用上下文（current_app / db）。
"""
import uuid
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import db
from models.user import User
from models.login_ticket import LoginTicket
from utils.time_utils import utcnow
from utils.jwt_utils import create_access_token, create_refresh_token, decode_token
from services.wechat_service import get_wechat_service, WeChatAPIError


class AuthError(Exception):
    """业务层可预期错误，携带 HTTP 状态码。"""

    def __init__(self, message, code=400):
        self.message = message
        self.code = code
        super().__init__(message)


class InvalidToken(AuthError):
    def __init__(self, message='无效或过期的令牌'):
        super().__init__(message, 401)


class TicketNotFound(AuthError):
    def __init__(self, message='票据不存在或已失效'):
        super().__init__(message, 404)


class TicketExpired(AuthError):
    def __init__(self, message='二维码已过期，请刷新'):
        super().__init__(message, 410)


# ---- 用户 ----
def find_or_create_user(openid, unionid=None, **profile):
    """按 openid 查找用户，不存在则创建；存在则按需补全资料。"""
    user = User.query.filter_by(openid=openid).first()
    if user is None:
        user = User(openid=openid, unionid=unionid, **profile)
        db.session.add(user)
    else:
        if unionid and not user.unionid:
            user.unionid = unionid
        for key, value in profile.items():
            if value and hasattr(user, key):
                setattr(user, key, value)
    user.last_login_at = utcnow()
    db.session.commit()
    return user


# ---- 令牌 ----
def issue_tokens(user):
    """签发 access + refresh 双令牌。"""
    return {
        'access_token': create_access_token(user.id),
        'refresh_token': create_refresh_token(user.id),
        'token_type': 'Bearer',
        'expires_in': int(current_app.config.get('JWT_ACCESS_EXPIRATION_HOURS', 2)) * 3600,
    }


def refresh_tokens(refresh_token):
    """用 refresh token 换发新的双令牌。"""
    try:
        payload = decode_token(refresh_token, expected_type='refresh')
    except Exception as e:  # noqa: F841
        raise InvalidToken()
    user = db.session.get(User, int(payload.get('sub')))
    if user is None:
        raise InvalidToken('用户不存在')
    return issue_tokens(user)


# ---- 扫码登录流程 ----
def create_qr_ticket():
    """生成一条 pending 票据，返回 (LoginTicket, qr_content)。"""
    ticket = uuid.uuid4().hex
    expire_seconds = current_app.config.get('LOGIN_QR_EXPIRE_SECONDS', 300)
    expires_at = utcnow() + timedelta(seconds=expire_seconds)
    lt = LoginTicket(
        ticket=ticket, status=LoginTicket.STATUS_PENDING, expire_at=expires_at
    )
    db.session.add(lt)
    db.session.commit()

    base = current_app.config.get('QR_LOGIN_BASE_URL', 'studymate://login')
    qr_content = f'{base}?ticket={ticket}'
    return lt, qr_content


def confirm_qr_login(ticket, code):
    """小程序扫码回调：校验票据 -> 调微信换 openid -> 创建/查找用户 -> 确认票据。

    返回确认后的 LoginTicket。
    """
    lt = LoginTicket.query.filter_by(ticket=ticket).first()
    if lt is None:
        raise TicketNotFound()
    if lt.is_expired():
        lt.expire()
        db.session.commit()
        raise TicketExpired()
    if lt.status == LoginTicket.STATUS_CONFIRMED:
        return lt

    wx = get_wechat_service()
    try:
        wx_data = wx.code2session(code)
    except WeChatAPIError as e:
        raise AuthError(f"微信授权失败: {e.detail}", 502)

    openid = wx_data.get('openid')
    unionid = wx_data.get('unionid')
    user = find_or_create_user(openid, unionid=unionid)
    lt.confirm(user.id, openid=openid)
    db.session.commit()
    return lt


def get_ticket_status(ticket):
    """轮询票据状态。confirmed 时一并返回令牌与用户信息。"""
    lt = LoginTicket.query.filter_by(ticket=ticket).first()
    if lt is None:
        raise TicketNotFound()
    if lt.is_expired() and lt.status != LoginTicket.STATUS_CONFIRMED:
        lt.expire()
        db.session.commit()
        return {'status': LoginTicket.STATUS_EXPIRED}

    if lt.status == LoginTicket.STATUS_CONFIRMED and lt.user_id:
        user = db.session.get(User, lt.user_id)
        return {
            'status': LoginTicket.STATUS_CONFIRMED,
            'token': issue_tokens(user),
            'user': user.to_dict(),
        }
    return {'status': LoginTicket.STATUS_PENDING}
