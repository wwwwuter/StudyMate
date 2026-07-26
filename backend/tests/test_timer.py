"""Phase 5 计时系统 + 升级方向 U3(RAG)/U5(字段) 测试。"""
import io

from app.extensions import db
from models.record import StudyRecord
from models.material import Material
from models.user import User


def _login(client, code='timer_user'):
    r = client.post('/api/auth/wechat/login', json={'code': code})
    token = r.get_json()['data']['token']['access_token']
    return {'Authorization': f'Bearer {token}'}


def _uid(client, code='timer_user'):
    return User.query.filter_by(wechat_openid=code).first().id


# ---------------------- 计时系统 ----------------------
def test_timer_start_stop_and_stats(client):
    h = _login(client)
    # 正计时：开始
    r = client.post('/api/records', json={'mode': 'countup', 'subject': '数学'}, headers=h)
    assert r.status_code == 201, r.get_json()
    rec = r.get_json()['data']
    assert rec['mode'] == 'countup'
    rid = rec['id']

    # 停止
    r2 = client.put(f'/api/records/{rid}/stop', headers=h)
    assert r2.status_code == 200
    assert r2.get_json()['data']['duration'] >= 0

    # 统计：结构正确且包含本次记录
    r3 = client.get('/api/records/stats?range=all', headers=h)
    assert r3.status_code == 200
    s = r3.get_json()['data']
    assert 'total_seconds' in s and 'by_mode' in s and 'daily' in s
    assert s['session_count'] >= 1
    assert s['by_mode'].get('countup', 0) >= 0

    # 倒计时：带计划时长
    r4 = client.post('/api/records', json={'mode': 'countdown', 'planned_duration': 1500, 'subject': '英语'}, headers=h)
    assert r4.status_code == 201
    assert r4.get_json()['data']['planned_duration'] == 1500


def test_timer_history_filter_and_delete(client):
    h = _login(client)
    r = client.post('/api/records', json={'mode': 'pomodoro', 'subject': '408'}, headers=h)
    rid = r.get_json()['data']['id']

    # 过滤：mode=pomodoro 应命中
    r2 = client.get('/api/records/history?mode=pomodoro', headers=h)
    assert r2.status_code == 200
    ids = [x['id'] for x in r2.get_json()['data']]
    assert rid in ids

    # 删除
    r3 = client.delete(f'/api/records/{rid}', headers=h)
    assert r3.status_code == 200
    r4 = client.get('/api/records/history', headers=h)
    assert rid not in [x['id'] for x in r4.get_json()['data']]


def test_timer_invalid_mode(client):
    h = _login(client)
    r = client.post('/api/records', json={'mode': 'fly'}, headers=h)
    assert r.status_code == 400


# ---------------------- U5 字段扩展 ----------------------
def test_task_fields_priority_tags(client):
    h = _login(client)
    payload = {
        'date': '2026-10-01', 'subject': '政治', 'content': '马原',
        'priority': 2, 'estimated_minutes': 90, 'tags': '强化,真题',
    }
    r = client.post('/api/tasks', json=payload, headers=h)
    assert r.status_code == 201, r.get_json()
    tid = r.get_json()['data']['id']

    r2 = client.get(f'/api/tasks/{tid}', headers=h)
    d = r2.get_json()['data']
    assert d['priority'] == 2
    assert d['estimated_minutes'] == 90
    assert d['tags'] == '强化,真题'

    # 更新标签
    r3 = client.put(f'/api/tasks/{tid}', json={'tags': '冲刺'}, headers=h)
    assert r3.get_json()['data']['tags'] == '冲刺'


# ---------------------- U3 RAG 关键词 MVP ----------------------
def test_material_upload_and_match(client):
    h = _login(client)
    # 上传资料（multipart：用 data 传文件元组）
    data = {
        'title': 'OS笔记',
        'file': (io.BytesIO('操作系统 进程调度 死锁 内存管理'.encode('utf-8')), 'os.txt'),
    }
    r = client.post('/api/materials', data=data,
                    content_type='multipart/form-data', headers=h)
    assert r.status_code == 201, r.get_json()

    # 检索与「进程调度」相关
    r2 = client.post('/api/materials/match', json={'query': '进程调度与死锁'}, headers=h)
    assert r2.status_code == 200
    res = r2.get_json()['data']
    assert len(res) >= 1
    assert res[0]['score'] > 0
    assert 'OS笔记' in res[0]['title']


def test_material_keyword_retrieve_pure():
    """纯函数：中文二元组重叠打分。"""
    from ai.rag import RAGService
    mats = [
        type('M', (), {'id': 1, 'title': '高数', 'content': '极限 导数 中值定理'})(),
        type('M', (), {'id': 2, 'title': '英语', 'content': '阅读理解 长难句'})(),
    ]
    res = RAGService.keyword_retrieve('导数与中值定理', mats)
    assert res and res[0]['id'] == 1
