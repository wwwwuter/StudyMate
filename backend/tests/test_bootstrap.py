"""Phase 6-2：/api/system/bootstrap 启动状态聚合接口。"""
import datetime as dt

from app.extensions import db
from models.task import StudyTask


def _register(client, username='boot_probe'):
    r = client.post('/api/auth/register', json={'username': username, 'password': 'pw123456'})
    assert r.status_code == 201, r.get_json()
    return {'Authorization': f"Bearer {r.get_json()['data']['token']}"}


def test_bootstrap_unauthenticated_returns_setup(client):
    r = client.get('/api/system/bootstrap')
    assert r.status_code == 200
    d = r.get_json()['data']
    assert d['user']['setup_done'] is False  # 独立测试库尚无用户
    assert d['user']['authenticated'] is False
    assert d['timer'] is None
    assert 'enabled' in d['reminder']


def test_bootstrap_authenticated_empty_timer(client):
    headers = _register(client)
    r = client.get('/api/system/bootstrap', headers=headers)
    d = r.get_json()['data']
    assert d['user']['setup_done'] is True
    assert d['user']['authenticated'] is True
    assert d['user']['username'] == 'boot_probe'
    assert d['timer'] is None
    assert d['reminder']['enabled'] is True


def test_bootstrap_includes_running_task_session(client):
    headers = _register(client)
    with client.application.app_context():
        from models.user import User
        uid = db.session.query(User).filter_by(username='boot_probe').first().id
        t = StudyTask(user_id=uid, date=dt.date.today(), subject='数学', content='高数强化',
                      start_time=dt.time(9, 0), end_time=dt.time(11, 30),
                      status=StudyTask.STATUS_PENDING)
        db.session.add(t)
        db.session.commit()
        tid = t.id
    r = client.post('/api/plans/timer/start', headers=headers,
                    json={'mode': 'task', 'task_id': tid})
    assert r.status_code == 200
    r2 = client.get('/api/system/bootstrap', headers=headers)
    t2 = r2.get_json()['data']['timer']
    assert t2 is not None
    assert t2['mode'] == 'task'
    assert t2['status'] == 'running'
    assert t2['task'] is not None
    assert t2['task']['subject'] == '数学'
    assert t2['plan_start_time'] is not None
    assert t2['plan_end_time'] is not None


def test_bootstrap_includes_pomodoro_rebuild_fields(client):
    headers = _register(client, 'boot_pomo')
    r = client.post('/api/plans/timer/start', headers=headers,
                    json={'mode': 'pomodoro', 'duration': 1500})
    assert r.status_code == 200
    r2 = client.get('/api/system/bootstrap', headers=headers)
    t2 = r2.get_json()['data']['timer']
    assert t2['mode'] == 'pomodoro'
    assert t2['pomodoro_phase'] == 'work'
    assert t2['target_seconds'] == 1500
    assert t2['phase_started_at'] is not None
