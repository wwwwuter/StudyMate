"""计划解析测试：验证「系统只认用户在设置页配置的 API Key」这一硬约束。

覆盖：
- 未配置 Key 时，AIService 直接抛 ValueError（无任何本地/模板降级路径）
- 未配置 Key 时，/api/plans/parse 返回 400 + 明确引导去「设置」页
- 配置了 Key 时，解析走用户自己的 client（注入假 client 验证，不联网）
- /api/plans/confirm 落库正常
"""
import io

import pytest

from ai.service import AIService, NO_KEY_MESSAGE


class FakeClient:
    """假的用户级 client：返回固定 JSON，避免联网。"""

    def __init__(self, payload=None):
        self.payload = payload or (
            '{"daily_tasks":[{"date":"2026-08-05","subject":"数学",'
            '"content":"高数极限","start_time":"08:30","end_time":"10:00"}]}'
        )

    def is_available(self):
        return True

    def chat(self, prompt, **kwargs):
        return self.payload


# ---- 无 Key：服务层直接抛错，不降级 ----
def test_require_client_raises_without_key(app):
    with pytest.raises(ValueError) as exc:
        AIService().require_client(user_id=1)
    assert '设置' in str(exc.value)


def test_extract_tasks_raises_without_key(app):
    with pytest.raises(ValueError) as exc:
        AIService().extract_tasks('随便一段计划文本', user_id=1)
    assert str(exc.value) == NO_KEY_MESSAGE


# ---- 无 Key：路由返回 400 且提示去设置页 ----
def test_parse_text_without_key_returns_400(client, auth_headers):
    r = client.post('/api/plans/parse', data={'text': '8:30-10:00 数学 高数极限'},
                    headers=auth_headers)
    assert r.status_code == 400
    assert '设置' in r.get_json()['message']


def test_parse_txt_file_without_key_returns_400(client, auth_headers):
    data = {'file': (io.BytesIO('数学 高数极限'.encode('utf-8')), 'plan.txt')}
    r = client.post('/api/plans/parse', data=data,
                    content_type='multipart/form-data', headers=auth_headers)
    assert r.status_code == 400
    assert '设置' in r.get_json()['message']


def test_parse_requires_input(client, auth_headers):
    r = client.post('/api/plans/parse', data={}, headers=auth_headers)
    assert r.status_code == 400


def test_parse_requires_auth(client):
    assert client.post('/api/plans/parse', data={'text': 'x'}).status_code == 401


def test_parse_rejects_unsupported_ext(client, auth_headers, monkeypatch):
    import ai.service as svc
    monkeypatch.setattr(svc.AIService, 'require_client', lambda self, uid: FakeClient())
    data = {'file': (io.BytesIO(b'binary'), 'plan.exe')}
    r = client.post('/api/plans/parse', data=data,
                    content_type='multipart/form-data', headers=auth_headers)
    assert r.status_code == 400
    assert '不支持' in r.get_json()['message']


# ---- 有 Key（注入假 client）：正常解析 ----
def test_parse_text_with_user_client(client, auth_headers, monkeypatch):
    import ai.service as svc
    monkeypatch.setattr(svc.AIService, 'require_client', lambda self, uid: FakeClient())
    r = client.post('/api/plans/parse', data={'text': '8:30-10:00 数学 高数极限'},
                    headers=auth_headers)
    assert r.status_code == 200, r.get_json()
    plans = r.get_json()['data']['plans']
    assert len(plans) == 1
    assert plans[0]['subject'] == '数学'
    assert plans[0]['start_time'] == '08:30'


def test_confirm_persists_plans(client, auth_headers):
    items = [{
        'date': '2026-08-05', 'subject': '数学', 'content': '高数极限',
        'start_time': '08:30', 'end_time': '10:00',
    }]
    r = client.post('/api/plans/confirm', json=items, headers=auth_headers)
    assert r.status_code in (200, 201), r.get_json()

    listed = client.get('/api/tasks?date=2026-08-05', headers=auth_headers)
    assert listed.status_code == 200
    assert any(t['content'] == '高数极限' for t in listed.get_json()['data'])
