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


# ---- 导入去重（幂等）----
def test_import_json_dedup(client):
    h = _login(client)
    payload = [{'date': '2026-09-05', 'subject': '数学', 'content': '真题', 'start_time': '09:00', 'end_time': '11:00'}]

    def _post():
        # 每次请求都用全新的流：Werkzeug 测试客户端会在请求后关闭文件对象
        buf = io.BytesIO(json.dumps(payload).encode('utf-8'))
        return client.post('/api/tasks/import/json', data={'file': (buf, 'plan.json')},
                           headers=h, content_type='multipart/form-data')

    r1 = _post()
    assert r1.get_json()['data']['count'] == 1
    # 重复导入同一份：应被去重，新增 0 条
    r2 = _post()
    assert r2.get_json()['data']['count'] == 0


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


# ---- PDF 解析（mock extract_text，避免依赖真实 PDF 文件）----
def test_parse_pdf_normalize_and_fallback(monkeypatch):
    """PDF 解析：科目归一化 + 无时间段行应保留（时间置空），不整行丢弃。"""
    # 模拟 pdfminer 提取出的文本
    fake_text = (
        "2026-09-01 高数 极限专题训练 08:00-10:00\n"
        "2026-09-02 英语 单词背诵\n"          # 无时间段，应保留
        "这行没有日期应被忽略\n"
    )

    import parser.pdf_parser as pp
    import pdfminer.high_level as hl

    def fake_extract(file, **kwargs):
        return fake_text

    # 解析器在调用时才 `from pdfminer.high_level import extract_text`，
    # 故直接 patch 真实模块的 extract_text 即可。
    monkeypatch.setattr(hl, 'extract_text', fake_extract)

    tasks = pp.parse_pdf_tasks(None, user_id=1)
    assert len(tasks) == 2
    # 归一化：高数 -> 数学
    assert tasks[0].subject == '数学'
    assert tasks[0].start_time is not None and tasks[0].end_time is not None
    # 无时间段行：科目英语(归一化) + 内容，时间置空
    assert tasks[1].subject == '英语'
    assert tasks[1].start_time is None and tasks[1].end_time is None
    assert tasks[1].content == '单词背诵'


# ---- Excel .xls 解析（mock xlrd.open_workbook，验证旧格式分支 + 日期转换）----
def test_parse_excel_xls_branch(monkeypatch):
    from datetime import date
    """扩展名为 .xls 时走 xlrd 分支，且日期单元格应转为 date。"""
    import io
    import parser.excel_parser as ep

    # 极简 xlrd stub
    class _Cell:
        def __init__(self, ctype, value):
            self.ctype = ctype
            self.value = value

    class _Sheet:
        def __init__(self, cells):
            self._cells = cells
            self.nrows = len(cells)
            self.ncols = 3

        def cell(self, r, c):
            return self._cells[r][c]

    class _Book:
        datemode = 0

        def __init__(self, cells):
            self._sheet = _Sheet(cells)

        def sheet_by_index(self, _):
            return self._sheet

    # 行：表头 + 1 条数据（日期用 xlrd 日期序列值 40000 ≈ 2009-07-06，仅验证能转成 date 类型）
    xlrd_date = 40000
    cells = [
        [_Cell(0, '日期'), _Cell(0, '科目'), _Cell(0, '内容')],
        [_Cell(3, xlrd_date), _Cell(1, '数学'), _Cell(1, '真题')],
    ]

    class _xlrd:
        XL_CELL_DATE = 3
        XL_CELL_EMPTY = 0

        @staticmethod
        def open_workbook(file_contents=None):
            return _Book(cells)

        class xldate:
            @staticmethod
            def xldate_as_datetime(v, _mode):
                from datetime import date, datetime, timedelta
                return datetime(1899, 12, 30) + timedelta(days=v)

    monkeypatch.setattr('xlrd.open_workbook', _xlrd.open_workbook)

    class FakeXls:
        filename = 'plan.xls'

        def read(self):
            return b'dummy'

    tasks = ep.parse_excel_tasks(FakeXls(), user_id=1)
    assert len(tasks) == 1
    assert tasks[0].subject == '数学'
    assert isinstance(tasks[0].date, date)
    assert tasks[0].content == '真题'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
