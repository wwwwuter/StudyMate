import os
import time
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API 客户端封装"""

    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.api_base = os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
        self.model = 'deepseek-chat'
        self.timeout = 60

        if not self.api_key:
            logger.warning('DEEPSEEK_API_KEY 未设置，AI 功能将不可用')

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=self.timeout,
        )

    def chat(self, messages, temperature=0.7, max_tokens=2048):
        """调用 DeepSeek 对话 API"""
        if not self.api_key:
            raise ValueError('DeepSeek API Key 未配置')

        try:
            start_time = time.time()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start_time
            logger.info(f'DeepSeek API 调用成功，耗时: {elapsed:.2f}s')

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f'DeepSeek API 调用失败: {e}')
            raise

    def is_available(self):
        """检查 API 是否可用"""
        return bool(self.api_key)