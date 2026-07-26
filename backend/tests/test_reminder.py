"""Phase 6 提醒系统测试：APScheduler 扫描生成、去重、过滤、回执与设置。"""
from datetime import timedelta

from app.extensions import db
from models.user import User
from models.task import StudyTask
from models.reminder import Reminder, ReminderSetting
from services.reminder_service import sweep_due_reminders, get_setting
from utils.time_utils import utcnow


def _login(client):
    r = client.post('/api/auth/wechat/login', json={'code': 'reminder-test'})
    token = r.get_json()['data']['token']['access_token']
    return {'Authorization': f'Bearer {token}'}


def _post_task(client, headers, date_str, start_str, subject='数学', content='极限'):
    r = client.post(
        '/api/tasks',
        json={'date': date_str, 'subject': subject, 'content': content,
              'start_time': start_str, 'end_time': None, 'status': 'pending'},
        headers=headers,
    )
    return r.get_json()['data']


def test_sweep_creates_reminder_for_soon_task(app, client):
    h = _login(client)
    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(minutes=5)).strftime('%H:%M')  # 5 分钟后开始，默认提前 10 分钟 → 触发
    _post_task(client, h, d, start)

    with app.app_context():
        created = sweep_due_reminders()
        assert created == 1
        rs = Reminder.query.all()
        assert len(rs) == 1
        assert rs[0].subject == '数学'
        assert rs[0].delivered is False


def test_sweep_skips_far_future_task(app, client):
    h = _login(client)
    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(hours=3)).strftime('%H:%M')  # 3 小时后，超提前量 → 不触发
    _post_task(client, h, d, start)

    with app.app_context():
        assert sweep_due_reminders() == 0
        assert Reminder.query.count() == 0


def test_sweep_skips_cancelled_task(app, client):
    h = _login(client)
    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(minutes=5)).strftime('%H:%M')
    _post_task(client, h, d, start)

    # 取消该任务
    items = client.get('/api/tasks', headers=h).get_json()['data']
    tid = items[0]['id']
    client.put(f'/api/tasks/{tid}', json={'status': 'cancelled'}, headers=h)

    with app.app_context():
        assert sweep_due_reminders() == 0
        assert Reminder.query.count() == 0


def test_sweep_dedup(app, client):
    h = _login(client)
    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(minutes=5)).strftime('%H:%M')
    _post_task(client, h, d, start)

    with app.app_context():
        assert sweep_due_reminders() == 1
        # 再次扫描同一任务不应重复生成
        assert sweep_due_reminders() == 0
        assert Reminder.query.count() == 1


def test_respects_user_setting_disabled(app, client):
    h = _login(client)
    # 读取当前用户 id：通过 me 接口
    uid = client.get('/api/auth/me', headers=h).get_json()['data']['id']
    with app.app_context():
        s = db.session.get(ReminderSetting, uid) or ReminderSetting(user_id=uid, enabled=False)
        s.enabled = False
        db.session.add(s)
        db.session.commit()

    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(minutes=5)).strftime('%H:%M')
    _post_task(client, h, d, start)

    with app.app_context():
        assert sweep_due_reminders() == 0
        assert Reminder.query.count() == 0


def test_pending_and_ack(app, client):
    h = _login(client)
    now = utcnow()
    d = now.date().isoformat()
    start = (now + timedelta(minutes=5)).strftime('%H:%M')
    _post_task(client, h, d, start)

    # 通过调度端点触发扫描（请求上下文内提交，与正式运行一致）
    sweep_resp = client.post('/api/reminders/sweep', headers=h)
    assert sweep_resp.get_json()['data']['created'] == 1

    # pending 返回 1 条
    r1 = client.get('/api/reminders/pending', headers=h)
    assert r1.status_code == 200
    items = r1.get_json()['data']
    assert len(items) == 1
    rid = items[0]['id']

    # ack 后 pending 清空
    r2 = client.post('/api/reminders/ack', json={'ids': [rid]}, headers=h)
    assert r2.get_json()['data']['count'] == 1
    r3 = client.get('/api/reminders/pending', headers=h)
    assert r3.get_json()['data'] == []


def test_settings_get_and_save(app, client):
    h = _login(client)
    g = client.get('/api/reminders/settings', headers=h)
    assert g.status_code == 200
    assert g.get_json()['data']['enabled'] is True

    s = client.post('/api/reminders/settings', json={'enabled': True, 'lead_minutes': 30}, headers=h)
    assert s.status_code == 200
    assert s.get_json()['data']['lead_minutes'] == 30

    g2 = client.get('/api/reminders/settings', headers=h)
    assert g2.get_json()['data']['lead_minutes'] == 30


def test_scheduler_start_stop(app):
    import services.reminder_service as rs
    # 验证调度器可正常拉起与停止（应用工厂在测试环境不自动拉起）
    rs.start_scheduler(app)
    assert rs._scheduler is not None and rs._scheduler.running
    rs.stop_scheduler()
    assert rs._scheduler is None or not rs._scheduler.running
