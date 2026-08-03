"""Phase 1 计划数据库升级测试。

覆盖：
1. StudyPlan 创建 / 版本递增（同名 v1 → v2）
2. supersede_older 把旧版本标记 superseded（历史保留）
3. StudyTask.plan_id 关联 StudyPlan
4. StudyTask 状态扩展：running / expired 合法
5. StudyRecord.extra_duration 默认 0
6. TimerSession plan_start_time / plan_end_time 字段
7. ensure_schema 幂等（内存库重复执行不报错、不重复加列）
"""
from datetime import datetime, timedelta

from app.extensions import db
from models.plan import StudyPlan
from models.task import StudyTask
from models.record import StudyRecord
from models.timer_session import TimerSession


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _mk_plan(client, uid, name, version):
    with client.application.app_context():
        p = StudyPlan(user_id=uid, name=name, version=version, source='pdf')
        db.session.add(p)
        db.session.commit()
        return p.id


def test_plan_create_and_next_version(client, auth_headers):
    uid = _uid(client)
    _mk_plan(client, uid, '数学强化计划', 1)
    with client.application.app_context():
        assert StudyPlan.next_version(uid, '数学强化计划') == 2
        assert StudyPlan.next_version(uid, '全新的计划') == 1


def test_plan_supersede_keeps_history(client, auth_headers):
    uid = _uid(client)
    p1 = _mk_plan(client, uid, '暑假计划', 1)
    _mk_plan(client, uid, '暑假计划', 2)
    with client.application.app_context():
        StudyPlan.supersede_older(uid, '暑假计划', keep_version=2)
        db.session.commit()
        v1 = StudyPlan.query.get(p1)
        v2 = StudyPlan.query.filter_by(user_id=uid, name='暑假计划', version=2).first()
        assert v1.status == StudyPlan.STATUS_SUPERSEDED  # 旧版保留但失效
        assert v2.status == StudyPlan.STATUS_ACTIVE      # 新版本生效


def test_task_plan_id_link(client, auth_headers):
    uid = _uid(client)
    pid = _mk_plan(client, uid, '数学强化计划', 1)
    with client.application.app_context():
        import datetime as dt
        t = StudyTask(user_id=uid, plan_id=pid, date=dt.date.today(),
                      subject='数学', content='不定积分')
        db.session.add(t)
        db.session.commit()
        tid = t.id
    with client.application.app_context():
        t2 = StudyTask.query.get(tid)
        assert t2.plan_id == pid
        assert 'plan_id' in t2.to_dict()


def test_task_status_extension(client, auth_headers):
    """状态枚举扩展：running / expired 为合法状态。"""
    uid = _uid(client)
    with client.application.app_context():
        import datetime as dt
        t = StudyTask(user_id=uid, date=dt.date.today(), subject='数学',
                      content='测试', status=StudyTask.STATUS_RUNNING)
        db.session.add(t)
        db.session.commit()
        assert t.status == 'running'
        assert StudyTask.is_valid_status('running')
        assert StudyTask.is_valid_status('expired')


def test_record_extra_duration_default(client, auth_headers):
    uid = _uid(client)
    with client.application.app_context():
        r = StudyRecord(user_id=uid, start_time=datetime.utcnow(),
                        end_time=datetime.utcnow(), duration=600,
                        record_type=StudyRecord.MODE_TASK)
        db.session.add(r)
        db.session.commit()
        assert r.extra_duration == 0
        r.extra_duration = 120  # 超时继续学习时长
        db.session.commit()
        assert r.to_dict()['extra_duration'] == 120


def test_timer_session_plan_window(client, auth_headers):
    uid = _uid(client)
    with client.application.app_context():
        s = TimerSession(user_id=uid, mode=TimerSession.MODE_TASK,
                         started_at=datetime.utcnow(),
                         plan_start_time=datetime.utcnow(),
                         plan_end_time=datetime.utcnow() + timedelta(hours=3),
                         status=TimerSession.STATUS_RUNNING)
        db.session.add(s)
        db.session.commit()
        d = s.to_dict()
        assert d['plan_start_time'] is not None
        assert d['plan_end_time'] is not None


def test_ensure_schema_idempotent(app):
    """ensure_schema 幂等：连续执行不报错、列不重复。"""
    from app.schema_migrate import ensure_schema
    ensure_schema(app)
    ensure_schema(app)
    with app.app_context():
        from sqlalchemy import inspect
        insp = inspect(db.engine)
        cols = {c['name'] for c in insp.get_columns('study_records')}
        assert 'extra_duration' in cols
        tcols = {c['name'] for c in insp.get_columns('timer_sessions')}
        assert 'plan_start_time' in tcols
        assert 'plan_end_time' in tcols
        tcols2 = {c['name'] for c in insp.get_columns('study_tasks')}
        assert 'plan_id' in tcols2
        # 表已建
        assert insp.has_table('study_plans')
