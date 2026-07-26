"""Phase 3 学习计划系统接口测试。

基于 SQLite 内存库 + 真实 JWT（通过 mock 微信 code 登录获取），覆盖
CRUD、批量创建、过滤、鉴权以及 Excel/JSON 导入。
"""
import io
import json

import pytest


def _login(client, code='plan_code'):
    """用 mock 微信 code 登录换取 Bearer 头。"""
    resp = client.post('/api/auth/wechat/login', json={'code': code})
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()['data']['token']['access_token']
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


# ---- JSON 导入 ----
def test_import_json(client):
    h = _login(client)
    payload = [
        {'date': '2026-09-01', 'subject': '高数', 'content': '极限', 'start_time': '08:00', 'end_time': '10:00'},
        {'date': '2026-09-02', 'subject': '英语', 'content': '单词', 'status': 'done'},
    ]
    data = {'file': (io.BytesIO(json.dumps(payload).encode('utf-8')), 'plan.json')}
    resp = client.post('/api/tasks/import/json', data=data, headers=h, content_type='multipart/form-data')
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()['data']['count'] == 2
    # 归一化生效
    assert resp.get_json()['data']['tasks'][0]['subject'] == '数学'


# ---- Excel 导入 ----
def test_import_excel(client):
    h = _login(client)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(['日期', '科目', '内容', '开始时间', '结束时间', '状态'])
    ws.append(['2026-10-01', '数学', '线代', '09:00', '11:00', 'pending'])
    ws.append(['2026-10-02', '英语', '作文', '14:00', '16:00'])
    ws.append(['', '政治', '漏填日期应被跳过'])          # 无效行
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    data = {'file': (buf, 'plan.xlsx')}
    resp = client.post('/api/tasks/import/excel', data=data, headers=h, content_type='multipart/form-data')
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()['data']['count'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
