"""Phase 6-5：僵尸计时清理（running 超时自动结束落库）。"""
import datetime as dt

from app.extensions import db
from models.timer_session import TimerSession
from models.record import StudyRecord


def _start_task_session(client, auth_headers, uid, hours_ago=1, plan_end_delta=None):
    """开启 task 计时，并回填 started_at / plan_end_time 模拟历史场景。"""
    r = client.post('/api/plans/timer/start', headers=auth_headers,
                    json={'mode': 'countup', 'note': '僵尸测试'})
    sid = r.get_json()['data']['id']
    with client.application.app_context():
        s = TimerSession.query.get(sid)
        s.started_at = dt.datetime.utcnow() - dt.timedelta(hours=hours_ago)
        if plan_end_delta is not None:
            s.mode = TimerSession.MODE_TASK
            s.task_id = uid  # 仅占位，不影响清理判定
            s.plan_end_time = dt.datetime.utcnow() - dt.timedelta(hours=plan_end_delta)
        db.session.commit()
    return sid


def test_cleanup_closes_very_old_running(app, client, auth_headers):
    _start_task_session(client, auth_headers, 1, hours_ago=48)
    from scheduler.timer_cleanup import cleanup_stale_sessions
    n = cleanup_stale_sessions(app)
    assert n == 1
    with client.application.app_context():
        s = TimerSession.query.first()
        assert s.status == TimerSession.STATUS_DONE
        assert s.ended_at is not None
        # 结束已落 StudyRecord（统计口径一致）
        rec = StudyRecord.query.filter_by(task_id=s.task_id).first()
        assert rec is not None


def test_cleanup_keeps_recent_running(app, client, auth_headers):
    _start_task_session(client, auth_headers, 1, hours_ago=1)
    from scheduler.timer_cleanup import cleanup_stale_sessions
    n = cleanup_stale_sessions(app)
    assert n == 0
    with client.application.app_context():
        s = TimerSession.query.first()
        assert s.status == TimerSession.STATUS_RUNNING


def test_cleanup_task_overtime_past_24h(app, client, auth_headers):
    """task 模式超过计划结束 24 小时但 started_at 未超 12h → 也应清理。"""
    _start_task_session(client, auth_headers, 1, hours_ago=10, plan_end_delta=30)
    from scheduler.timer_cleanup import cleanup_stale_sessions
    n = cleanup_stale_sessions(app)
    assert n == 1
    with client.application.app_context():
        s = TimerSession.query.first()
        assert s.status == TimerSession.STATUS_DONE


def test_cleanup_idempotent(app, client, auth_headers):
    _start_task_session(client, auth_headers, 1, hours_ago=48)
    from scheduler.timer_cleanup import cleanup_stale_sessions
    assert cleanup_stale_sessions(app) == 1
    assert cleanup_stale_sessions(app) == 0  # 已 done，不再重复
