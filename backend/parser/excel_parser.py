"""Excel 学习计划解析器（表头感知，鲁棒）。"""
import re
from datetime import datetime, date, time

from models.task import StudyTask
from utils.subject_utils import normalize_subject

# 表头（中/英）-> 字段名
HEADER_MAP = {
    '日期': 'date', 'date': 'date',
    '科目': 'subject', 'subject': 'subject',
    '内容': 'content', 'content': 'content',
    '任务': 'content', '任务内容': 'content',
    '开始时间': 'start_time', 'start': 'start_time', '开始': 'start_time',
    '结束时间': 'end_time', 'end': 'end_time', '结束': 'end_time',
    '状态': 'status', 'status': 'status',
}


def _parse_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        s = v.strip()
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d'):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return None


def _parse_time(v):
    if isinstance(v, datetime):
        return v.time()
    if isinstance(v, time):
        return v
    if isinstance(v, str):
        s = v.strip()
        m = re.match(r'^(\d{1,2}):(\d{2})$', s)
        if m:
            try:
                return time(int(m.group(1)), int(m.group(2)))
            except ValueError:
                return None
    return None


def parse_excel_tasks(file, user_id):
    """解析 .xlsx/.xls 学习计划，返回 StudyTask 列表。

    支持表头映射（日期/科目/内容/开始时间/结束时间/状态），无表头时按位置兜底。
    跳过缺日期或缺内容的行；状态非法时回退为 pending。
    """
    # 延迟导入：openpyxl 属后续阶段解析依赖，避免在应用启动时强制安装
    from openpyxl import load_workbook

    wb = load_workbook(file, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c).strip() if c is not None else '' for c in rows[0]]
    col = {HEADER_MAP.get(h): i for i, h in enumerate(header) if HEADER_MAP.get(h)}

    # 兜底：无任何已知表头时按位置映射（日期, 科目, 内容, 开始, 结束, 状态）
    if 'date' not in col or 'content' not in col:
        col = {'date': 0, 'subject': 1, 'content': 2, 'start_time': 3, 'end_time': 4, 'status': 5}

    tasks = []
    for row in rows[1:]:
        if not row or all(c is None for c in row):
            continue

        task_date = _parse_date(row[col['date']]) if 'date' in col else None
        if not task_date:
            continue

        content = str(row[col['content']]).strip() if row[col['content']] is not None else ''
        if not content:
            continue

        subject = (
            normalize_subject(str(row[col['subject']]).strip())
            if ('subject' in col and row[col['subject']] is not None)
            else ''
        )
        start = (
            _parse_time(row[col['start_time']])
            if ('start_time' in col and row[col['start_time']] is not None)
            else None
        )
        end = (
            _parse_time(row[col['end_time']])
            if ('end_time' in col and row[col['end_time']] is not None)
            else None
        )
        status_raw = (
            str(row[col['status']]).strip()
            if ('status' in col and row[col['status']] is not None)
            else StudyTask.STATUS_PENDING
        )
        status = status_raw if StudyTask.is_valid_status(status_raw) else StudyTask.STATUS_PENDING

        tasks.append(StudyTask(
            user_id=user_id,
            date=task_date,
            subject=subject,
            content=content,
            start_time=start,
            end_time=end,
            status=status,
            plan_source=StudyTask.SOURCE_EXCEL,
        ))
    return tasks
