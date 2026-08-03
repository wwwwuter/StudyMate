"""计划解析与计时路由（新核心：上传计划 -> AI 识别排期 -> 到点提醒 + 自动计时）。

- POST /api/plans/parse    ：文本 / PDF / Word / 图片(截图) -> 时间槽计划列表（不落库）
- POST /api/plans/confirm  ：将复核后的计划列表落库为 study_tasks（自动生成提醒）
- POST /api/timer/start    ：针对某计划（或手动主题）开启一次计时
- POST /api/timer/stop     ：结束当前/指定计时
- GET  /api/timer/current  ：返回当前正在运行的计时会话
"""
import base64
import os
from datetime import datetime, date, timedelta

from flask import Blueprint, request, jsonify

from utils.local_auth import login_required
from app.extensions import db
from models.task import StudyTask
from models.timer_session import TimerSession
from models.record import StudyRecord
from models.pomodoro_cycle import PomodoroCycle
from utils.subject_utils import normalize_subject
from services.plan_service import _parse_date, _parse_time
from services.reminder_service import sweep_due_reminders

plan_bp = Blueprint('plan', __name__)


# ------------------------- 计划解析 -------------------------
def _is_ai_auth_error(exc: Exception) -> bool:
    """判断异常是否为 AI 认证 / Key 无效错误（用于给出精准提示）。"""
    msg = str(exc).lower()
    return any(k in msg for k in ('401', 'unauthorized', 'authentication', '认证失败'))



@plan_bp.route('/parse', methods=['POST'])
@login_required
def parse_plan(current_user):
    """识别上传的计划（文本 / PDF / Word / 图片），返回带时间槽的计划列表。

    支持字段：
    - form ``text``：直接粘贴的计划文本
    - form ``file``：文件（.txt/.md/.pdf/.docx/.png/.jpg/.jpeg）
    返回 {code, data:{plans:[{date,subject,content,start_time,end_time,needs_review}]}}
    """
    text = (request.form.get('text') or '').strip()
    file_storage = request.files.get('file') if 'file' in request.files else None

    if not text and (not file_storage or not file_storage.filename):
        return jsonify({'code': 400, 'message': '请提供 text 或上传文件'}), 400

    plans: list[dict] = []
    plan_name: str | None = None

    try:
        from ai.service import AIService
        svc = AIService()

        if file_storage and file_storage.filename:
            filename = getattr(file_storage, 'filename', '') or ''
            ext = os.path.splitext(filename)[1].lower()

            if ext in ('.txt', '.md'):
                raw = file_storage.read().decode('utf-8', errors='ignore')
                parsed = svc.extract_tasks(raw, current_user.id)
                plans = _daily_tasks(parsed)
                plan_name = parsed.get('plan_name') if isinstance(parsed, dict) else None

            elif ext == '.docx':
                parsed = svc.extract_tasks_from_docx(file_storage, current_user.id)
                plans = _daily_tasks(parsed)
                plan_name = parsed.get('plan_name') if isinstance(parsed, dict) else None

            elif ext == '.pdf':
                from parser.pdf_parser import extract_pdf_text
                pdf_text = extract_pdf_text(file_storage)
                parsed = svc.extract_tasks(pdf_text, current_user.id)
                plans = _daily_tasks(parsed)
                plan_name = parsed.get('plan_name') if isinstance(parsed, dict) else None

            elif ext in ('.xlsx', '.xls'):
                # Excel 为结构化数据：表头映射直接抽取（非正则），无需 AI
                from parser.excel_parser import extract_excel_rows, extract_excel_plan_name
                plans = extract_excel_rows(file_storage)
                plan_name = extract_excel_plan_name(file_storage)

            elif ext == '.json':
                # JSON 计划文件已结构化：{plan_name?, tasks:[...]} 或数组
                raw = file_storage.read().decode('utf-8', errors='ignore')
                plans, plan_name = _parse_json_plan(raw)

            elif ext in ('.png', '.jpg', '.jpeg'):
                data = file_storage.read()
                b64 = base64.b64encode(data).decode('ascii')
                plans = svc.vision_parse_plan(b64, current_user.id)

            else:
                return jsonify({'code': 400, 'message': '不支持的文件类型，请用 txt/md/pdf/docx/xlsx/json/png/jpg'}), 400
        else:
            parsed = svc.extract_tasks(text, current_user.id)
            plans = _daily_tasks(parsed)
            plan_name = parsed.get('plan_name') if isinstance(parsed, dict) else None

    except ValueError as e:
        # 未配置 Key / 图片识别失败等，均为用户可修复的输入类问题
        return jsonify({'code': 400, 'message': str(e)}), 400
    except Exception as e:
        if _is_ai_auth_error(e):
            return jsonify({
                'code': 400,
                'message': 'AI 认证失败：你在「设置」页配置的 API Key 无效或已过期，请更换后重试。',
            }), 400
        return jsonify({'code': 500, 'message': f'AI 解析失败：{e}'}), 500

    plans = [_normalize_plan(p) for p in plans]

    return jsonify({
        'code': 200,
        'message': f'AI 识别到 {len(plans)} 条计划',
        'data': {'plans': plans, 'plan_name': plan_name},
    })


def _daily_tasks(parsed) -> list[dict]:
    """统一取出 AI 解析结果中的 daily_tasks。"""
    if isinstance(parsed, dict):
        return parsed.get('daily_tasks', []) or []
    return parsed or []


def _parse_json_plan(raw: str) -> tuple[list, str | None]:
    """解析 JSON 计划文件：{plan_name?, tasks:[...]} 或直接数组。返回 (plans, plan_name)。"""
    import json as _json

    try:
        data = _json.loads(raw)
    except Exception:
        return [], None

    plan_name = data.get('plan_name') if isinstance(data, dict) else None
    tasks = data.get('tasks') if isinstance(data, dict) else data
    if not isinstance(tasks, list):
        return [], plan_name

    out = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        out.append({
            'date': t.get('date'),
            'subject': t.get('subject'),
            'content': t.get('content'),
            'start_time': t.get('start_time'),
            'end_time': t.get('end_time'),
            'priority': t.get('priority'),
            'status': t.get('status', 'pending'),
        })
    return out, plan_name


def _normalize_plan(p: dict) -> dict:
    if not isinstance(p, dict):
        return {'date': None, 'subject': '', 'content': '', 'start_time': None, 'end_time': None,
                'priority': 0, 'needs_review': True}
    date_val = _parse_date(p.get('date'))
    subject = normalize_subject(p.get('subject')) or ''
    content = (p.get('content') or '').strip()
    start = _parse_time(p.get('start_time'))
    end = _parse_time(p.get('end_time'))
    needs_review = (date_val is None) or (not subject) or (not content) or (start is None)
    # 优先级归一化：high→1(高) / medium·low→0(普通) / 数字按 0普通·1高·2紧急
    prio_map = {'high': 1, 'urgent': 2, '紧急': 2, 'medium': 0, 'low': 0, 'normal': 0, '普通': 0, '低': 0}
    pv = p.get('priority')
    if isinstance(pv, str):
        priority = prio_map.get(pv.strip().lower(), 0)
    elif isinstance(pv, (int, float)):
        priority = int(pv)
    else:
        priority = 0
    return {
        'date': date_val.strftime('%Y-%m-%d') if date_val else None,
        'subject': subject,
        'content': content,
        'start_time': start.strftime('%H:%M') if start else None,
        'end_time': end.strftime('%H:%M') if end else None,
        'priority': priority,
        'needs_review': needs_review,
    }


@plan_bp.route('/confirm', methods=['POST'])
@login_required
def confirm_plan(current_user):
    """将复核后的计划确认落库（生成 StudyPlan 版本，冲突任务跳过并返回提示）。

    body: {plan_name?, tasks:[{date,subject,content,start_time,end_time,priority}]}
    兼容旧格式：直接传任务数组。
    返回 {plan_id, plan_name, version, created, skipped:[冲突任务]}
    """
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        plan_name = data.get('plan_name')
        items = data.get('tasks')
    else:
        plan_name = None
        items = data
    if not isinstance(items, list) or not items:
        return jsonify({'code': 400, 'message': 'body 应为 {plan_name?, tasks:[...]}'}), 400

    try:
        from services.plan_manager import confirm_plan_version
        result = confirm_plan_version(current_user.id, plan_name or '', items, source='parsed')
    except Exception as e:
        return jsonify({'code': 500, 'message': f'保存失败: {e}'}), 500

    # 立即扫描生成提醒（无需等待调度周期）
    try:
        sweep_due_reminders()
    except Exception:
        pass

    message = f'已保存 {result["created"]} 条计划'
    if result['skipped']:
        message += f'，跳过 {len(result["skipped"])} 条时间冲突'
    return jsonify({'code': 200, 'message': message, 'data': result})


# ------------------------- 计时 -------------------------
def _pomodoro_focus_total(session_id: int) -> int:
    """番茄钟各轮「专注时长」之和（休息时长严禁计入）。"""
    rows = PomodoroCycle.query.filter_by(timer_session_id=session_id).all()
    return sum((r.focus_duration or 0) for r in rows)


def _effective_duration(session: TimerSession) -> int:
    """本次计时的有效学习时长（秒）。

    - 番茄钟：各轮专注时长之和（不含休息）。
    - 其它模式：实际起止时间差。
    """
    if session.mode == TimerSession.MODE_POMODORO:
        focus = _pomodoro_focus_total(session.id)
        if focus:
            return focus
        # 前端未上报轮次时回退到整段时长（至少不会把休息单列统计）
        if session.started_at and session.ended_at:
            return int((session.ended_at - session.started_at).total_seconds())
        return 0
    if session.started_at and session.ended_at:
        return int((session.ended_at - session.started_at).total_seconds())
    return session.duration_seconds or 0


def _sync_session_to_record(session: TimerSession):
    """计时结束（done）时同步写入 StudyRecord，统一统计数据源。

    仅在有有效时长时写入，避免重复（仅由下面两个会触发状态变更的入口调用）。
    record_type 严格按 TimerSession.mode 映射；番茄钟只统计专注段。
    extra_duration = 计划时间段结束后的额外学习时长（超时继续），单独统计不计入计划内。
    """
    if session.status != TimerSession.STATUS_DONE:
        return
    duration = _effective_duration(session)
    if not duration:
        return

    record_type = {
        TimerSession.MODE_POMODORO: StudyRecord.MODE_POMODORO,
        TimerSession.MODE_TASK: StudyRecord.MODE_TASK,
        TimerSession.MODE_COUNTUP: StudyRecord.MODE_COUNTUP,
        TimerSession.MODE_COUNTDOWN: StudyRecord.MODE_COUNTDOWN,
    }.get(session.mode, StudyRecord.MODE_COUNTUP)

    subject = None
    if session.task_id:
        t = StudyTask.query.get(session.task_id)
        if t:
            subject = t.subject
    extra = 0
    if session.plan_end_time and session.ended_at and session.ended_at > session.plan_end_time:
        extra = int((session.ended_at - session.plan_end_time).total_seconds())
    db.session.add(StudyRecord(
        user_id=session.user_id,
        task_id=session.task_id,
        start_time=session.started_at,
        end_time=session.ended_at,
        duration=duration,
        record_type=record_type,
        subject=subject,
        extra_duration=extra,
        note=session.note,
    ))


def _close_running(user_id):
    """结束该用户当前正在运行的计时（计算时长）。"""
    running = TimerSession.query.filter_by(
        user_id=user_id, status=TimerSession.STATUS_RUNNING
    ).first()
    if running is not None:
        running.ended_at = datetime.utcnow()
        running.status = TimerSession.STATUS_DONE
        running.duration_seconds = _effective_duration(running)
        _sync_session_to_record(running)
        db.session.commit()
    return running


def _combine_utc(d, t):
    """本地时间（StudyTask.date + start/end_time，按中国时区 UTC+8）转 UTC naive datetime。

    供 task 模式填充 TimerSession.plan_start_time/plan_end_time，
    前端拿到带 Z 的 UTC ISO 后由 Date 解析回本地显示，与计划时间一致。
    """
    return datetime.combine(d, t) - timedelta(hours=8)


@plan_bp.route('/timer/start', methods=['POST'])
@login_required
def timer_start(current_user):
    """开启一次计时。

    body: {task_id?, mode?, note?, duration?}
    - mode 取值：pomodoro / task / countup / countdown（默认 countup）。
    - task 模式必须带 task_id，且任务归属当前用户。
    - duration 为前端预设的计划专注时长（秒），仅用于展示，不强制写库。
    返回新建的 TimerSession（含 id / mode）。
    """
    data = request.get_json(silent=True) or {}
    raw_task_id = data.get('task_id')
    note = (data.get('note') or '').strip()
    mode = (data.get('mode') or TimerSession.DEFAULT_MODE)

    if mode not in TimerSession.VALID_MODES:
        return jsonify({'code': 400, 'message': f'不支持的计时模式：{mode}'}), 400

    task_id = None
    if raw_task_id:
        try:
            task_id = int(raw_task_id)
        except (TypeError, ValueError):
            return jsonify({'code': 400, 'message': 'task_id 必须为整数'}), 400
        task = StudyTask.query.get(task_id)
        if not task or task.user_id != current_user.id:
            return jsonify({'code': 400, 'message': '任务不存在或无权限'}), 400

    _close_running(current_user.id)

    session = TimerSession(
        user_id=current_user.id,
        task_id=task_id,
        mode=mode,
        started_at=datetime.utcnow(),
        status=TimerSession.STATUS_RUNNING,
        note=note or None,
    )
    # task 模式：从 StudyTask 计算计划时间段（本地 → UTC），供前端「计划倒计时」显示
    if mode == TimerSession.MODE_TASK and task_id:
        t = StudyTask.query.get(task_id)
        if t and t.start_time and t.end_time:
            session.plan_start_time = _combine_utc(t.date, t.start_time)
            session.plan_end_time = _combine_utc(t.date, t.end_time)
    db.session.add(session)
    db.session.commit()
    return jsonify({'code': 200, 'message': '计时开始', 'data': _session_dict(session)})


@plan_bp.route('/timer/cycle', methods=['POST'])
@login_required
def timer_cycle(current_user):
    """记录番茄钟一轮（专注 + 休息）。仅番茄钟会话可调用。

    body: {session_id, cycle_number?, focus_duration, break_duration?}
    - 学习时长统计只累加 focus_duration，break_duration 仅作明细留存。
    """
    data = request.get_json(silent=True) or {}
    sid = data.get('session_id')
    focus_duration = data.get('focus_duration')
    break_duration = data.get('break_duration', 0)
    cycle_number = data.get('cycle_number', 1)
    if not sid or focus_duration is None:
        return jsonify({'code': 400, 'message': 'session_id 与 focus_duration 必填'}), 400
    session = TimerSession.query.filter_by(id=sid, user_id=current_user.id).first()
    if session is None:
        return jsonify({'code': 404, 'message': '计时会话不存在'}), 404
    if session.mode != TimerSession.MODE_POMODORO:
        return jsonify({'code': 400, 'message': '仅番茄钟模式可记录轮次'}), 400
    try:
        focus_duration = int(focus_duration)
        break_duration = int(break_duration or 0)
        cycle_number = int(cycle_number)
    except (TypeError, ValueError):
        return jsonify({'code': 400, 'message': '参数必须为整数'}), 400
    db.session.add(PomodoroCycle(
        timer_session_id=session.id,
        cycle_number=cycle_number,
        focus_duration=focus_duration,
        break_duration=break_duration,
    ))
    db.session.commit()
    return jsonify({
        'code': 200,
        'message': '轮次已记录',
        'data': {'cycle_number': cycle_number, 'focus_duration': focus_duration},
    })


@plan_bp.route('/timer/stop', methods=['POST'])
@login_required
def timer_stop(current_user):
    """结束计时。body: {session_id?}；缺省则结束当前运行中的会话。"""
    data = request.get_json(silent=True) or {}
    sid = data.get('session_id')
    if sid:
        session = TimerSession.query.filter_by(id=sid, user_id=current_user.id).first()
    else:
        session = TimerSession.query.filter_by(
            user_id=current_user.id, status=TimerSession.STATUS_RUNNING
        ).first()
    if session is None:
        return jsonify({'code': 404, 'message': '没有正在运行的计时'}), 404
    if session.status == TimerSession.STATUS_RUNNING:
        session.ended_at = datetime.utcnow()
        session.status = TimerSession.STATUS_DONE
        session.duration_seconds = _effective_duration(session)
        _sync_session_to_record(session)
        db.session.commit()
    return jsonify({'code': 200, 'message': '计时结束', 'data': _session_dict(session)})


@plan_bp.route('/timer/current', methods=['GET'])
@login_required
def timer_current(current_user):
    """返回当前运行中的计时会话（含关联计划信息），无则返回 null。"""
    session = TimerSession.query.filter_by(
        user_id=current_user.id, status=TimerSession.STATUS_RUNNING
    ).first()
    if session is None:
        return jsonify({'code': 200, 'data': None})
    return jsonify({'code': 200, 'data': _session_dict(session)})


def _session_dict(session: TimerSession) -> dict:
    d = session.to_dict()
    task = StudyTask.query.get(session.task_id) if session.task_id else None
    d['task'] = task.to_dict() if task else None
    return d


# ------------------------- 学习统计 -------------------------
@plan_bp.route('/stats', methods=['GET'])
@login_required
def plan_stats(current_user):
    """按范围统计学习时长 / 次数 / 科目占比 / 每日趋势，以及任务完成率。

    range: day(今日) / week(近7天) / month(近30天) / all(全部)
    """
    range_type = (request.args.get('range') or 'day').strip().lower()
    now = datetime.utcnow()
    if range_type == 'week':
        start = now - timedelta(days=7)
    elif range_type == 'month':
        start = now - timedelta(days=30)
    elif range_type == 'all':
        start = datetime(2000, 1, 1)
    else:  # day
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = (
        TimerSession.query
        .filter(
            TimerSession.user_id == current_user.id,
            TimerSession.status == TimerSession.STATUS_DONE,
            TimerSession.ended_at >= start,
        )
        .all()
    )

    total_seconds = 0
    session_count = 0
    by_subject: dict[str, int] = {}
    daily: dict[str, int] = {}
    for s in sessions:
        secs = s.duration_seconds or 0
        total_seconds += secs
        session_count += 1
        subj = '未关联'
        if s.task_id:
            t = StudyTask.query.get(s.task_id)
            if t:
                subj = t.subject
        by_subject[subj] = by_subject.get(subj, 0) + secs
        dkey = s.ended_at.strftime('%Y-%m-%d') if s.ended_at else start.strftime('%Y-%m-%d')
        daily[dkey] = daily.get(dkey, 0) + secs

    today = date.today()
    tasks = (
        StudyTask.query
        .filter(
            StudyTask.user_id == current_user.id,
            StudyTask.date >= start.date(),
            StudyTask.date <= today,
        )
        .all()
    )
    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks if t.status == StudyTask.STATUS_DONE)
    completion_rate = round(done_tasks / total_tasks, 3) if total_tasks else 0

    return jsonify({
        'code': 200,
        'data': {
            'range': range_type,
            'total_seconds': total_seconds,
            'total_hours': round(total_seconds / 3600, 2),
            'session_count': session_count,
            'by_subject': by_subject,
            'daily': [{'date': k, 'seconds': v} for k, v in sorted(daily.items())],
            'task_total': total_tasks,
            'task_done': done_tasks,
            'completion_rate': completion_rate,
        },
    })
