import json
from datetime import datetime
from models.task import StudyTask


def parse_json_tasks(file, user_id):
    """解析 JSON 文件中的学习计划"""
    content = file.read().decode('utf-8')
    data = json.loads(content)

    # 支持两种格式：直接数组 或 { "tasks": [...] }
    tasks_data = data if isinstance(data, list) else data.get('tasks', [])

    tasks = []
    for item in tasks_data:
        date_str = item.get('date', '')
        try:
            task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue

        start_time = None
        if item.get('start_time'):
            try:
                start_time = datetime.strptime(item['start_time'], '%H:%M').time()
            except (ValueError, TypeError):
                pass

        end_time = None
        if item.get('end_time'):
            try:
                end_time = datetime.strptime(item['end_time'], '%H:%M').time()
            except (ValueError, TypeError):
                pass

        task = StudyTask(
            user_id=user_id,
            date=task_date,
            subject=item.get('subject', ''),
            content=item.get('content', ''),
            start_time=start_time,
            end_time=end_time,
            status='pending',
            plan_source='json',
        )
        tasks.append(task)

    return tasks