"""Phase 6：TimerSession 状态持久化（pomodoro_phase / phase_started_at / target_seconds）。"""
import datetime as dt

from app.extensions import db
from models.task import StudyTask
from models.timer_session import TimerSession


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid):
    with client.application.app_context():
        t = StudyTask(
            user_id=uid, date=dt.date.today(), subject='数学', content='高数强化',
            start_time=dt.time(9, 0), end_time=dt.time(11, 30),
            status=StudyTask.STATUS_PENDING,
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def test_pomodoro_start_persists_phase_and_target(client, auth_headers):
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'pomodoro', 'duration': 1500})
    assert r.status_code == 200
    d = r.get_json()['data']
    assert d['pomodoro_phase'] == 'work'
    assert d['target_seconds'] == 1500
    assert d['phase_started_at'] is not None
    with client.application.app_context():
        s = TimerSession.query.get(d['id'])
        assert s.pomodoro_phase == 'work'
        assert s.target_seconds == 1500
        assert s.phase_started_at is not None


def test_countdown_start_persists_target(client, auth_headers):
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'countdown', 'duration': 1800})
    d = r.get_json()['data']
    assert d['target_seconds'] == 1800
    with client.application.app_context():
        s = TimerSession.query.get(d['id'])
        assert s.target_seconds == 1800


def test_task_start_has_no_phase_fields(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid)
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'task', 'task_id': tid})
    d = r.get_json()['data']
    assert d['pomodoro_phase'] is None
    assert d['target_seconds'] is None
    assert d['plan_start_time'] is not None
    assert d['plan_end_time'] is not None


def test_phase_sync_updates_stage(client, auth_headers):
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'pomodoro', 'duration': 1500})
    sid = r.get_json()['data']['id']
    r2 = client.post('/api/plans/timer/phase', headers=auth_headers,
                     json={'phase': 'break', 'target_seconds': 300})
    assert r2.status_code == 200
    d = r2.get_json()['data']
    assert d['pomodoro_phase'] == 'break'
    assert d['target_seconds'] == 300
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        assert s.pomodoro_phase == 'break'
        assert s.target_seconds == 300


def test_phase_sync_rejects_non_pomodoro(client, auth_headers):
    client.post('/api/plans/timer/start', headers=auth_headers,
                json={'mode': 'countup', 'note': '自由'})
    r = client.post('/api/plans/timer/phase', headers=auth_headers,
                    json={'phase': 'break'})
    assert r.status_code == 400


def test_phase_sync_rejects_bad_phase(client, auth_headers):
    client.post('/api/plans/timer/start', headers=auth_headers,
                json={'mode': 'pomodoro', 'duration': 1500})
    r = client.post('/api/plans/timer/phase', headers=auth_headers,
                    json={'phase': 'lunch'})
    assert r.status_code == 400
