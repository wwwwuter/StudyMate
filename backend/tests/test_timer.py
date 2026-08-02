"""计时系统测试：正计时 / 倒计时 / 番茄钟 + 历史与统计 + 任务扩展字段。"""
from models.user import User


def _login(client, username='timer_user'):
    r = client.post('/api/auth/register', json={'username': username, 'password': 'pw123456'})
    assert r.status_code == 201, r.get_json()
    return {'Authorization': f"Bearer {r.get_json()['data']['token']}"}


def _uid(client, username='timer_user'):
    return User.query.filter_by(username=username).first().id


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
