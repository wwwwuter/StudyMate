"""AI 接入设置路由。

系统不持有任何全局 API Key —— 所有 AI 能力使用的 Key 都由学生在「设置」页
自行填写，仅保存在本机数据库（user_ai_settings）。本模块只负责这份配置的
读取与保存，以及基于用户数据的 AI 学习建议。
"""
import logging

from flask import Blueprint, request, jsonify
from datetime import datetime

from models.ai_setting import UserAISetting, DEFAULT_API_BASE, DEFAULT_MODEL
from utils.local_auth import login_required

logger = logging.getLogger(__name__)

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
    """基于今日复习情况生成 AI 学习建议（双轨）。

    - 配置了可用 Key：调用用户的 AI 生成个性化建议（source='ai'）；
      调用失败自动回退规则模板，不阻塞页面。
    - 未配置 Key / 已禁用：走规则模板建议（source='template'），
      基于今日统计的完成率 / 时长 / 科目均衡 / 模式分布生成。
    数据源统一使用 today_stat()（StudyRecord + StudyTask，与统计页同口径）。
    """
    from ai.service import AIService
    from services.stat_service import today_stat, build_template_advice, plan_deviation

    stat = today_stat(current_user)
    deviation = plan_deviation(current_user, days=7)  # 近 7 天低完成率科目（计划偏差）
    client = AIService().client_for_user(current_user.id)

    if client is not None and client.is_available():
        try:
            lines = [
                f'今日任务共 {stat["task_total"]} 项，已完成 {stat["task_completed"]} 项（完成率 {stat["completion_rate"]}%）。',
                f'今日学习时长 {round(stat["study_time"] / 60)} 分钟。',
            ]
            if stat.get('subjects'):
                lines.append('按科目：' + '、'.join(
                    f"{s['name']} {round(s['time'] / 60)}分钟" for s in stat['subjects']
                ))
            else:
                lines.append('按科目：（暂无）')
            lines.append(
                '计时模式：番茄钟 {pomo} 分钟、任务 {task} 分钟、自由 {free} 分钟、倒计时 {cd} 分钟。'.format(
                    pomo=round(stat.get('pomodoro_time', 0) / 60),
                    task=round(stat.get('task_time', 0) / 60),
                    free=round(stat.get('free_time', 0) / 60),
                    cd=round(stat.get('countdown_time', 0) / 60),
                )
            )
            lines.append('今日任务明细：')
            for t in stat.get('tasks', []):
                done_flag = '已完成' if t.get('status') == 'done' else '未完成'
                lines.append(f"- {t.get('subject', '')} / {t.get('content', '')} [{done_flag}]")
            # 计划偏差：近 7 天低完成率科目
            if deviation:
                lines.append('近 7 天计划偏差（完成率 < 50% 的科目）：')
                for d in deviation:
                    lines.append(f"- {d['subject']}: {d['done']}/{d['total']}（完成率 {d['rate']}%）")
            else:
                lines.append('近 7 天无显著计划偏差。')

            prompt = (
                '你是考研学习教练。下面是某学生今日的学习复习情况与近 7 天计划偏差，'
                '请基于数据给出分析与建议。\n'
                + '\n'.join(lines)
                + '\n\n请只输出如下 JSON（不要 Markdown 围栏，不要额外说明）：\n'
                '{"summary":"今日学习总结（1-2句）",'
                '"problems":"发现的问题（含计划偏差：如某科目连续低完成率）",'
                '"suggestions":"可执行的调整建议（如调整某科目时间/任务量）"}'
            )
            messages = [
                {'role': 'system', 'content': '你是严谨的学习教练，只输出 JSON。'},
                {'role': 'user', 'content': prompt},
            ]
            raw = client.chat(messages, temperature=0.4, max_tokens=1024)
            result = _parse_analyze(raw)
            result['source'] = 'ai'
            result['deviation'] = deviation
            result['generated_at'] = datetime.now().isoformat(timespec='seconds')
            return jsonify({'code': 200, 'data': result})
        except Exception as e:
            logger.warning(f'AI 学习建议生成失败，回退模板：{e}')

    result = build_template_advice(stat, deviation)
    result['source'] = 'template'
    result['deviation'] = deviation
    result['generated_at'] = datetime.now().isoformat(timespec='seconds')
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
