"""Phase 8 AIService 与 RAG 路由测试（注入假 client / rag）。"""
import pytest


class FakeClient:
    def __init__(self, text='AI回答'):
        self._text = text
    def is_available(self):
        return True
    def chat(self, messages, **kw):
        return self._text


class NoKeyClient:
    def is_available(self):
        return False


class FakeRag:
    def __init__(self):
        self.calls = []
    def retrieve(self, uid, q, top_k=None):
        self.calls.append((uid, q))
        return [{
            'material_id': 1, 'title': '线代', 'score': 0.9,
            'snippet': 'x', 'content': '特征值与特征向量内容',
        }]


def _login(client, code='rag_user'):
    r = client.post('/api/auth/wechat/login', json={'code': code})
    token = r.get_json()['data']['token']['access_token']
    return {'Authorization': f'Bearer {token}'}


def _patch(monkeypatch, client=None, rag=None):
    import ai
    monkeypatch.setattr(ai.ai_service, 'client', client or FakeClient())
    monkeypatch.setattr(ai.ai_service, 'rag', rag or FakeRag())


def test_rag_answer_ai_path(monkeypatch):
    import ai
    monkeypatch.setattr(ai.ai_service, 'client', FakeClient('来自AI'))
    monkeypatch.setattr(ai.ai_service, 'rag', FakeRag())
    r = ai.ai_service.rag_answer(1, '什么是特征值')
    assert r['source'] == 'ai'
    assert r['answer'] == '来自AI'
    assert r['sources'][0]['material_id'] == 1


def test_rag_answer_retrieval_fallback(monkeypatch):
    import ai
    monkeypatch.setattr(ai.ai_service, 'client', NoKeyClient())
    monkeypatch.setattr(ai.ai_service, 'rag', FakeRag())
    r = ai.ai_service.rag_answer(1, '什么是特征值')
    assert r['source'] == 'retrieval'
    assert '检索' in r['answer']


def test_learning_report_mock(monkeypatch):
    import ai
    monkeypatch.setenv('LEARNING_REPORT_MOCK', 'true')
    monkeypatch.setattr(ai.ai_service, 'client', FakeClient())
    m = {
        'total_hours': 5, 'session_count': 3, 'streak': 2,
        'tasks': {'done': 4, 'total': 5, 'completion_rate': 80},
        'planned_minutes': 300, 'actual_minutes': 300,
        'by_subject_actual': {'数学': 18000},
    }
    r = ai.ai_service.learning_report(m)
    assert r['source'] == 'template'
    assert '学习报告' in r['text']


def test_rag_query_route(client, monkeypatch):
    import ai
    monkeypatch.setattr(ai.ai_service, 'client', FakeClient('路由AI'))
    monkeypatch.setattr(ai.ai_service, 'rag', FakeRag())
    h = _login(client)
    r = client.post('/api/rag/query', json={'question': '特征值'}, headers=h)
    assert r.status_code == 200, r.get_json()
    data = r.get_json()['data']
    assert data['source'] == 'ai'
    assert data['answer'] == '路由AI'
    assert data['sources']


def test_rag_status_route(client, monkeypatch):
    import ai
    monkeypatch.setattr(ai.ai_service, 'rag', FakeRag())
    h = _login(client)
    r = client.get('/api/rag/status', headers=h)
    assert r.status_code == 200


def test_rag_query_missing_question(client, monkeypatch):
    import ai
    monkeypatch.setattr(ai.ai_service, 'client', FakeClient())
    monkeypatch.setattr(ai.ai_service, 'rag', FakeRag())
    h = _login(client)
    r = client.post('/api/rag/query', json={}, headers=h)
    assert r.status_code == 400
