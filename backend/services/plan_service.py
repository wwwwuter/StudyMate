"""学习计划业务层。

只承载学习任务的 CRUD 与字段校验，保持路由轻量、可单测。
计划文件的导入统一走 `/api/plans/parse` + `/api/plans/confirm`（AI 解析，
使用用户在「设置」页配置的 Key），这里不提供任何本地导入 / 降级入口。
所有函数以 user_id 做数据隔离，路由层仅负责 HTTP 编解码。
"""
from datetime import datetime, date, time

from app.extensions import db
from models.task import StudyTask
from utils.subject_utils import normalize_subject


# ------------------------- 解析辅助 -------------------------
def _parse_date(value):
    """支持 date / datetime / 字符串(YYYY-MM-DD 或 YYYY/MM/DD)。"""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d'):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
    return None


def _parse_time(value):
    """支持 time / datetime / 字符串(HH:MM)。空值/非法值返回 None。"""
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        s = value.strip()
        parts = s.split(':')
        if len(parts) == 2:
            try:
                return time(int(parts[0]), int(parts[1]))
            except ValueError:
                return None
    return None


def _build_task(user_id, data, source):
    """根据字典构造一个 StudyTask，含校验；失败抛 ValueError。"""
    if not isinstance(data, dict):
        raise ValueError('任务数据应为对象')

    task_date = _parse_date(data.get('date'))
    if task_date is None:
        raise ValueError("缺少或格式错误的 date（应为 YYYY-MM-DD）")

    subject = normalize_subject(data.get('subject'))
    if not subject:
        raise ValueError('缺少 subject（科目）')

    content = (data.get('content') or '').strip()
    if not content:
        raise ValueError('缺少 content（内容）')

    status = data.get('status', StudyTask.STATUS_PENDING)
    if not StudyTask.is_valid_status(status):
        raise ValueError(f'非法 status: {status}')

    start_time = _parse_time(data.get('start_time'))
    end_time = _parse_time(data.get('end_time'))
    if start_time and end_time and start_time > end_time:
        raise ValueError('结束时间不能早于开始时间')

    task = StudyTask(
        user_id=user_id,
        date=task_date,
        subject=subject,
        content=content,
        start_time=start_time,
        end_time=end_time,
        status=status,
        plan_source=data.get('plan_source', source),
    )
    # U5 字段扩展（可选）
    if data.get('priority') is not None:
        try:
            task.priority = int(data['priority'])
        except (ValueError, TypeError):
            pass
    if data.get('estimated_minutes') is not None:
        try:
            task.estimated_minutes = int(data['estimated_minutes'])
        except (ValueError, TypeError):
            pass
    if data.get('tags') is not None:
        tags_val = data['tags']
        if isinstance(tags_val, list):
            tags_val = ','.join(str(t) for t in tags_val)
        task.tags = tags_val
    return task


# ------------------------- CRUD -------------------------
def create_task(user_id, data):
    task = _build_task(user_id, data, StudyTask.SOURCE_MANUAL)
    db.session.add(task)
    db.session.commit()
    return task


def bulk_create(user_id, items):
    if not isinstance(items, list) or not items:
        raise ValueError('任务列表为空')
    tasks = []
    for i, item in enumerate(items):
        try:
            tasks.append(_build_task(user_id, item, StudyTask.SOURCE_MANUAL))
        except ValueError as e:
            raise ValueError(f'第 {i + 1} 条: {e}')
    db.session.add_all(tasks)
    db.session.commit()
    return tasks


def get_task(user_id, task_id):
    return StudyTask.query.filter_by(id=task_id, user_id=user_id).first()


def list_tasks(user_id, filters=None):
    filters = filters or {}
    query = StudyTask.query.filter_by(user_id=user_id)

    if filters.get('date'):
        d = _parse_date(filters['date'])
        if d:
            query = query.filter_by(date=d)
    if filters.get('start_date'):
        d = _parse_date(filters['start_date'])
        if d:
            query = query.filter(StudyTask.date >= d)
    if filters.get('end_date'):
        d = _parse_date(filters['end_date'])
        if d:
            query = query.filter(StudyTask.date <= d)
    if filters.get('subject'):
        query = query.filter_by(subject=normalize_subject(filters['subject']))
    if filters.get('status'):
        query = query.filter_by(status=filters['status'])
    if filters.get('keyword'):
        like = f"%{filters['keyword']}%"
        query = query.filter(
            db.or_(
                StudyTask.subject.ilike(like),
                StudyTask.content.ilike(like),
            )
        )

    query = query.order_by(StudyTask.date, StudyTask.start_time)

    # 分页：同时提供 page 与 page_size 时返回 (items, total)
    page = filters.get('page')
    page_size = filters.get('page_size')
    if isinstance(page, int) and isinstance(page_size, int) and page >= 1 and page_size >= 1:
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    items = query.all()
    return items, len(items)

def update_task(user_id, task_id, data):
    task = get_task(user_id, task_id)
    if task is None:
        return None

    if 'date' in data and data['date'] is not None:
        d = _parse_date(data['date'])
        if d is None:
            raise ValueError('date 格式错误（应为 YYYY-MM-DD）')
        task.date = d
    if 'subject' in data:
        s = normalize_subject(data['subject'])
        if not s:
            raise ValueError('subject 不能为空')
        task.subject = s
    if 'content' in data:
        c = (data['content'] or '').strip()
        if not c:
            raise ValueError('content 不能为空')
        task.content = c
    if 'start_time' in data:
        task.start_time = _parse_time(data['start_time'])
    if 'end_time' in data:
        task.end_time = _parse_time(data['end_time'])
    if task.start_time and task.end_time and task.start_time > task.end_time:
        raise ValueError('结束时间不能早于开始时间')
    if 'status' in data:
        if not StudyTask.is_valid_status(data['status']):
            raise ValueError(f'非法 status: {data["status"]}')
        task.status = data['status']
    if 'priority' in data and data['priority'] is not None:
        try:
            task.priority = int(data['priority'])
        except (ValueError, TypeError):
            raise ValueError('priority 应为整数')
    if 'estimated_minutes' in data and data['estimated_minutes'] is not None:
        try:
            task.estimated_minutes = int(data['estimated_minutes'])
        except (ValueError, TypeError):
            raise ValueError('estimated_minutes 应为整数')
    if 'tags' in data:
        tags_val = data['tags']
        if isinstance(tags_val, list):
            tags_val = ','.join(str(t) for t in tags_val)
        task.tags = tags_val

    db.session.commit()
    return task


def delete_task(user_id, task_id):
    task = get_task(user_id, task_id)
    if task is None:
        return False
    db.session.delete(task)
    db.session.commit()
    return True


def bulk_delete(user_id, task_ids):
    """批量删除属于该用户的任务，返回实际删除条数（越权 id 会被忽略）。"""
    if not task_ids:
        return 0
    ids = [int(i) for i in task_ids if str(i).isdigit()]
    if not ids:
        return 0
    tasks = StudyTask.query.filter(
        StudyTask.user_id == user_id,
        StudyTask.id.in_(ids),
    ).all()
    count = len(tasks)
    for t in tasks:
        db.session.delete(t)
    db.session.commit()
    return count


def _apply_criteria(query, criteria):
    """根据条件构建查询，返回 (query, has_criterion)。"""
    has_criterion = False

    subject = normalize_subject(criteria.get('subject'))
    if subject:
        query = query.filter_by(subject=subject)
        has_criterion = True

    start_date = _parse_date(criteria.get('start_date'))
    end_date = _parse_date(criteria.get('end_date'))
    if start_date:
        query = query.filter(StudyTask.date >= start_date)
        has_criterion = True
    if end_date:
        query = query.filter(StudyTask.date <= end_date)
        has_criterion = True

    start_time = _parse_time(criteria.get('start_time'))
    end_time = _parse_time(criteria.get('end_time'))
    if start_time and end_time:
        # 时间段重叠：任务的起止时间与给定区间有交集
        query = query.filter(
            StudyTask.start_time.isnot(None),
            StudyTask.end_time.isnot(None),
            StudyTask.start_time < end_time,
            StudyTask.end_time > start_time,
        )
        has_criterion = True
    elif start_time:
        query = query.filter(StudyTask.start_time == start_time)
        has_criterion = True
    elif end_time:
        query = query.filter(StudyTask.end_time == end_time)
        has_criterion = True

    status = criteria.get('status')
    if status:
        query = query.filter_by(status=status)
        has_criterion = True

    source = criteria.get('plan_source')
    if source:
        if source == 'uploaded':
            query = query.filter(StudyTask.plan_source != StudyTask.SOURCE_MANUAL)
        else:
            query = query.filter_by(plan_source=source)
        has_criterion = True

    return query, has_criterion


def count_by_criteria(user_id, criteria):
    """统计符合删除条件的任务数量（不删除）。"""
    query = StudyTask.query.filter_by(user_id=user_id)
    query, has_criterion = _apply_criteria(query, criteria)
    if not has_criterion:
        raise ValueError('请至少指定一个删除条件')
    return query.count()


def delete_by_criteria(user_id, criteria):
    """按条件批量删除任务，返回删除条数。"""
    query = StudyTask.query.filter_by(user_id=user_id)
    query, has_criterion = _apply_criteria(query, criteria)
    if not has_criterion:
        raise ValueError('请至少指定一个删除条件')
    tasks = query.all()
    count = len(tasks)
    for t in tasks:
        db.session.delete(t)
    db.session.commit()
    return count
