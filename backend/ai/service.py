import logging
from ai.deepseek_client import DeepSeekClient
from ai.prompt import (
    DAILY_SUMMARY_PROMPT,
    PLAN_OPTIMIZE_PROMPT,
    CHAT_PROMPT,
    RAG_CHAT_PROMPT,
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