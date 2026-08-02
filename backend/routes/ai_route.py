"""AI 接入设置路由。

系统不持有任何全局 API Key —— 所有 AI 能力使用的 Key 都由学生在「设置」页
自行填写，仅保存在本机数据库（user_ai_settings）。本模块只负责这份配置的
读取与保存，以及基于用户数据的 AI 学习分析。
"""
from flask import Blueprint, request, jsonify
from datetime import date

from models.ai_setting import UserAISetting, DEFAULT_API_BASE, DEFAULT_MODEL
from models.task import StudyTask
from models.timer_session import TimerSession
from utils.local_auth import login_required
from sqlalchemy import func

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/key-settings', methods=['GET'])
@login_required
def get_key_settings(current_user):
    """读取当前学生的 AI 接入设置（Key 脱敏返回）。"""
    s = UserAISetting.get_for_user(current_user.id)
    if s is None:
        return jsonify({'code': 200, 'data': {
            'api_base': DEFAULT_API_BASE, 'model': DEFAULT_MODEL,
            'enabled': True, 'has_key': False, 'api_key_masked': None,
        }})
    return jsonify({'code': 200, 'data': s.to_dict()})


@ai_bp.route('/key-settings', methods=['POST'])
@login_required
def save_key_settings(current_user):
    """保存当前学生的 AI 接入设置（Key 仅存本地，开发者不持有）。

    注意：含 `*` 的掩码串会被 save_for_user 视为「未修改」而忽略，
    避免前端回显的脱敏值覆盖掉真实 Key。
    """
    data = request.get_json(silent=True) or {}
    api_key = (data.get('api_key') or '').strip() or None
    api_base = (data.get('api_base') or '').strip() or None
    model = (data.get('model') or '').strip() or None
    enabled = data.get('enabled')
    s = UserAISetting.save_for_user(
        current_user.id, api_key=api_key, api_base=api_base, model=model, enabled=enabled,
    )
    return jsonify({'code': 200, 'message': '已保存', 'data': s.to_dict()})


@ai_bp.route('/analyze', methods=['POST'])
@login_required
def analyze(current_user):
    """基于当日 StudyTask + TimerSession 生成 AI 学习分析（总结 / 问题 / 建议）。

    仅使用用户在「设置」页配置的 Key；未配置或无效直接返回 400 引导去设置页。
    """
    from ai.service import AIService

    try:
        client = AIService().require_client(current_user.id)
    except ValueError as e:
        return jsonify({'code': 400, 'message': str(e)}), 400

    today = date.today()
    tasks = StudyTask.query.filter_by(user_id=current_user.id, date=today).all()
    sessions = TimerSession.query.filter(
        TimerSession.user_id == current_user.id,
        TimerSession.status == TimerSession.STATUS_DONE,
        func.date(TimerSession.ended_at) == today.isoformat(),
    ).all()

    total = len(tasks)
    done = sum(1 for t in tasks if t.status == StudyTask.STATUS_DONE)
    actual_by_subject: dict[str, int] = {}
    for s in sessions:
        subj = '未关联'
        if s.task_id:
            t = StudyTask.query.get(s.task_id)
            if t:
                subj = t.subject
        actual_by_subject[subj] = actual_by_subject.get(subj, 0) + (s.duration_seconds or 0)

    lines = [f'今日任务共 {total} 项，已完成 {done} 项。']
    for t in tasks:
        plan = t.estimated_minutes or 0
        lines.append(f'- {t.subject} / {t.content} [{"已完成" if t.status == StudyTask.STATUS_DONE else "未完成"}] 计划约 {plan} 分钟')
    lines.append('今日实际专注时长（按科目，单位分钟）：')
    if actual_by_subject:
        for k, v in actual_by_subject.items():
            lines.append(f'- {k}: {round(v / 60)} 分钟')
    else:
        lines.append('- （暂无计时记录）')

    prompt = (
        '你是考研学习教练。下面是某学生今日的学习计划执行情况，请基于数据给出分析。\n'
        + '\n'.join(lines)
        + '\n\n请只输出如下 JSON（不要 Markdown 围栏，不要额外说明）：\n'
        '{"summary":"今日学习总结（1-2句）",'
        '"problems":"发现的问题（如某科目投入不足、完成率低、时间分配不均）",'
        '"suggestions":"可执行的调整建议（如明天增加某科目 X 分钟）"}'
    )
    messages = [
        {'role': 'system', 'content': '你是严谨的学习教练，只输出 JSON。'},
        {'role': 'user', 'content': prompt},
    ]

    try:
        raw = client.chat(messages, temperature=0.4, max_tokens=1024)
    except Exception as e:
        return jsonify({'code': 500, 'message': f'AI 分析失败：{e}'}), 500

    result = _parse_analyze(raw)
    return jsonify({'code': 200, 'data': result})


def _parse_analyze(raw: str) -> dict:
    """从模型输出稳健解析出 {summary, problems, suggestions}。"""
    empty = {'summary': '', 'problems': '', 'suggestions': ''}
    if not raw:
        return empty
    s = raw.strip()
    if s.startswith('```'):
        s = s[s.find('{', 0):]
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        # 退化：把整段当成总结
        return {'summary': raw.strip(), 'problems': '', 'suggestions': ''}
    try:
        import json
        data = json.loads(s[start:end + 1])
    except Exception:
        return {'summary': raw.strip(), 'problems': '', 'suggestions': ''}
    return {
        'summary': str(data.get('summary', '') or ''),
        'problems': str(data.get('problems', '') or ''),
        'suggestions': str(data.get('suggestions', '') or ''),
    }
