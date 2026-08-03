"""计划确认与版本管理（Phase 3）。

职责：
- 生成 StudyPlan 版本：同名计划 v1/v2…，新版本 active，旧版本 superseded 保留历史
- 将确认后的任务落库（StudyTask.plan_id 关联版本）
- 冲突检测：新任务与「用户已有未完成任务」同日期时间段重叠 → 跳过落库并返回冲突列表，
  由前端提示用户（替换/调整/保留），本层不做覆盖式写入
- 已执行任务保护：已有 StudyRecord 的任务天然不动（只新增，不修改/删除任何已有任务）
"""
from datetime import date

from app.extensions import db
from models.plan import StudyPlan
from models.task import StudyTask
from utils.subject_utils import normalize_subject
from services.plan_service import _parse_time


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    """时间区间重叠判断（time 对象；任一为空则不冲突）。"""
    if not (a_start and a_end and b_start and b_end):
        return False
    return a_start < b_end and b_start < a_end


def detect_conflicts(user_id: int, tasks: list[dict]) -> list[dict]:
    """检测 tasks 与用户已有未完成任务的时间冲突。

    返回 [{'date','subject','content','start_time','end_time','conflicts_with':[...]}]
    """
    by_date: dict[str, list[StudyTask]] = {}
    for t in StudyTask.query.filter_by(user_id=user_id).all():
        if t.status in (StudyTask.STATUS_DONE, StudyTask.STATUS_CANCELLED):
            continue  # 已完成/已取消的不参与冲突
        by_date.setdefault(t.date.isoformat(), []).append(t)

    conflicts = []
    for t in tasks:
        d = t.get('date')
        if not d:
            continue
        dstr = d.isoformat() if isinstance(d, date) else str(d)
        existing = by_date.get(dstr, [])
        hit = [
            x.to_dict()
            for x in existing
            if _overlaps(t.get('start_time'), t.get('end_time'), x.start_time, x.end_time)
        ]
        if hit:
            conflicts.append({
                'date': dstr,
                'subject': t.get('subject') or '',
                'content': t.get('content') or '',
                'start_time': t.get('start_time'),
                'end_time': t.get('end_time'),
                'conflicts_with': hit,
            })
    return conflicts


def confirm_plan_version(user_id: int, plan_name: str, tasks: list[dict], source: str = 'parsed') -> dict:
    """确认计划：创建/更新 StudyPlan 版本并落库任务（冲突任务跳过）。

    tasks 每项: {date, subject, content, start_time, end_time, priority, status}
    返回 {plan_id, plan_name, version, created, skipped:[冲突任务]}
    """
    name = (plan_name or '').strip() or f'{date.today().isoformat()}学习计划'
    version = StudyPlan.next_version(user_id, name)
    plan = StudyPlan(user_id=user_id, name=name, version=version, source=source)
    db.session.add(plan)
    db.session.flush()

    # 已有未完成任务按日期分组（用于冲突检测，避免重复查询）
    by_date: dict[str, list[StudyTask]] = {}
    for t in StudyTask.query.filter_by(user_id=user_id).all():
        if t.status in (StudyTask.STATUS_DONE, StudyTask.STATUS_CANCELLED):
            continue
        by_date.setdefault(t.date.isoformat(), []).append(t)

    created = 0
    skipped: list[dict] = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        d = t.get('date')
        content = (t.get('content') or '').strip()
        if not d or not content:
            continue
        dstr = d.isoformat() if isinstance(d, date) else str(d)
        try:
            d_parsed = d if isinstance(d, date) else date.fromisoformat(str(d)[:10])
        except ValueError:
            continue
        start = _parse_time(t.get('start_time'))
        end = _parse_time(t.get('end_time'))

        # 冲突检测：与已有未完成任务时间重叠 → 跳过（保留历史，不覆盖）
        hit = [
            x for x in by_date.get(dstr, [])
            if _overlaps(start, end, x.start_time, x.end_time)
        ]
        if hit:
            skipped.append({
                'date': dstr,
                'subject': t.get('subject') or '',
                'content': content,
                'start_time': t.get('start_time'),
                'end_time': t.get('end_time'),
                'conflicts_with': [x.to_dict() for x in hit],
            })
            continue

        priority = t.get('priority')
        try:
            priority = int(priority) if priority is not None else 0
        except (TypeError, ValueError):
            priority = 0

        task = StudyTask(
            user_id=user_id,
            plan_id=plan.id,
            date=d_parsed,
            subject=normalize_subject(t.get('subject')) or '其他',
            content=content,
            start_time=start,
            end_time=end,
            status=StudyTask.STATUS_PENDING,
            priority=priority,
            plan_source=source,
        )
        db.session.add(task)
        created += 1

    plan.task_count = created
    StudyPlan.supersede_older(user_id, name, keep_version=version)
    db.session.commit()
    return {
        'plan_id': plan.id,
        'plan_name': name,
        'version': version,
        'created': created,
        'skipped': skipped,
    }
