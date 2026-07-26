import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """应用基础配置（环境变量优先，本地回退）。"""

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')

    # ---- 数据库连接 ----
    # 优先使用完整的 DATABASE_URL；若未提供，则按 MYSQL_* 片段拼接。
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'studymate')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- JWT ----
    # 优先读取 JWT_SECRET_KEY，回退到 JWT_SECRET / 默认值。
    JWT_SECRET = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET', 'dev-jwt-secret')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '72'))

    # 双令牌策略：access token 短期有效，refresh token 长期有效用于无感刷新。
    JWT_ACCESS_EXPIRATION_HOURS = int(os.getenv('JWT_ACCESS_EXPIRATION_HOURS', '2'))
    JWT_REFRESH_EXPIRATION_DAYS = int(os.getenv('JWT_REFRESH_EXPIRATION_DAYS', '30'))

    # ---- DeepSeek AI（后续阶段实现）----
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_BASE = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
    # PDF 智能解析降级开关：无密钥时置 true 可走正则解析（离线 / CI 可用）
    PDF_AI_MOCK = os.getenv('PDF_AI_MOCK', 'false').lower() in ('1', 'true', 'yes')

    # ---- 微信小程序（预留）----
    WECHAT_APP_ID = os.getenv('WECHAT_APP_ID', '')
    WECHAT_APP_SECRET = os.getenv('WECHAT_APP_SECRET', '')

    # ---- 扫码登录（桌面端 + 配套小程序）----
    # 本地开发 / 测试无真实 AppID 时置 true：WeChatService 返回确定性 mock openid。
    WECHAT_MOCK = os.getenv('WECHAT_MOCK', 'false').lower() in ('1', 'true', 'yes')
    # 二维码票据有效期（秒）
    LOGIN_QR_EXPIRE_SECONDS = int(os.getenv('LOGIN_QR_EXPIRE_SECONDS', '300'))
    # 二维码承载的内容前缀（桌面端 / 小程序据此识别扫码登录意图）
    QR_LOGIN_BASE_URL = os.getenv('QR_LOGIN_BASE_URL', 'studymate://login')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
