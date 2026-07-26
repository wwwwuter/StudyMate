"""Phase 7 数据分析 + 学习报告 测试。"""
from datetime import datetime, timedelta

from app.extensions import db
from models.record import StudyRecord
from models.task import StudyTask
from models.analysis import AIAnalysis


def _login(client, code='analytics_user'):
    r = client.post('/api/auth/wechat/login', json={'code': code})
    token = r.get_json()['data']['token']['access_token']
    return {'Authorization': f'Bearer {token}'}


def _uid(client, code='analytics_user'):
    from models.user import User
    # 测试环境 WECHAT_MOCK=True，code2session 返回确定性 openid
    return User.query.filter_by(openid=f'mock_openid_{code}').first().id


def _seed(client, uid):
    now = datetime.now()
    rec1 = StudyRecord(
        user_id=uid, record_type='countup', subject='数学',
        start_time=now, duration=3600,
    )
    rec2 = StudyRecord(
        user_id=uid, record_type='pomodoro', subject='英语',
        start_time=now - timedelta(days=1), duration=1800,
    )
    db.session.add_all([rec1, rec2])

    t1 = StudyTask(
        user_id=uid, date=now.date(), subject='数学', content='极限训练',
        status=StudyTask.STATUS_DONE, estimated_minutes=120,
    )
    t2 = StudyTask(
        user_id=uid, date=now.date() - timedelta(days=1), subject='英语', content='单词',
        status=StudyTask.STATUS_PENDING, estimated_minutes=60,
    )
    db.session.add_all([t1, t2])
    db.session.commit()


def test_report_metrics(client):
    h = _login(client)
    uid = _uid(client)
    _seed(client, uid)

    r = client.get('/api/analytics/report?range=all', headers=h)
    assert r.status_code == 200, r.get_json()
    d = r.get_json()['data']

    # 时长聚合
    assert d['total_seconds'] == 5400
    assert d['total_hours'] == 1.5
    assert d['session_count'] == 2

    # 模式 / 科目分布
    assert d['by_mode'].get('countup') == 3600
    assert d['by_subject_actual'].get('数学') == 3600

    # 时段分布：24 小时完整且加总等于总时长
    assert len(d['hour_distribution']) == 24
    assert sum(x['seconds'] for x in d['hour_distribution']) == 5400

    # 任务完成率
    assert d['tasks']['total'] == 2
    assert d['tasks']['done'] == 1
    assert d['tasks']['completion_rate'] == 50.0
    assert d['tasks']['planned_minutes'] == 180

    # 连续打卡：今天 + 昨天 >= 2
    assert d['streak'] >= 2

    # 每日序列包含两天
    assert len(d['daily']) == 2


def test_report_invalid_range(client):
    h = _login(client)
    r = client.get('/api/analytics/report?range=year', headers=h)
    assert r.status_code == 400


def test_report_custom_range(client):
    h = _login(client)
    uid = _uid(client)
    _seed(client, uid)
    today = datetime.now().date()
    start = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    r = client.get(f'/api/analytics/report?start={start}&end={end}', headers=h)
    assert r.status_code == 200
    d = r.get_json()['data']
    # 未显式传 range 时默认 week，但 start/end 自定义区间生效
    assert d['range'] == 'week'
    assert d['total_seconds'] == 5400


def test_summary_generates_and_stores(client, monkeypatch):
    # 强制走模板降级，避免测试环境调用真实 DeepSeek
    monkeypatch.setenv('LEARNING_REPORT_MOCK', 'true')
    h = _login(client)
    uid = _uid(client)
    _seed(client, uid)

    r = client.post('/api/analytics/summary', json={'range': 'all'}, headers=h)
    assert r.status_code == 200, r.get_json()
    data = r.get_json()['data']
    assert data['text']
    assert data['source'] == 'template'
    assert '学习报告' in data['text']

    # 落库校验
    count = AIAnalysis.query.filter_by(user_id=uid, analysis_type='learning_report').count()
    assert count == 1
