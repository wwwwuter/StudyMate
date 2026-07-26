import logging
import os
import json
import re

from ai.deepseek_client import DeepSeekClient
from ai.prompt_manager import PromptManager
from ai.rag import RAGService

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务层（Phase 8：统一用 PromptManager 渲染，RAG 走向量检索）。

    支持依赖注入（client / rag / prompts），便于测试用假对象替换。
    """

    def __init__(self, client=None, rag=None, prompts=None):
        self.client = client or DeepSeekClient()
        self.rag = rag or RAGService()
        self.prompts = prompts or PromptManager()

    # --------------------------- 通用对话 / 总结 / 优化 ---------------------------
    def daily_summary(self, input_data: str) -> str:
        prompt = self.prompts.render('daily_summary', INPUT_DATA=input_data)
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习助手。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    def plan_optimize(self, input_data: str) -> str:
        prompt = self.prompts.render('plan_optimize', INPUT_DATA=input_data)
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习规划专家。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    def chat(self, message: str) -> str:
        prompt = self.prompts.render('chat', MESSAGE=message)
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习助手。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    # --------------------------- RAG 问答 ---------------------------
    def rag_answer(self, user_id, question: str, top_k: int = None) -> dict:
        """基于用户资料库的 RAG 问答。

        返回 {answer, sources, source}。source='ai'（DeepSeek 生成）/
        'retrieval'（无密钥，仅返回检索片段）/ 'empty'（无资料）。
        """
        sources = self.rag.retrieve(user_id, question, top_k=top_k)
        context = '\n\n'.join(
            f"【{s['title']}】\n{s['content']}" for s in sources
        ) if sources else '未找到相关学习资料。'

        prompt = self.prompts.render('rag_chat', CONTEXT=context, QUESTION=question)

        if self.client.is_available():
            try:
                messages = [
                    {'role': 'system', 'content': '你是基于学习资料的专业考研学习助手。'},
                    {'role': 'user', 'content': prompt},
                ]
                answer = self.client.chat(messages, temperature=0.5, max_tokens=1500)
                return {'answer': answer, 'sources': sources, 'source': 'ai'}
            except Exception as e:
                logger.warning(f'RAG AI 生成失败，回退检索结果：{e}')

        # 无密钥或 AI 失败：返回检索片段作为答案
        if sources:
            answer = '（未连接 AI，以下为检索到的相关资料）\n\n' + '\n\n'.join(
                f"【{s['title']}】{s['content']}" for s in sources
            )
            return {'answer': answer, 'sources': sources, 'source': 'retrieval'}

        return {'answer': '未找到相关资料，请先上传学习资料。', 'sources': [], 'source': 'empty'}

    # --------------------------- 学习报告（指标 -> 文字）---------------------------
    def learning_report(self, metrics: dict) -> dict:
        """生成学习报告文字总结。

        返回 {text, source}。source='ai' 表示来自 DeepSeek；
        source='template' 表示离线模板降级（无密钥或 LEARNING_REPORT_MOCK=true）。
        """
        use_ai = self.client.is_available() and not os.getenv(
            'LEARNING_REPORT_MOCK', 'false').lower() in ('1', 'true', 'yes')
        if use_ai:
            try:
                metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
                prompt = self.prompts.render('learning_report', METRICS=metrics_json)
                messages = [
                    {'role': 'system', 'content': '你是考研学习数据分析专家。'},
                    {'role': 'user', 'content': prompt},
                ]
                text = self.client.chat(messages, temperature=0.6, max_tokens=1200)
                return {'text': text, 'source': 'ai'}
            except Exception as e:  # AI 失败兜底到模板，保证报告可用
                logger.warning(f'学习报告 AI 生成失败，回退模板：{e}')
        return {'text': _template_report(metrics), 'source': 'template'}

    # --------------------------- PDF 任务提取 ---------------------------
    def extract_tasks(self, pdf_text: str, user_id: int = 0) -> list[dict]:
        """从 PDF 提取文本中识别学习计划任务，返回结构化 list[dict]。

        - 配置了 DEEPSEEK_API_KEY：调用 DeepSeek 做智能识别。
        - 未配置但开启 PDF_AI_MOCK：用正则解析作为降级（离线 / CI 可用）。
        - 两者皆无：抛出 ValueError，由路由返回明确错误。
        """
        if self.client.is_available():
            prompt = self.prompts.render('pdf_task_extract', TEXT=pdf_text)
            messages = [
                {'role': 'system', 'content': '你是考研学习计划结构化提取助手，只输出 JSON。'},
                {'role': 'user', 'content': prompt},
            ]
            raw = self.client.chat(messages, temperature=0.2, max_tokens=2048)
            return _parse_tasks_json(raw)

        if os.getenv('PDF_AI_MOCK', 'false').lower() in ('1', 'true', 'yes'):
            from parser.pdf_parser import _parse_pdf_text
            return [_task_to_extract_dict(t) for t in _parse_pdf_text(pdf_text, user_id)]

        raise ValueError(
            'DeepSeek API Key 未配置，无法执行智能解析'
            '（可设置 PDF_AI_MOCK=true 走正则降级，或在 .env 配置 DEEPSEEK_API_KEY）'
        )


def _parse_tasks_json(raw: str) -> list[dict]:
    """从 LLM 输出中稳健解析出任务列表。

    兼容：带 ```json 围栏、前后有说明文字、对象或数组形态。
    """
    if not raw:
        return []
    s = raw.strip()
    if s.startswith('```'):
        s = re.sub(r'^```[a-zA-Z]*\n?', '', s)
        s = re.sub(r'\n?```$', '', s).strip()
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        tasks = data.get('tasks') or data.get('data') or []
    elif isinstance(data, list):
        tasks = data
    else:
        tasks = []

    result = []
    for t in tasks:
        if not isinstance(t, dict):
            continue
        item = {
            'date': t.get('date'),
            'subject': t.get('subject'),
            'content': t.get('content'),
            'start_time': t.get('start_time'),
            'end_time': t.get('end_time'),
            'status': t.get('status', 'pending'),
            'confidence': t.get('confidence'),
            'reason': t.get('reason'),
            'date_note': t.get('date_note'),
        }
        if not item['content']:
            continue
        result.append(item)
    return result


def _task_to_extract_dict(t) -> dict:
    """将 StudyTask 转为 extract_tasks 的精简 dict（供 mock 降级使用）。"""
    return {
        'date': t.date.strftime('%Y-%m-%d') if t.date else None,
        'subject': t.subject,
        'content': t.content,
        'start_time': t.start_time.strftime('%H:%M') if t.start_time else None,
        'end_time': t.end_time.strftime('%H:%M') if t.end_time else None,
        'status': t.status,
        'confidence': 1.0,
        'reason': '正则降级解析',
        'date_note': None,
    }


def _fmt_dur(seconds: int) -> str:
    seconds = int(seconds or 0)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h:
        return f'{h}小时{m}分'
    if m:
        return f'{m}分'
    return f'{seconds}秒'


def _template_report(m: dict) -> str:
    """离线模板：基于聚合指标生成确定性中文学习报告（无需调用大模型）。"""
    total = m.get('total_hours', 0)
    sessions = m.get('session_count', 0)
    streak = m.get('streak', 0)
    tasks = m.get('tasks', {}) or {}
    done = tasks.get('done', 0)
    total_tasks = tasks.get('total', 0)
    rate = tasks.get('completion_rate', 0)
    planned = tasks.get('planned_minutes', 0)
    actual = tasks.get('actual_minutes', 0)

    by_subject = m.get('by_subject_actual', {}) or {}
    top_subject = max(by_subject, key=by_subject.get) if by_subject else None
    top_subject_dur = _fmt_dur(by_subject.get(top_subject, 0)) if top_subject else '—'

    if planned and actual:
        if actual >= planned:
            plan_note = f'实际学习 {_fmt_dur(actual*60)}，已超过计划 {_fmt_dur(planned*60)}，执行力很强。'
        else:
            gap = planned - actual
            plan_note = f'实际学习 {_fmt_dur(actual*60)}，距计划 {_fmt_dur(planned*60)} 还差 {_fmt_dur(gap*60)}，可适当提高专注度。'
    else:
        plan_note = '暂无任务计划时长数据，建议为任务补充预估时长以便对比。'

    lines = [
        f'【学习报告】本周期累计学习 {total} 小时，共 {sessions} 次计时会话，连续打卡 {streak} 天。',
        f'投入最多的科目是「{top_subject}」（{top_subject_dur}），可作为当前重心。',
        f'任务完成率 {rate}%（{done}/{total_tasks}）。{plan_note}',
    ]
    if rate >= 80:
        lines.append('亮点：任务完成率很高，保持节奏即可。')
    elif rate >= 50:
        lines.append('建议：完成率中等，可把大任务拆小、每天固定清空几件。')
    else:
        lines.append('提醒：完成率偏低，优先保证「少量但完成」，建立正反馈。')
    if streak >= 7:
        lines.append('连续打卡已超一周，习惯正在养成，了不起！')
    elif streak == 0:
        lines.append('今天还没开始学习，先从 25 分钟番茄钟热个身吧。')
    lines.append('下周建议：固定每日学习起点时段，针对薄弱科目加量，并坚持连续打卡。')
    return '\n'.join(lines)
