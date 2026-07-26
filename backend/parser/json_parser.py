"""JSON 学习计划解析器（支持数组或 { "tasks": [...] } 两种形态）。"""
import json
from datetime import datetime, date, time

from models.task import StudyTask
from utils.subject_utils import normalize_subject


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
        parts = v.strip().split(':')
        if len(parts) == 2:
            try:
                return time(int(parts[0]), int(parts[1]))
            except ValueError:
                return None
    return None


def parse_json_tasks(file, user_id):
    """解析 JSON 学习计划，返回 StudyTask 列表。

    支持两种顶层结构：数组，或 {"tasks": [...]}。跳过缺日期或缺内容的项；
    状态非法时回退为 pending；科目自动归一化。
    """
    content = file.read().decode('utf-8')
    data = json.loads(content)

    items = data if isinstance(data, list) else data.get('tasks', [])
    if not isinstance(items, list):
        return []

    tasks = []
    for item in items:
        if not isinstance(item, dict):
            continue

        task_date = _parse_date(item.get('date'))
        if not task_date:
            continue

        content = (item.get('content') or '').strip()
        if not content:
            continue

        subject = normalize_subject(item.get('subject', ''))
        start = _parse_time(item.get('start_time'))
        end = _parse_time(item.get('end_time'))
        status_raw = item.get('status', StudyTask.STATUS_PENDING)
        status = status_raw if StudyTask.is_valid_status(status_raw) else StudyTask.STATUS_PENDING

        tasks.append(StudyTask(
            user_id=user_id,
            date=task_date,
            subject=subject,
            content=content,
            start_time=start,
            end_time=end,
            status=status,
            plan_source=StudyTask.SOURCE_JSON,
        ))
    return tasks
