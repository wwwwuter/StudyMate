import logging
import os
import json
import re

from ai.deepseek_client import DeepSeekClient
from ai.prompt import (
    DAILY_SUMMARY_PROMPT,
    PLAN_OPTIMIZE_PROMPT,
    CHAT_PROMPT,
    RAG_CHAT_PROMPT,
    PDF_TASK_EXTRACT_PROMPT,
)
from ai.rag import RAGService

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务层"""

    def __init__(self):
        self.client = DeepSeekClient()
        self.rag = RAGService()

    def daily_summary(self, input_data: str) -> str:
        """每日学习总结"""
        prompt = DAILY_SUMMARY_PROMPT.format(input_data=input_data)
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习助手。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    def plan_optimize(self, input_data: str) -> str:
        """学习计划优化"""
        prompt = PLAN_OPTIMIZE_PROMPT.format(input_data=input_data)
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习规划专家。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    def chat(self, message: str) -> str:
        """AI 对话"""
        messages = [
            {'role': 'system', 'content': '你是一个专业的考研学习助手。'},
            {'role': 'user', 'content': CHAT_PROMPT.format(message=message)},
        ]
        return self.client.chat(messages)

    def chat_with_rag(self, question: str) -> str:
        """基于 RAG 知识库的对话"""
        context_docs = self.rag.search(question)
        context = '\n\n'.join(context_docs) if context_docs else '未找到相关学习资料。'

        prompt = RAG_CHAT_PROMPT.format(context=context, question=question)
        messages = [
            {'role': 'system', 'content': '你是一个基于学习资料的专业考研学习助手。'},
            {'role': 'user', 'content': prompt},
        ]
        return self.client.chat(messages)

    def extract_tasks(self, pdf_text: str, user_id: int = 0) -> list[dict]:
        """从 PDF 提取文本中识别学习计划任务，返回结构化 list[dict]。

        每条：{date, subject, content, start_time, end_time, status}。
        - 配置了 DEEPSEEK_API_KEY：调用 DeepSeek 做智能识别。
        - 未配置但开启 PDF_AI_MOCK：用正则解析作为降级（离线 / CI 可用）。
        - 两者皆无：抛出 ValueError，由路由返回明确错误。
        """
        if self.client.is_available():
            prompt = PDF_TASK_EXTRACT_PROMPT.replace('<<<TEXT>>>', pdf_text)
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
        }
        if not item['date'] or not item['content']:
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
    }
