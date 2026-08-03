"""Phase 4 计划计时倒计时改造测试。

覆盖：
1. task 模式 timer_start → TimerSession.plan_start_time/plan_end_time 由 StudyTask 填充（本地→UTC）
2. 未超时结束 → StudyRecord.extra_duration == 0
3. 超过计划结束时间结束 → extra_duration = 超时秒数（计划外额外学习时长）
"""
from datetime import date, datetime, time as dtime, timedelta

from app.extensions import db
from models.task import StudyTask
from models.timer_session import TimerSession
from models.record import StudyRecord


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid, d, subject='数学', content='高数强化',
              start=dtime(8, 30), end=dtime(11, 30)):
    with client.application.app_context():
        t = StudyTask(user_id=uid, date=d, subject=subject, content=content,
                      start_time=start, end_time=end)
        db.session.add(t)
        db.session.commit()
        return t.id


def test_task_start_fills_plan_window(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, date(2026, 8, 15))
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'task', 'task_id': tid})
    assert r.status_code == 200
    d = r.get_json()['data']
    assert d['plan_start_time'] is not None
    assert d['plan_end_time'] is not None
    # plan_end 对应本地 11:30 → UTC 03:30
    assert d['plan_end_time'].startswith('2026-08-15T03:30')
    # 结束当前计时，避免影响后续
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})


def test_no_overtime_extra_zero(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, date(2026, 8, 16))
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'task', 'task_id': tid})
    sid = r.get_json()['data']['id']
    # 模拟：已学习 2 小时，计划结束时间在未来（未超时）
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        s.started_at = datetime.utcnow() - timedelta(hours=2)
        s.plan_start_time = datetime.utcnow() - timedelta(hours=1)
        s.plan_end_time = datetime.utcnow() + timedelta(hours=3)
        db.session.commit()
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    with client.application.app_context():
        rec = (StudyRecord.query
               .filter_by(user_id=uid, record_type=StudyRecord.MODE_TASK)
               .order_by(StudyRecord.id.desc()).first())
        assert rec is not None
        assert rec.extra_duration == 0
        # 未超时：有效时长 = 真实时长（2 小时）
        assert rec.duration == 7200
        assert rec.effective_duration == 7200
        # 计划安排时长 = plan_end - plan_start = 4 小时
        assert rec.planned_duration == 4 * 3600


def test_overtime_records_extra(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, date(2026, 8, 17))
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'task', 'task_id': tid})
    sid = r.get_json()['data']['id']
    # 模拟：已学习 3 小时，计划结束时间已过 5 分钟（用户继续学习）
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        s.started_at = datetime.utcnow() - timedelta(hours=3)
        s.plan_start_time = datetime.utcnow() - timedelta(hours=3)
        s.plan_end_time = datetime.utcnow() - timedelta(minutes=5)
        db.session.commit()
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    with client.application.app_context():
        rec = (StudyRecord.query
               .filter_by(user_id=uid, record_type=StudyRecord.MODE_TASK)
               .order_by(StudyRecord.id.desc()).first())
        assert rec is not None
        # 真实投入 3 小时
        assert rec.duration == 3 * 3600
        # 计划有效时长 = plan_end - actual_start = 2h55m
        assert rec.effective_duration == 10500
        # 额外学习 = ended - plan_end = 5 分钟
        assert rec.extra_duration == 300
        # 计划安排时长 = plan_end - plan_start = 2h55m（测试里 plan_start=now-3h, plan_end=now-5min）
        assert rec.planned_duration == 10500


def test_stale_task_extra_is_zero(client, auth_headers):
    """过期任务（计划日期早于今天）补学：plan_end 早于 started_at → extra 必须为 0。"""
    uid = _uid(client)
    yesterday = date.today() - timedelta(days=1)
    tid = _add_task(client, uid, yesterday, start=dtime(7, 30), end=dtime(8, 30))
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'task', 'task_id': tid})
    sid = r.get_json()['data']['id']
    # 模拟已计时 1 分钟（避免 duration≈0 被 _sync 跳过）
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        s.started_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
    client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    with client.application.app_context():
        rec = (StudyRecord.query
               .filter_by(user_id=uid, task_id=tid)
               .order_by(StudyRecord.id.desc()).first())
        assert rec is not None
        assert rec.extra_duration == 0  # 过期补学不计额外
        assert rec.duration > 0
