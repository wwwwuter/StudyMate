from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
# 开放注册防滥用：默认内存存储（单实例足够）；多实例可换 Redis。
limiter = Limiter(key_func=get_remote_address, default_limits=[])