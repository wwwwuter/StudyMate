"""本地鉴权业务层：账号初始化、登录校验、会话签发。

全部逻辑离线执行，不依赖微信或任何三方服务。密码使用 PBKDF2 哈希存储。
"""
from app.extensions import db
from models.user import User
from utils.local_auth import create_session
from utils.time_utils import utcnow


class AuthError(Exception):
    def __init__(self, message, code=400):
        self.message = message
        self.code = code
        super().__init__(message)


def account_exists() -> bool:
    """是否已初始化本地账号（决定前端显示「初始化」还是「登录」）。"""
    return db.session.query(User.id).first() is not None


def setup_account(username: str, password: str) -> User:
    """首次初始化账号（网站部署时用于创建首个管理员）。已存在则报错。"""
    if account_exists():
        raise AuthError('账号已初始化，请直接登录', 409)
    return _create_user(username, password)


def register(username: str, password: str) -> User:
    """开放注册（多用户网站）。用户名已存在则报错。

    与 setup_account 的区别：不要求「无账号」前置条件，允许多个用户注册。
    """
    if User.query.filter_by(username=username.strip()).first():
        raise AuthError('该用户名已被注册', 409)
    return _create_user(username, password)


def _create_user(username: str, password: str) -> User:
    """创建用户的公共逻辑（密码哈希、入库、提交）。"""
    _validate(username, password)
    user = User(username=username.strip())
    user.password_hash, user.salt = User.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(username: str, password: str) -> str:
    """校验账号密码，成功返回会话令牌。"""
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        raise AuthError('用户名或密码错误', 401)
    user.last_login_at = utcnow()
    db.session.commit()
    return create_session(user.id)


def _validate(username: str, password: str):
    if not username or not username.strip():
        raise AuthError('用户名不能为空')
    if len(username.strip()) < 2:
        raise AuthError('用户名至少 2 个字符')
    if not password or len(password) < 6:
        raise AuthError('密码至少 6 位')
