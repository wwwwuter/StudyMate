"""Phase 6+: 当前任务按时间动态选取（doing > 区间内 > 即将开始 > 兜底）。"""
import datetime as dt
from unittest.mock import patch

from app.extensions import db
from models.task import StudyTask


def _add(client, uid, hour_start, hour_end, subject='数学', date=None):
    with client.application.app_context():
        t = StudyTask(
            user_id=uid, date=date or dt.date.today(), subject=subject, content=subject,
            start_time=dt.time(hour_start, 0), end_time=dt.time(hour_end, 0),
            status=StudyTask.STATUS_PENDING,
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def test_current_task_picks_in_progress_window(client, auth_headers):
    """14:48 当前时间 → 14:00-17:30 任务应被选中（而非 08:30-11:30）。"""
    with client.application.app_context():
        from models.user import User
        uid = db.session.query(User).first().id
    _add(client, uid, 8, 11, '数学')
    _add(client, uid, 14, 17, '408')
    fake_now = dt.datetime(2026, 8, 3, 14, 48)
    with patch('services.stat_service.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.strptime = dt.datetime.strptime
        mock_dt.time = dt.time
        r = client.get('/api/stat/today', headers=auth_headers)
    d = r.get_json()['data']
    assert d['current_task'] is not None
    assert d['current_task']['subject'] == '408'
    assert d['current_task']['start_time'] == '14:00'


def test_current_task_picks_next_upcoming(client, auth_headers):
    """所有今日任务都在未来 → 选最近的下一个（19:00）。"""
    with client.application.app_context():
        from models.user import User
        uid = db.session.query(User).first().id
    _add(client, uid, 19, 21, '英语')
    _add(client, uid, 20, 22, '政治')
    fake_now = dt.datetime(2026, 8, 3, 14, 0)
    with patch('services.stat_service.datetime') as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.strptime = dt.datetime.strptime
        mock_dt.time = dt.time
        r = client.get('/api/stat/today', headers=auth_headers)
    d = r.get_json()['data']
    assert d['current_task']['subject'] == '英语'


def test_current_task_no_match_falls_back(client, auth_headers):
    """无未完成任务时 current_task 可为 None（今日全部 done）。"""
    with client.application.app_context():
        from models.user import User
        uid = db.session.query(User).first().id
    r = client.get('/api/stat/today', headers=auth_headers)
    d = r.get_json()['data']
    assert d['current_task'] is None