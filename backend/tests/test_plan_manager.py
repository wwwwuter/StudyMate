"""Phase 3 计划确认与版本管理测试。

覆盖：
1. confirm 创建 StudyPlan v1 + 任务 plan_id 关联
2. 同名再次 confirm → v2，旧版本 superseded
3. 时间冲突：新任务与已有未完成任务重叠 → skipped（不覆盖）
4. 已完成任务不参与冲突（done 不挡新任务）
5. detect_conflicts 独立检测
"""
from datetime import date, time as dtime

from app.extensions import db
from models.plan import StudyPlan
from models.task import StudyTask


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid, d, subject, content, start, end, status=StudyTask.STATUS_PENDING):
    with client.application.app_context():
        t = StudyTask(user_id=uid, date=d, subject=subject, content=content,
                      start_time=start, end_time=end, status=status)
        db.session.add(t)
        db.session.commit()
        return t.id


def _tasks():
    return [
        {'date': '2026-08-10', 'subject': '数学', 'content': '高数强化', 'start_time': '08:30', 'end_time': '11:30'},
        {'date': '2026-08-10', 'subject': '408', 'content': '计组', 'start_time': '14:00', 'end_time': '17:30'},
    ]


def test_confirm_creates_plan_v1(client, auth_headers):
    r = client.post('/api/plans/confirm', headers=auth_headers,
                    json={'plan_name': '数学强化计划', 'tasks': _tasks()})
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['version'] == 1
    assert data['created'] == 2
    assert data['skipped'] == []
    with client.application.app_context():
        plan = StudyPlan.query.get(data['plan_id'])
        assert plan.name == '数学强化计划'
        assert plan.version == 1
        tasks = StudyTask.query.filter_by(plan_id=plan.id).all()
        assert len(tasks) == 2
        assert tasks[0].priority == 0


def test_confirm_same_name_bumps_version(client, auth_headers):
    r1 = client.post('/api/plans/confirm', headers=auth_headers,
                     json={'plan_name': '同款计划', 'tasks': _tasks()})
    v1_id = r1.get_json()['data']['plan_id']
    r2 = client.post('/api/plans/confirm', headers=auth_headers,
                     json={'plan_name': '同款计划', 'tasks': _tasks()})
    d2 = r2.get_json()['data']
    assert d2['version'] == 2
    assert d2['plan_id'] != v1_id
    with client.application.app_context():
        v1 = StudyPlan.query.get(v1_id)
        assert v1.status == StudyPlan.STATUS_SUPERSEDED  # 旧版保留但失效
        v2 = StudyPlan.query.get(d2['plan_id'])
        assert v2.status == StudyPlan.STATUS_ACTIVE
        # 历史任务不删除，仍挂在 v1
        assert StudyTask.query.filter_by(plan_id=v1_id).count() == 2


def test_confirm_skips_time_conflict(client, auth_headers):
    uid = _uid(client)
    # 已有 08:30-11:30 数学任务（未开始）→ 新任务同时间段冲突
    _add_task(client, uid, date(2026, 8, 10), '数学', '已有任务', dtime(8, 30), dtime(11, 30))
    r = client.post('/api/plans/confirm', headers=auth_headers,
                    json={'plan_name': '冲突计划', 'tasks': _tasks()})
    data = r.get_json()['data']
    assert data['created'] == 1        # 408 那条 14:00-17:30 无冲突落库
    assert len(data['skipped']) == 1   # 数学那条冲突跳过
    assert data['skipped'][0]['content'] == '高数强化'
    assert 'conflicts_with' in data['skipped'][0]
    with client.application.app_context():
        # 已有任务未被修改/删除
        t = StudyTask.query.filter_by(user_id=uid, content='已有任务').first()
        assert t is not None and t.status == StudyTask.STATUS_PENDING


def test_done_task_not_conflict(client, auth_headers):
    uid = _uid(client)
    # 已有任务已完成 → 不参与冲突，新任务正常落库
    _add_task(client, uid, date(2026, 8, 11), '数学', '已完成任务', dtime(8, 30), dtime(11, 30),
              status=StudyTask.STATUS_DONE)
    r = client.post('/api/plans/confirm', headers=auth_headers,
                    json={'plan_name': '无冲突', 'tasks': [{'date': '2026-08-11', 'subject': '数学',
                                                           'content': '新任务', 'start_time': '09:00',
                                                           'end_time': '10:00'}]})
    data = r.get_json()['data']
    assert data['created'] == 1
    assert data['skipped'] == []


def test_detect_conflicts_api(client, auth_headers):
    uid = _uid(client)
    _add_task(client, uid, date(2026, 8, 12), '英语', '阅读', dtime(19, 0), dtime(20, 30))
    r = client.post('/api/plans/confirm', headers=auth_headers,
                    json={'plan_name': '检测', 'tasks': [
                        {'date': '2026-08-12', 'subject': '英语', 'content': '冲突项',
                         'start_time': '19:30', 'end_time': '20:00'},
                        {'date': '2026-08-13', 'subject': '数学', 'content': '正常项',
                         'start_time': '08:30', 'end_time': '11:30'},
                    ]})
    data = r.get_json()['data']
    assert data['created'] == 1          # 仅 08-13 那条
    assert len(data['skipped']) == 1     # 08-12 冲突
