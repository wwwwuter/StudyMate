"""学习计划业务层。

承载学习任务的 CRUD 与 Excel/JSON/PDF 导入编排，保持路由轻量、可单测。
所有函数以 user_id 做数据隔离，路由层仅负责 HTTP 编解码。
"""
from datetime import datetime, date, time

from app.extensions import db
from models.task import StudyTask
from utils.subject_utils import normalize_subject
from parser import pdf_parser


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
        query = query.filter(StudyTask.content.like(like))

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


# ------------------------- 导入 -------------------------
def _persist_imported(user_id, tasks):
    """将解析器产出的对象落库，校正 user_id 与非法状态。

    去重（幂等）：同一用户下已存在 (date, subject, content, start_time)
    完全相同的任务则跳过，避免重复导入产生重复行。
    """
    existing = {
        (t.date, t.subject, t.content, t.start_time)
        for t in StudyTask.query.filter_by(user_id=user_id).all()
    }
    valid = []
    for t in tasks:
        t.user_id = user_id
        if not StudyTask.is_valid_status(t.status):
            t.status = StudyTask.STATUS_PENDING
        key = (t.date, t.subject, t.content, t.start_time)
        if key in existing:
            continue
        existing.add(key)
        valid.append(t)
    if valid:
        db.session.add_all(valid)
        db.session.commit()
    return valid


def import_from_excel(user_id, file_storage):
    from parser.excel_parser import parse_excel_tasks
    return _persist_imported(user_id, parse_excel_tasks(file_storage, user_id))


def import_from_json(user_id, file_storage):
    from parser.json_parser import parse_json_tasks
    return _persist_imported(user_id, parse_json_tasks(file_storage, user_id))


def import_from_pdf(user_id, file_storage):
    try:
        from parser.pdf_parser import parse_pdf_tasks
    except ImportError:
        raise ValueError('PDF 解析依赖未安装，请先 pip install pdfminer.six')
    return _persist_imported(user_id, parse_pdf_tasks(file_storage, user_id))


def preview_pdf_ai(user_id, file_storage):
    """智能解析预览（U2 人工复核）：提取文本 → AI 识别任务 → 返回结构化列表（不落库）。

    每条含 date（相对/歧义时为 null）、subject、content、start_time、end_time、
    status、confidence、reason、date_note，便于前端展示置信度并允许用户修正后落库。
    AI 层在无密钥且未开启 PDF_AI_MOCK 时会抛出 ValueError，由路由转成明确错误。
    """
    try:
        if pdf_parser.is_scanned_pdf(file_storage):
            raise ValueError(
                '该 PDF 未检测到文本层，疑似扫描件/图片型文档。'
                '真实 OCR（图片转文字）识别需在后续阶段接入 paddleocr 等引擎，'
                '当前暂不支持扫描件解析。'
            )
    except Exception:
        # 扫描检测失败（如依赖缺失）时跳过，直接进入 AI 解析流程
        pass
    text = pdf_parser.extract_pdf_text(file_storage)
    from ai.service import AIService
    return AIService().extract_tasks(text, user_id)


def confirm_pdf_ai(user_id, items):
    """将人工复核后的任务列表落库（校验 + 去重）。

    返回 (persisted_tasks, skipped_count)。相对日期等无效条目在校验阶段被跳过，
    因此前端应在确认前补全 date。
    """
    if not isinstance(items, list):
        raise ValueError('任务列表应为数组')
    valid = []
    skipped = 0
    for item in items:
        try:
            valid.append(_build_task(user_id, item, StudyTask.SOURCE_PDF))
        except ValueError:
            skipped += 1
    persisted = _persist_imported(user_id, valid)
    return persisted, skipped
