import os

from dotenv import load_dotenv

load_dotenv()

# 项目根目录（StudyMate/），用于派生数据存储路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

    # ---- Phase 8 DeepSeek / RAG ----
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    DEEPSEEK_TIMEOUT = int(os.getenv('DEEPSEEK_TIMEOUT', '60'))
    DEEPSEEK_MAX_RETRIES = int(os.getenv('DEEPSEEK_MAX_RETRIES', '3'))

    # RAG 知识库（本地 sentence-transformers 向量化 + FAISS 磁盘索引）
    RAG_EMBEDDING_MODEL = os.getenv('RAG_EMBEDDING_MODEL', 'shibing624/text2vec-base-chinese')
    RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '400'))
    RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '80'))
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', '4'))
    RAG_SIM_THRESHOLD = float(os.getenv('RAG_SIM_THRESHOLD', '0.25'))
    RAG_INDEX_DIR = os.getenv('RAG_INDEX_DIR', os.path.join(BASE_DIR, 'data', 'rag'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# ---- 提醒系统（Phase 6，基于 APScheduler）----
# 放在模块级，便于 services.reminder_service 直接导入，且不随 Config 实例变化。
REMINDER_ENABLED = os.getenv('REMINDER_ENABLED', 'true').lower() in ('1', 'true', 'yes')
REMINDER_LEAD_MINUTES = int(os.getenv('REMINDER_LEAD_MINUTES', '10'))
REMINDER_SWEEP_INTERVAL = int(os.getenv('REMINDER_SWEEP_INTERVAL', '60'))
# 任务开始后才扫描到时，仍允许在宽限期内补发一次提醒
REMINDER_GRACE_MINUTES = int(os.getenv('REMINDER_GRACE_MINUTES', '2'))
# 单次扫描只向前看这么久，避免无谓遍历；需大于最大提前量
REMINDER_MAX_LOOKAHEAD = int(os.getenv('REMINDER_MAX_LOOKAHEAD', '120'))


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
