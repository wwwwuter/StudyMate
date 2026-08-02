"""AI 学习建议测试（今日复习情况 → 建议）。

覆盖：
1. 无任何数据 → 规则模板建议（source='template'）
2. 有任务 + 计时记录 → 模板建议包含完成率 / 时长
3. 完成率低 → problems 提示
4. 单科占比过高 → 科目均衡提示
5. 有可用 Key（mock）→ source='ai' 且解析出 summary/problems/suggestions
6. AI 调用失败 → 自动回退模板
7. HTTP 接口 /api/ai/analyze 返回结构 {code, data{source,...}}
"""
from datetime import datetime, timedelta

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask


def _uid(client):
    with client.application.app_context():
        from models.user import User
        return db.session.query(User).first().id


def _add_task(client, uid, subject, content, status):
    with client.application.app_context():
        from datetime import time as dtime
        import datetime as dt
        t = StudyTask(
            user_id=uid, date=dt.date.today(), subject=subject, content=content,
            start_time=dtime(9, 0), end_time=dtime(10, 0), status=status,
        )
        db.session.add(t)
        db.session.commit()
        return t.id


def _add_record(client, uid, duration, subject='数学', record_type=StudyRecord.MODE_COUNTUP):
    """直接插入一条今日学习记录（模拟计时结束自动同步的结果）。"""
    with client.application.app_context():
        r = StudyRecord(
            user_id=uid,
            task_id=None,
            start_time=datetime.utcnow() - timedelta(seconds=duration),
            end_time=datetime.utcnow(),
            duration=duration,
            record_type=record_type,
            subject=subject,
        )
        db.session.add(r)
        db.session.commit()


# ------------------------- 规则模板（降级路径） -------------------------

def test_template_advice_empty(client, auth_headers):
    """无任务无记录 → 提示今天还没有学习记录。"""
    r = client.post('/api/ai/analyze', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['source'] == 'template'
    assert '还没有学习记录' in data['summary']
    assert data['problems'] and data['suggestions']


def test_template_advice_with_data(client, auth_headers):
    """2 个任务完成 1 个 + 60 分钟记录 → summary 含完成率与时长，problems 提示完成率。"""
    uid = _uid(client)
    _add_task(client, uid, '数学', '高数强化', 'done')
    _add_task(client, uid, '英语', '阅读两篇', 'pending')
    _add_record(client, uid, 3600, subject='数学')

    r = client.post('/api/ai/analyze', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['source'] == 'template'
    assert '60 分钟' in data['summary']
    assert '1/2' in data['summary']
    assert '50%' in data['summary']
    assert '完成率' in data['problems']


def test_template_advice_low_rate(client, auth_headers):
    """任务全未完成 → problems 提示完成率偏低。"""
    uid = _uid(client)
    _add_task(client, uid, '数学', '高数强化', 'pending')
    _add_task(client, uid, '英语', '阅读两篇', 'pending')
    _add_record(client, uid, 1800, subject='数学')

    r = client.post('/api/ai/analyze', headers=auth_headers)
    data = r.get_json()['data']
    assert '偏低' in data['problems']


def test_template_advice_subject_imbalance(client, auth_headers):
    """单科占比 >= 70% → problems 提示科目失衡。"""
    uid = _uid(client)
    _add_record(client, uid, 3600, subject='数学')
    _add_record(client, uid, 600, subject='英语')

    r = client.post('/api/ai/analyze', headers=auth_headers)
    data = r.get_json()['data']
    assert '数学' in data['problems']
    assert '均衡' in data['suggestions']


# ------------------------- AI 路径 -------------------------

def test_analyze_ai_source(client, auth_headers, monkeypatch):
    """有可用 Key（mock）→ source='ai'，解析出三字段。"""
    import ai.service as svc

    class FakeClient:
        def is_available(self):
            return True

        def chat(self, messages, **kwargs):
            return '{"summary":"总结","problems":"问题","suggestions":"建议"}'

    monkeypatch.setattr(svc.AIService, 'client_for_user', lambda self, uid: FakeClient())
    r = client.post('/api/ai/analyze', headers=auth_headers)
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['source'] == 'ai'
    assert data['summary'] == '总结'
    assert data['problems'] == '问题'
    assert data['suggestions'] == '建议'
    assert data['generated_at']


def test_analyze_ai_failure_falls_back_to_template(client, auth_headers, monkeypatch):
    """AI 调用抛异常 → 自动回退模板（source='template'，HTTP 仍 200）。"""
    import ai.service as svc

    class BrokenClient:
        def is_available(self):
            return True

        def chat(self, messages, **kwargs):
            raise RuntimeError('upstream down')

    monkeypatch.setattr(svc.AIService, 'client_for_user', lambda self, uid: BrokenClient())
    r = client.post('/api/ai/analyze', headers=auth_headers)
    assert r.status_code == 200
    assert r.get_json()['data']['source'] == 'template'
