"""本地账号鉴权测试：注册 / 登录 / 当前用户 / 退出。

系统已去微信化，登录态由 AuthSession 会话令牌维护（Bearer token）。
"""


def _register(client, username='alice', password='pw123456'):
    return client.post('/api/auth/register',
                       json={'username': username, 'password': password})


def test_status_before_setup(client):
    r = client.get('/api/auth/status')
    assert r.status_code == 200
    assert r.get_json()['data']['setup_done'] is False


def test_register_returns_token(client):
    r = _register(client)
    assert r.status_code == 201, r.get_json()
    data = r.get_json()['data']
    assert data['token']
    assert data['user']['username'] == 'alice'


def test_register_duplicate_username(client):
    _register(client)
    r = _register(client)
    assert r.status_code >= 400
    assert r.get_json()['code'] >= 400


def test_register_weak_password(client):
    r = _register(client, 'bob', '123')
    assert r.status_code >= 400


def test_login_success_and_me(client):
    _register(client)
    r = client.post('/api/auth/login', json={'username': 'alice', 'password': 'pw123456'})
    assert r.status_code == 200, r.get_json()
    token = r.get_json()['data']['token']

    me = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.get_json()['data']['username'] == 'alice'


def test_login_wrong_password(client):
    _register(client)
    r = client.post('/api/auth/login', json={'username': 'alice', 'password': 'wrong-pw'})
    assert r.status_code >= 400


def test_me_requires_token(client):
    assert client.get('/api/auth/me').status_code == 401


def test_me_rejects_bad_token(client):
    r = client.get('/api/auth/me', headers={'Authorization': 'Bearer not-a-real-token'})
    assert r.status_code == 401


def test_logout_invalidates_token(client):
    _register(client)
    r = client.post('/api/auth/login', json={'username': 'alice', 'password': 'pw123456'})
    token = r.get_json()['data']['token']
    h = {'Authorization': f'Bearer {token}'}

    assert client.post('/api/auth/logout', headers=h).status_code == 200
    assert client.get('/api/auth/me', headers=h).status_code == 401


def test_status_after_setup(client):
    _register(client)
    assert client.get('/api/auth/status').get_json()['data']['setup_done'] is True
