"""学习计划接口测试（本地账号鉴权）。

基于 SQLite 内存库 + 本地注册登录令牌，覆盖任务 CRUD、批量创建、过滤、
分页、每日统计与字段校验。计划文件导入统一走 /api/plans/parse（AI 解析，
需用户在「设置」页配置 Key），相关用例见 test_plan_parse.py。
"""


def _login(client, username="plan_user"):
    """注册本地账号并换取 Bearer 头。"""
    resp = client.post('/api/auth/register', json={'username': username, 'password': 'pw123456'})
    assert resp.status_code == 201, resp.get_json()
    token = resp.get_json()['data']['token']
    return {'Authorization': f'Bearer {token}'}


# ---- 创建 ----
def test_create_task_full_fields(client):
    h = _login(client)
    body = {
        'date': '2026-08-01',
        'subject': '高数',        # 别名，应归一化为「数学」
        'content': '高数强化训练',
        'start_time': '08:30',
        'end_time': '11:30',
        'status': 'pending',
    }
    resp = client.post('/api/tasks', json=body, headers=h)
    assert resp.status_code == 201, resp.get_json()
    d = resp.get_json()['data']
    assert d['subject'] == '数学'          # 归一化生效
    assert d['start_time'] == '08:30'
    assert d['plan_source'] == 'manual'


def test_create_missing_required(client):
    h = _login(client)
    resp = client.post('/api/tasks', json={'date': '2026-08-01'}, headers=h)
    assert resp.status_code == 400


def test_create_invalid_status(client):
    h = _login(client)
    resp = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'x', 'status': 'bogus'
    }, headers=h)
    assert resp.status_code == 400


def test_create_requires_auth(client):
    resp = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'x'
    })
    assert resp.status_code == 401


# ---- 查询 / 过滤 ----
def test_get_by_id(client):
    h = _login(client)
    created = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '英语', 'content': '阅读'
    }, headers=h).get_json()['data']
    rid = created['id']

    resp = client.get(f'/api/tasks/{rid}', headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['data']['id'] == rid


def test_get_not_found(client):
    h = _login(client)
    resp = client.get('/api/tasks/99999', headers=h)
    assert resp.status_code == 404


def test_list_filter_by_date(client):
    h = _login(client)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '数学', 'content': 'A'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-08-02', 'subject': '数学', 'content': 'B'}, headers=h)

    resp = client.get('/api/tasks?date=2026-08-01', headers=h)
    data = resp.get_json()['data']
    assert len(data) == 1
    assert data[0]['content'] == 'A'


def test_list_filter_by_subject_and_status(client):
    h = _login(client)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '数学', 'content': 'A'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '英语', 'content': 'B', 'status': 'done'}, headers=h)

    # subject 归一化：传「高数」也能命中「数学」
    resp = client.get('/api/tasks?subject=高数', headers=h)
    assert len(resp.get_json()['data']) == 1

    resp2 = client.get('/api/tasks?status=done', headers=h)
    assert len(resp2.get_json()['data']) == 1
    assert resp2.get_json()['data'][0]['content'] == 'B'


# ---- 更新 / 删除 ----
def test_update_full_fields(client):
    h = _login(client)
    rid = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'A'
    }, headers=h).get_json()['data']['id']

    resp = client.put(f'/api/tasks/{rid}', json={
        'date': '2026-08-03', 'subject': '政治', 'content': '背诵',
        'start_time': '19:00', 'end_time': '20:30', 'status': 'done'
    }, headers=h)
    assert resp.status_code == 200, resp.get_json()
    d = resp.get_json()['data']
    assert d['date'] == '2026-08-03'
    assert d['subject'] == '政治'
    assert d['status'] == 'done'


def test_update_not_found(client):
    h = _login(client)
    resp = client.put('/api/tasks/99999', json={'content': 'x'}, headers=h)
    assert resp.status_code == 404


def test_delete_and_404(client):
    h = _login(client)
    rid = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'A'
    }, headers=h).get_json()['data']['id']

    assert client.delete(f'/api/tasks/{rid}', headers=h).status_code == 200
    assert client.get(f'/api/tasks/{rid}', headers=h).status_code == 404


# ---- 批量 ----
def test_batch_create(client):
    h = _login(client)
    items = [
        {'date': '2026-08-01', 'subject': '数学', 'content': 'A'},
        {'date': '2026-08-02', 'subject': '英语', 'content': 'B'},
    ]
    resp = client.post('/api/tasks/batch', json=items, headers=h)
    assert resp.status_code == 201
    assert resp.get_json()['data'][1]['content'] == 'B'


def test_batch_invalid_item(client):
    h = _login(client)
    items = [{'date': '2026-08-01', 'subject': '数学'}]  # 缺 content
    resp = client.post('/api/tasks/batch', json=items, headers=h)
    assert resp.status_code == 400


def test_batch_delete(client):
    h = _login(client)
    a = client.post('/api/tasks', json={'date': '2026-09-01', 'subject': '数学', 'content': 'A'}, headers=h).get_json()['data']['id']
    b = client.post('/api/tasks', json={'date': '2026-09-01', 'subject': '英语', 'content': 'B'}, headers=h).get_json()['data']['id']
    c = client.post('/api/tasks', json={'date': '2026-09-01', 'subject': '政治', 'content': 'C'}, headers=h).get_json()['data']['id']

    # 缺 ids -> 400
    assert client.delete('/api/tasks/batch', json={}, headers=h).status_code == 400

    # 批量删除 a, b
    resp = client.delete('/api/tasks/batch', json={'ids': [a, b]}, headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['data']['deleted'] == 2

    # 删除后只剩 c
    rows = client.get('/api/tasks?date=2026-09-01', headers=h).get_json()['data']
    assert [r['id'] for r in rows] == [c]


# ---- 按条件删除 ----
def test_delete_by_criteria(client):
    h = _login(client)
    # 数学，8-1 08:30-10:30
    client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'A',
        'start_time': '08:30', 'end_time': '10:30', 'status': 'pending',
    }, headers=h)
    # 数学，8-2 14:00-16:00
    client.post('/api/tasks', json={
        'date': '2026-08-02', 'subject': '数学', 'content': 'B',
        'start_time': '14:00', 'end_time': '16:00', 'status': 'done',
    }, headers=h)
    # 英语，8-1 09:00-11:00
    client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '英语', 'content': 'C',
        'start_time': '09:00', 'end_time': '11:00', 'status': 'pending',
    }, headers=h)

    # 按科目删除：删 2 条数学
    resp = client.post('/api/tasks/delete-by-criteria', json={'subject': '数学'}, headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['data']['deleted'] == 2

    # 重新建数据测试日期范围 + 时间段
    client.post('/api/tasks', json={
        'date': '2026-08-05', 'subject': '数学', 'content': 'D',
        'start_time': '08:30', 'end_time': '10:30', 'status': 'pending',
    }, headers=h)
    client.post('/api/tasks', json={
        'date': '2026-08-06', 'subject': '数学', 'content': 'E',
        'start_time': '14:00', 'end_time': '16:00', 'status': 'pending',
    }, headers=h)

    # 日期范围 8-01 到 8-05，应删 D（8-5）和之前的英语 C（如果还在）
    # 但 C 已在 8-1；数学已被删；所以只剩 C 和 E？
    # 重新整理：当前剩余 C(8-1 英语) 和 D(8-5 数学) 和 E(8-6 数学)
    resp = client.post('/api/tasks/delete-by-criteria', json={'start_date': '2026-08-01', 'end_date': '2026-08-05'}, headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['data']['deleted'] == 2  # C 和 D

    # 预览：当前只剩 E(8-6 14:00-16:00)，按时间段 08:00-12:00 应匹配 0
    resp = client.post('/api/tasks/delete-by-criteria/preview', json={'start_time': '08:00', 'end_time': '12:00'}, headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['data']['count'] == 0

    # 无条件 -> 400
    resp = client.post('/api/tasks/delete-by-criteria', json={}, headers=h)
    assert resp.status_code == 400


# ---- 区间过滤 ----
def test_list_filter_by_keyword_matches_subject_and_content(client):
    h = _login(client)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '数学', 'content': '高数强化'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '英语', 'content': '数学词汇'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '政治', 'content': '马原'}, headers=h)

    # 搜科目
    resp = client.get('/api/tasks?keyword=数学', headers=h)
    rows = resp.get_json()['data']
    assert len(rows) == 2
    assert {r['subject'] for r in rows} == {'数学', '英语'}

    # 搜内容
    resp = client.get('/api/tasks?keyword=马原', headers=h)
    rows = resp.get_json()['data']
    assert len(rows) == 1
    assert rows[0]['subject'] == '政治'


# ---- 区间过滤 ----
def test_list_filter_by_date_range(client):
    h = _login(client)
    client.post('/api/tasks', json={'date': '2026-11-01', 'subject': '数学', 'content': 'A'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-11-15', 'subject': '数学', 'content': 'B'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-12-01', 'subject': '数学', 'content': 'C'}, headers=h)

    resp = client.get('/api/tasks?start_date=2026-11-10&end_date=2026-11-30', headers=h)
    rows = resp.get_json()['data']
    assert len(rows) == 1
    assert rows[0]['content'] == 'B'


# ---- 每日统计 ----
def test_daily_stats(client):
    h = _login(client)
    client.post('/api/tasks', json={'date': '2026-08-10', 'subject': '数学', 'content': 'A'}, headers=h)
    client.post('/api/tasks', json={'date': '2026-08-10', 'subject': '英语', 'content': 'B', 'status': 'done'}, headers=h)

    resp = client.get('/api/tasks/stats/daily?date=2026-08-10', headers=h)
    d = resp.get_json()['data']
    assert d['total'] == 2
    assert d['done'] == 1
    assert d['completion_rate'] == 50.0
    assert set(d['subjects']) == {'数学', '英语'}


# ---- 更新校验 ----
def test_update_invalid_date(client):
    h = _login(client)
    rid = client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '数学', 'content': 'A'}, headers=h).get_json()['data']['id']
    resp = client.put(f'/api/tasks/{rid}', json={'date': 'bad-date'}, headers=h)
    assert resp.status_code == 400


def test_update_empty_subject(client):
    h = _login(client)
    rid = client.post('/api/tasks', json={'date': '2026-08-01', 'subject': '数学', 'content': 'A'}, headers=h).get_json()['data']['id']
    resp = client.put(f'/api/tasks/{rid}', json={'subject': '  '}, headers=h)
    assert resp.status_code == 400


# ---- 时间段校验 ----
def test_create_invalid_time_range(client):
    h = _login(client)
    resp = client.post('/api/tasks', json={
        'date': '2026-08-01', 'subject': '数学', 'content': 'A',
        'start_time': '11:00', 'end_time': '09:00',
    }, headers=h)
    assert resp.status_code == 400


# ---- 分页 ----
def test_list_pagination(client):
    h = _login(client)
    for i in range(5):
        client.post('/api/tasks', json={'date': '2026-08-20', 'subject': '数学', 'content': f'任务{i}'}, headers=h)
    resp = client.get('/api/tasks?date=2026-08-20&page=1&page_size=2', headers=h)
    body = resp.get_json()
    assert body['total'] == 5
    assert len(body['data']) == 2
    assert body['page'] == 1 and body['page_size'] == 2
    # 第二页
    resp2 = client.get('/api/tasks?date=2026-08-20&page=2&page_size=2', headers=h)
    assert len(resp2.get_json()['data']) == 2
