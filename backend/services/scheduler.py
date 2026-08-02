"""艾宾浩斯智能排程引擎（M2）。

核心职责：
- 根据用户上传的「学习清单」（每条 = 一个科目 + 内容）自动铺排复习任务。
- 首次学习日 = 上传日（study_date）；之后按 EBBINGHAUS_INTERVALS 自动生成复习任务。
- 每条学习内容生成：1 个首次学习任务（round 0）+ N 个复习任务（round 1..N）。
- 复习链通过 root_task_id 串联，便于前端展示「某内容还需复习几次」。

设计取舍（与产品计划一致）：
- 忽略原文件里写的具体时间，全部由软件按间隔自动排；date 仅由间隔推算。
- 单人单机（SQLite），数据以 user_id 隔离，不跨用户。
"""
from datetime import date, datetime, timedelta

from app.extensions import db
from models.task import StudyTask
from utils.subject_utils import normalize_subject

# 默认艾宾浩斯遗忘曲线间隔（天）：学完后的第 1/2/4/7/15/30 天复习
EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15, 30]

# 间隔的中文标签（用于前端展示「第几次复习」）
ROUND_LABELS = ['首次学习', '第 1 次复习', '第 2 次复习', '第 3 次复习',
                '第 4 次复习', '第 5 次复习', '第 6 次复习']


def round_label(round_index: int) -> str:
    if round_index <= 0:
        return '首次学习'
    if round_index <= len(ROUND_LABELS) - 1:
        return ROUND_LABELS[round_index]
    return f'第 {round_index} 次复习'


def _parse_date(value):
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


def build_review_chain(user_id, subject, content, study_date, priority=0,
                       intervals=None, root_task_id=None, source=StudyTask.SOURCE_PARSED):
    """为单个学习内容生成「首次学习 + 复习」任务链，返回 StudyTask 列表（未提交）。

    若 root_task_id 为 None，则首任务自带 round=0，并作为后续复习的 root。
    """
    if intervals is None:
        intervals = EBBINGHAUS_INTERVALS
    subject = normalize_subject(subject) or subject
    content = (content or '').strip()
    if not subject or not content:
        return [], None

    is_root_owner = root_task_id is None
    tasks = []

    # round 0：首次学习
    root = StudyTask(
        user_id=user_id,
        date=study_date,
        subject=subject,
        content=content,
        status=StudyTask.STATUS_PENDING,
        plan_source=source,
        priority=priority if priority else 0,
        review_round=0,
        root_task_id=root_task_id,
    )
    tasks.append(root)

    # round 1..N：复习任务
    for i, delta in enumerate(intervals, start=1):
        review_date = study_date + timedelta(days=delta)
        review = StudyTask(
            user_id=user_id,
            date=review_date,
            subject=subject,
            content=f'【复习】{content}',
            status=StudyTask.STATUS_PENDING,
            plan_source=source,
            priority=priority if priority else 0,
            review_round=i,
            # root_task_id 在首任务落库后回填（见 generate_schedule）
            root_task_id=root_task_id,
        )
        tasks.append(review)

    return tasks, root if is_root_owner else None


def generate_schedule(user_id, items, study_date=None, intervals=None):
    """将解析/录入的清单整体排程：每条内容生成一条复习链。

    items: [{subject, content, priority?}, ...]（经用户校正后的清单）
    study_date: 首次学习日（默认今天）
    返回 (created_tasks, skipped_count)
    """
    if study_date is None:
        study_date = date.today()
    elif isinstance(study_date, str):
        study_date = _parse_date(study_date) or date.today()

    created = []
    skipped = 0
    for item in items:
        subject = normalize_subject(item.get('subject'))
        content = (item.get('content') or '').strip()
        if not subject or not content:
            skipped += 1
            continue
        try:
            priority = int(item.get('priority') or 0)
        except (ValueError, TypeError):
            priority = 0
        tasks, root = build_review_chain(
            user_id, subject, content, study_date, priority, intervals
        )
        # 先落库 root 拿到 id，再回填各复习任务的 root_task_id
        db.session.add(root)
        db.session.flush()  # 获得 root.id
        for t in tasks:
            if t is not root:
                t.root_task_id = root.id
        created.extend(tasks)

    if created:
        db.session.add_all([t for t in created if t is not None])
        db.session.commit()
    return created, skipped


def get_review_chain(user_id, root_task_id):
    """返回某内容的完整复习链（含首任务），按复习轮次排序。"""
    tasks = (
        StudyTask.query
        .filter_by(user_id=user_id)
        .filter((StudyTask.id == root_task_id) | (StudyTask.root_task_id == root_task_id))
        .order_by(StudyTask.review_round)
        .all()
    )
    return tasks


def get_upcoming_reviews(user_id, from_date, to_date):
    """区间内（含）所有复习任务（round>=1），用于课表/提醒。"""
    return (
        StudyTask.query
        .filter_by(user_id=user_id)
        .filter(StudyTask.review_round >= 1)
        .filter(StudyTask.date >= from_date)
        .filter(StudyTask.date <= to_date)
        .order_by(StudyTask.date, StudyTask.review_round)
        .all()
    )
