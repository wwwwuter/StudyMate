"""学习统计模块测试（覆盖需求第十条的四个场景）。

1. 存在学习记录 → 统计正常
2. 无学习记录 → 显示 0
3. 任务完成状态变化 → 完成率同步变化
4. 计时结束 → 统计增加
"""
import time
from datetime import datetime, date, time as dtime, timedelta

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask
from models.user import User


def _uid(client):
    with client.application.app_context():
        return db.session.query(User).first().id


def _add_task(client, uid, subject, content, status, d=None):
    d = d or date.today()
    with client.application.app_context():
        t = StudyTask(
            user_id=uid, date=d, subject=subject, content=content,
            start_time=dtime(9, 0), end_time=dtime(10, 0), status=status,
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def _add_record(client, uid, subject, seconds, start=None, task_id=None):
    start = start or datetime.combine(date.today(), dtime(9, 30))
    with client.application.app_context():
        r = StudyRecord(
            user_id=uid, task_id=task_id,
            start_time=start, end_time=start + timedelta(seconds=seconds),
            duration=seconds, record_type=StudyRecord.MODE_COUNTUP, subject=subject,
        )
        db.session.add(r)
        db.session.commit()
        return r.id


def test_no_records_shows_zero(client, auth_headers):
    r = client.get('/api/stat/today', headers=auth_headers)
    assert r.status_code == 200
    d = r.get_json()['data']
    assert d['study_time'] == 0
    assert d['task_total'] == 0
    assert d['task_completed'] == 0
    assert d['completion_rate'] == 0

    r = client.get('/api/stat/all', headers=auth_headers)
    d = r.get_json()['data']
    assert d['total_time'] == 0
    assert d['total_sessions'] == 0
    assert d['completed_tasks'] == 0
    assert d['completion_rate'] == 0
    assert d['continuous_days'] == 0


def test_with_records_stat_normal(client, auth_headers):
    uid = _uid(client)
    _add_task(client, uid, '数学', '高数强化', StudyTask.STATUS_DONE)
    _add_task(client, uid, '英语', '单词', StudyTask.STATUS_PENDING)
    _add_record(client, uid, '数学', 3600)
    _add_record(client, uid, '英语', 1800)

    r = client.get('/api/stat/today', headers=auth_headers)
    d = r.get_json()['data']
    assert d['study_time'] == 5400
    assert d['task_total'] == 2
    assert d['task_completed'] == 1
    assert d['completion_rate'] == 50
    names = {s['name'] for s in d['subjects']}
    assert '数学' in names and '英语' in names

    r = client.get('/api/stat/all', headers=auth_headers)
    d = r.get_json()['data']
    assert d['total_time'] == 5400
    assert d['total_sessions'] == 2
    assert d['completed_tasks'] == 1
    assert d['completion_rate'] == 50
    assert d['continuous_days'] >= 1


def test_completion_rate_updates_with_task_status(client, auth_headers):
    uid = _uid(client)
    t1 = _add_task(client, uid, '数学', '高数', StudyTask.STATUS_PENDING)
    _add_task(client, uid, '英语', '单词', StudyTask.STATUS_PENDING)

    r = client.get('/api/stat/today', headers=auth_headers)
    assert r.get_json()['data']['completion_rate'] == 0

    # 把一条任务标记为完成
    with client.application.app_context():
        t = StudyTask.query.get(t1)
        t.status = StudyTask.STATUS_DONE
        db.session.commit()

    r = client.get('/api/stat/today', headers=auth_headers)
    assert r.get_json()['data']['completion_rate'] == 50


def test_timer_stop_increments_stat(client, auth_headers):
    uid = _uid(client)
    tid = _add_task(client, uid, '数学', '高数', StudyTask.STATUS_PENDING)

    before = client.get('/api/stat/today', headers=auth_headers).get_json()['data']['study_time']

    # 启动 → 等待 → 结束（计时结束应自动写入 StudyRecord）
    r = client.post('/api/plans/timer/start', headers=auth_headers, json={'task_id': tid})
    assert r.status_code == 200
    time.sleep(1.2)
    r = client.post('/api/plans/timer/stop', headers=auth_headers, json={})
    assert r.status_code == 200

    with client.application.app_context():
        rec_count = StudyRecord.query.filter_by(user_id=uid).count()
    assert rec_count >= 1

    after = client.get('/api/stat/today', headers=auth_headers).get_json()['data']['study_time']
    assert after > before
