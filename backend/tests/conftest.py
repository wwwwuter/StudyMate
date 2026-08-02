"""测试夹具：用 SQLite 内存库构建独立测试应用。

完全离线，不依赖本地 MySQL、不依赖任何 AI API Key —— 系统只认用户在
「设置」页配置的个人 Key，测试中一律为空，因此 AI 相关路径应报明确错误。
"""
import os

# 必须在 import app 之前设置：app/config.py 在模块 import 时求值环境变量。
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402


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
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
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
def auth_headers(client):
    """注册一个本地账号并返回 Bearer 头。"""
    r = client.post('/api/auth/register',
                    json={'username': 'tester', 'password': 'pw123456'})
    assert r.status_code == 201, r.get_json()
    return {'Authorization': f"Bearer {r.get_json()['data']['token']}"}
