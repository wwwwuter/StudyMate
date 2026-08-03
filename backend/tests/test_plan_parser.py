"""Phase 2 AI 计划解析模块升级测试。

覆盖：
1. Excel(.xlsx) 表头映射抽取（中英文表头、无表头兜底）
2. HTTP 上传 Excel → /api/plans/parse 返回结构
3. HTTP 上传 JSON 计划文件（{plan_name, tasks}）→ 直接结构化
4. _parse_tasks_json 提取 plan_name / 保留 priority
5. _normalize_plan 优先级归一化（high→1 / 数字透传）
"""
import io
import json

from ai.service import _parse_tasks_json
from routes.plan import _normalize_plan


def _mk_xlsx(headers: list[str] | None, rows: list[list]):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    if headers:
        ws.append(headers)
    for r in rows:
        ws.append(r)
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def test_excel_rows_with_header(client, auth_headers):
    from parser.excel_parser import extract_excel_rows
    bio = _mk_xlsx(
        ['日期', '科目', '内容', '开始时间', '结束时间', '优先级'],
        [['2026-08-05', '数学', '高数强化-不定积分', '08:30', '11:30', 'high'],
         ['2026-08-05', '408', '计组-指令系统', '14:00', '17:30', 'medium']],
    )
    bio.filename = 'plan.xlsx'
    rows = extract_excel_rows(bio)
    assert len(rows) == 2
    assert rows[0]['date'] == '2026-08-05'
    assert rows[0]['subject'] == '数学'
    assert rows[0]['start_time'] == '08:30'
    assert rows[0]['priority'] == 'high'


def test_excel_parse_api(client, auth_headers):
    """HTTP 上传 xlsx → 结构化 plans（不走 AI，无需 Key）。"""
    bio = _mk_xlsx(
        ['date', 'subject', 'content', 'start_time', 'end_time', 'priority'],
        [['2026-08-06', '英语', '阅读精翻', '19:00', '20:30', 'high']],
    )
    bio.filename = 'plan.xlsx'
    r = client.post('/api/plans/parse', headers=auth_headers,
                    data={'file': (bio, 'plan.xlsx')}, content_type='multipart/form-data')
    assert r.status_code == 200
    data = r.get_json()['data']
    assert len(data['plans']) == 1
    p = data['plans'][0]
    assert p['date'] == '2026-08-06'
    assert p['priority'] == 1  # high → 1
    assert p['needs_review'] is False


def test_json_plan_parse_api(client, auth_headers):
    """HTTP 上传 JSON 计划文件（结构化，不走 AI）。"""
    payload = {
        'plan_name': '暑假考研计划',
        'tasks': [
            {'date': '2026-08-05', 'subject': '数学', 'content': '高数强化',
             'start_time': '08:30', 'end_time': '11:30', 'priority': 'high'},
            {'date': '2026-08-05', 'subject': '英语', 'content': '单词',
             'start_time': '19:00', 'end_time': '20:00', 'priority': 'low'},
        ],
    }
    bio = io.BytesIO(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
    bio.filename = 'plan.json'
    r = client.post('/api/plans/parse', headers=auth_headers,
                    data={'file': (bio, 'plan.json')}, content_type='multipart/form-data')
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['plan_name'] == '暑假考研计划'
    assert len(data['plans']) == 2
    assert data['plans'][0]['priority'] == 1


def test_parse_tasks_json_plan_name_priority():
    raw = json.dumps({
        'plan_name': '数学强化计划',
        'daily_tasks': [
            {'date': '2026-08-07', 'subject': '数学', 'content': '不定积分',
             'start_time': '08:30', 'end_time': '11:30', 'priority': 'high'},
            {'date': '2026-08-07', 'subject': '英语', 'content': '阅读',
             'start_time': '19:00', 'end_time': '20:00'},
        ],
    }, ensure_ascii=False)
    out = _parse_tasks_json(raw)
    assert out['plan_name'] == '数学强化计划'
    assert out['daily_tasks'][0]['priority'] == 'high'
    assert out['daily_tasks'][1]['priority'] is None


def test_normalize_plan_priority_map():
    p = _normalize_plan({'date': '2026-08-08', 'subject': '数学', 'content': 'x',
                         'start_time': '08:30', 'end_time': '10:00', 'priority': 'high'})
    assert p['priority'] == 1
    p2 = _normalize_plan({'date': '2026-08-08', 'subject': '数学', 'content': 'x',
                          'start_time': '08:30', 'end_time': '10:00', 'priority': 2})
    assert p2['priority'] == 2
