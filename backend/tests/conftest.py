"""测试夹具：用 SQLite 内存库 + WECHAT_MOCK 构建独立测试应用。

不依赖本地 MySQL 服务；微信接口走 mock，保证可在任意环境跑通。
"""
import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    application = create_app('development')
    # SQLite 内存库默认每个连接独立；用 StaticPool 让所有连接共享同一库，
    # 保证跨请求 / 跨测试的表与数据一致。
    application.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        WECHAT_MOCK=True,
        JWT_ACCESS_EXPIRATION_HOURS=2,
        JWT_REFRESH_EXPIRATION_DAYS=30,
        WTF_CSRF_ENABLED=False,
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def wx_headers():
    """小程序 mock 登录后拿到的 Bearer 头。"""
    return None
