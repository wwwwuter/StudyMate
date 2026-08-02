"""AI 能力包。

Key 来源唯一：学生在「设置」页保存的个人配置。此处不创建任何持有全局 Key
的共享实例，调用方按需 `AIService()` 并传入 user_id。
"""
from ai.deepseek_client import DeepSeekClient
from ai.service import AIService

__all__ = ['DeepSeekClient', 'AIService']
