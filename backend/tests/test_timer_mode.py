"""计时模式体系测试（需求八/九/十二）。

覆盖：
1. 番茄钟 → StudyRecord.record_type == 'pomodoro'
2. 自由计时 → StudyRecord.record_type == 'countup'
3. 任务计时 → StudyRecord.task_id 正确绑定、record_type == 'task'
4. 统计页对 番茄/自由/任务 分别统计
5. 番茄钟休息时间不计入学习时长
"""
import time
from datetime import datetime, timedelta

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask
from models.timer_session import TimerSession
from models.pomodoro_cycle import PomodoroCycle


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid, subject, content, status):
    with client.application.app_context():
        from datetime import date, time as dtime
        import datetime as dt
        t = StudyTask(
            user_id=uid, date=dt.date.today(), subject=subject, content=content,
            start_time=dtime(9, 0), end_time=dtime(10, 0), status=status,
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def _set_started_ago(client, sid, seconds_ago):
    """把指定 session 的开始时间往前调，模拟一段真实计时时长（非番茄模式用）。"""
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        s.started_at = datetime.utcnow() - timedelta(seconds=seconds_ago)
        db.session.commit()


def test_pomodoro_record_type(client, auth_headers):
    uid = _uid(client)
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'pomodoro'})
    assert r.status_code == 200
    sid = r.get_json()['data']['id']
    # 上报一轮：专注 25 分钟
    rc = client.post('/api/plans/timer/cycle', headers=auth_headers,
                     json={'session_id': sid, 'focus_duration': 1500, 'break_duration': 300})
    assert rc.status_code == 200
    time.sleep(0.3)
    r = client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    assert r.status_code == 200

    with client.application.app_context():
        rec = StudyRecord.query.filter_by(user_id=uid).order_by(StudyRecord.id.desc()).first()
        assert rec is not None
        assert rec.record_type == StudyRecord.MODE_POMODORO
        assert rec.task_id is None


def test_free_countup_record_type(client, auth_headers):
    uid = _uid(client)
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'countup'})
    assert r.status_code == 200
    sid = r.get_json()['data']['id']
    _set_started_ago(client, sid, 600)  # 10 分钟
    time.sleep(0.3)
    r = client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    assert r.status_code == 200

    with client.application.app_context():
        rec = StudyRecord.query.filter_by(user_id=uid).order_by(StudyRecord.id.desc()).first()
        assert rec.record_type == StudyRecord.MODE_COUNTUP
        assert rec.duration == 600


def test_task_timer_binds_task_id(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, '数学', '高数强化', StudyTask.STATUS_PENDING)
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'task', 'task_id': tid})
    assert r.status_code == 200
    sid = r.get_json()['data']['id']
    _set_started_ago(client, sid, 300)
    time.sleep(0.3)
    r = client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    assert r.status_code == 200

    with client.application.app_context():
        rec = StudyRecord.query.filter_by(user_id=uid).order_by(StudyRecord.id.desc()).first()
        assert rec.record_type == StudyRecord.MODE_TASK
        assert rec.task_id == tid


def test_stats_split_by_mode(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, '数学', '高数强化', StudyTask.STATUS_PENDING)

    # 番茄钟 25 分钟
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'pomodoro'})
    sid = r.get_json()['data']['id']
    client.post('/api/plans/timer/cycle', headers=auth_headers,
                json={'session_id': sid, 'focus_duration': 1500, 'break_duration': 300})
    time.sleep(0.2)
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})

    # 自由计时 10 分钟
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'countup'})
    sid = r.get_json()['data']['id']
    _set_started_ago(client, sid, 600)
    time.sleep(0.2)
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})

    # 任务计时 5 分钟
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'task', 'task_id': tid})
    sid = r.get_json()['data']['id']
    _set_started_ago(client, sid, 300)
    time.sleep(0.2)
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})

    # 今日统计分别统计
    r = client.get('/api/stat/today', headers=auth_headers)
    d = r.get_json()['data']
    assert d['pomodoro_time'] == 1500
    assert d['free_time'] == 600
    assert d['task_time'] == 300
    assert d['sessions']['pomodoro'] == 1
    assert d['sessions']['countup'] == 1
    assert d['sessions']['task'] == 1

    # 全部统计模式分布
    r = client.get('/api/stat/all', headers=auth_headers)
    d = r.get_json()['data']
    assert d['pomodoro_total'] == 1500
    assert d['countup_total'] == 600
    assert d['task_total'] == 300
    modes = {m['mode']: m['value'] for m in d['mode_distribution']}
    assert modes['pomodoro'] == 1500
    assert modes['countup'] == 600
    assert modes['task'] == 300


def test_pomodoro_break_not_counted(client, auth_headers):
    """番茄钟休息 5 分钟不应计入学习时长（只统计专注段）。"""
    uid = _uid(client)
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'mode': 'pomodoro'})
    sid = r.get_json()['data']['id']
    # 一轮：专注 1500s + 休息 300s
    client.post('/api/plans/timer/cycle', headers=auth_headers,
                json={'session_id': sid, 'focus_duration': 1500, 'break_duration': 300})
    time.sleep(0.3)
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})

    with client.application.app_context():
        rec = StudyRecord.query.filter_by(user_id=uid).order_by(StudyRecord.id.desc()).first()
        # 时长应等于专注时长，不含休息
        assert rec.duration == 1500
        # 明细轮次里休息时长是独立留存，但不进入统计
        cyc = PomodoroCycle.query.filter_by(timer_session_id=sid).first()
        assert cyc.focus_duration == 1500
        assert cyc.break_duration == 300

    r = client.get('/api/stat/all', headers=auth_headers)
    d = r.get_json()['data']
    assert d['pomodoro_total'] == 1500  # 不能出现 1800
