"""Phase 6 统计系统升级测试。

覆盖：
1. today_stat 返回 current_task（今日最早未完成任务）
2. all_stat 返回 plan_execution_rate（计划执行率）
3. all_stat 返回 plan_stats（按 StudyPlan 版本聚合的执行情况）
"""
from datetime import date, time as dtime

from app.extensions import db
from models.plan import StudyPlan
from models.task import StudyTask


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid, d, subject, content, start=None, end=None, status='pending', plan_id=None):
    with client.application.app_context():
        t = StudyTask(user_id=uid, plan_id=plan_id, date=d, subject=subject, content=content,
                      start_time=start, end_time=end, status=status)
        db.session.add(t)
        db.session.commit()
        return t.id


def test_today_stat_current_task(client, auth_headers):
    uid = _uid(client)
    today = date.today()
    _add_task(client, uid, today, '数学', '已完成任务', dtime(8, 30), dtime(9, 30), status='done')
    _add_task(client, uid, today, '英语', '当前任务', dtime(10, 0), dtime(11, 0))
    r = client.get('/api/stat/today', headers=auth_headers)
    data = r.get_json()['data']
    assert data['current_task'] is not None
    assert data['current_task']['content'] == '当前任务'
    assert data['current_task']['status'] in ('pending', 'doing')


def test_all_stat_plan_execution_rate(client, auth_headers):
    uid = _uid(client)
    _add_task(client, uid, date.today(), '数学', '任务A', status='done')
    _add_task(client, uid, date.today(), '英语', '任务B', status='pending')
    r = client.get('/api/stat/all', headers=auth_headers)
    data = r.get_json()['data']
    assert 'plan_execution_rate' in data
    assert data['plan_execution_rate'] == 50  # 1/2
    assert isinstance(data['plan_stats'], list)


def test_all_stat_plan_stats_by_version(client, auth_headers):
    uid = _uid(client)
    with client.application.app_context():
        p = StudyPlan(user_id=uid, name='暑假计划', version=1)
        db.session.add(p)
        db.session.commit()
        pid = p.id
    _add_task(client, uid, date.today(), '数学', '计划内已完成', plan_id=pid, status='done')
    _add_task(client, uid, date.today(), '408', '计划内未完成', plan_id=pid, status='pending')
    r = client.get('/api/stat/all', headers=auth_headers)
    data = r.get_json()['data']
    stats = [s for s in data['plan_stats'] if s['plan_id'] == pid]
    assert len(stats) == 1
    assert stats[0]['plan_name'] == '暑假计划'
    assert stats[0]['version'] == 1
    assert stats[0]['total'] == 2
    assert stats[0]['done'] == 1
    assert stats[0]['rate'] == 50
