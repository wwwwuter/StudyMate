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

    # ---- Web 化（多租户网站部署）----
    # 允许跨域的前端域名（逗号分隔）。生产环境务必设为你的前端站域名，
    # 不要用 '*'（会暴露凭据且浏览器在带凭据时拒绝）。与前端同源部署时填 '*' 也可。
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')
    # 是否对存储的学生第三方 API Key 做静态加密（Fernet，密钥派生自 SECRET_KEY）。
    # 网站部署强烈建议设为 true；桌面版默认 false（明文，仅本机）。
    AI_KEY_ENCRYPT = os.getenv('AI_KEY_ENCRYPT', 'false').lower() in ('1', 'true', 'yes')

    # ---- AI 接入 ----
    # 系统不持有任何全局 API Key：AI 所需的 Key / Base / Model 一律来自学生在
    # 「设置」页保存的个人配置（user_ai_settings 表，本地存储）。
    # 这里只保留与密钥无关的运行参数。
    AI_TIMEOUT = int(os.getenv('AI_TIMEOUT', '60'))
    AI_MAX_RETRIES = int(os.getenv('AI_MAX_RETRIES', '3'))

    # ---- 上传限制 ----
    # 单次上传资料文件大小上限（MB），环境变量 MAX_UPLOAD_SIZE 可覆盖。
    # 设为 0 表示不限制（不推荐，大文件会占满内存）。
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', '16')) * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE or None


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
# 无具体开始时间的任务（如按艾宾浩斯铺排的日期型任务）默认在此整点触发提醒
REMINDER_DEFAULT_HOUR = int(os.getenv('REMINDER_DEFAULT_HOUR', '9'))


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
