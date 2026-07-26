"""Phase 2 用户系统接口测试。"""
import pytest

from app.extensions import db
from models.user import User
from utils.jwt_utils import decode_token


def _login_via_code(client, code='test_code_123'):
    """调用小程序 code 登录，返回 (access_token, refresh_token, user_id)。"""
    resp = client.post('/api/auth/wechat/login', json={'code': code})
    assert resp.status_code == 200, resp.get_json()
    data = resp.get_json()['data']
    return data['token']['access_token'], data['token']['refresh_token'], data['user']['id']


# ---- 小程序 code 登录 ----
def test_wechat_code_login(client):
    access, refresh, uid = _login_via_code(client, 'abc')
    assert access and refresh
    assert uid > 0


def test_wechat_code_login_missing_code(client):
    resp = client.post('/api/auth/wechat/login', json={})
    assert resp.status_code == 400


# ---- 扫码登录完整流程 ----
def test_qr_login_flow(client):
    # 1) 创建二维码票据
    resp = client.post('/api/auth/wechat/qr')
    assert resp.status_code == 200
    ticket = resp.get_json()['data']['ticket']
    assert ticket

    # 2) 轮询，初始应为 pending
    status = client.get(f'/api/auth/wechat/qr/status?ticket={ticket}')
    assert status.status_code == 200
    assert status.get_json()['data']['status'] == 'pending'

    # 3) 小程序扫码回调
    scan = client.post('/api/auth/wechat/scan', json={'ticket': ticket, 'code': 'scan_code_1'})
    assert scan.status_code == 200

    # 4) 再次轮询，应为 confirmed 并拿到令牌
    status2 = client.get(f'/api/auth/wechat/qr/status?ticket={ticket}')
    body = status2.get_json()
    assert body['data']['status'] == 'confirmed'
    assert body['data']['token']['access_token']
    assert body['data']['user']['id'] > 0


def test_qr_status_unknown_ticket(client):
    resp = client.get('/api/auth/wechat/qr/status?ticket=does_not_exist')
    assert resp.status_code == 404


def test_qr_expired(client, app):
    from models.login_ticket import LoginTicket
    from datetime import timedelta
    import uuid
    from app.extensions import db
    from utils.time_utils import utcnow

    ticket = uuid.uuid4().hex
    lt = LoginTicket(
        ticket=ticket,
        status=LoginTicket.STATUS_PENDING,
        expire_at=utcnow() - timedelta(seconds=10),
    )
    db.session.add(lt)
    db.session.commit()

    resp = client.get(f'/api/auth/wechat/qr/status?ticket={ticket}')
    assert resp.status_code == 410
    assert resp.get_json()['data']['status'] == 'expired'


# ---- 令牌刷新 ----
def test_refresh_token(client):
    _, refresh, _ = _login_via_code(client, 'refresh_code')
    resp = client.post('/api/auth/refresh', json={'refresh_token': refresh})
    assert resp.status_code == 200
    new = resp.get_json()['data']['token']
    assert new['access_token'] and new['refresh_token']


def test_refresh_invalid(client):
    resp = client.post('/api/auth/refresh', json={'refresh_token': 'garbage'})
    assert resp.status_code == 401


# ---- 当前用户 ----
def test_me_requires_auth(client):
    resp = client.get('/api/auth/me')
    assert resp.status_code == 401


def test_me_with_token(client):
    access, _, _ = _login_via_code(client, 'me_code')
    resp = client.get('/api/auth/me', headers={'Authorization': f'Bearer {access}'})
    assert resp.status_code == 200
    assert 'id' in resp.get_json()['data']


# ---- 用户资料更新 ----
def test_update_profile(client):
    access, _, _ = _login_via_code(client, 'profile_code')
    headers = {'Authorization': f'Bearer {access}'}

    # 更新昵称
    resp = client.put('/api/user/profile', json={'nickname': '考研人'}, headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['data']['nickname'] == '考研人'

    # /info 应反映更新
    info = client.get('/api/user/info', headers=headers)
    assert info.get_json()['data']['nickname'] == '考研人'


def test_update_profile_rejects_internal_fields(client):
    access, _, _ = _login_via_code(client, 'profile_code2')
    headers = {'Authorization': f'Bearer {access}'}
    # 尝试越权写入 openid 应被白名单忽略
    resp = client.put('/api/user/profile', json={'openid': 'hack'}, headers=headers)
    assert resp.status_code == 200
    data = resp.get_json()['data']
    # 公开接口不应泄露 openid
    assert 'openid' not in data
    # 库中真实 openid 未被覆盖（仍为原始 mock 值，而非 'hack'）
    payload = decode_token(access, expected_type='access')
    user = db.session.get(User, int(payload['sub']))
    assert user.openid != 'hack'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
