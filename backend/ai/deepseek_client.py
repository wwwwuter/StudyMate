import os
import time
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ---- 错误分类 ----
class DeepSeekError(Exception):
    """DeepSeek 调用相关错误的基类。"""


class DeepSeekAuthError(DeepSeekError):
    """认证失败（401）—— 通常是 API Key 无效，不重试。"""


class DeepSeekRateLimitError(DeepSeekError):
    """触发限流（429）—— 可重试。"""


class DeepSeekTransientError(DeepSeekError):
    """可重试的瞬时错误（超时 / 网络 / 5xx）。"""


class DeepSeekAPIError(DeepSeekError):
    """其他 API 错误（含「未配置 Key」的快捷报错）。"""


def _classify(exc: Exception) -> DeepSeekError:
    """把底层异常归并为可重试 / 不可重试的 DeepSeekError。"""
    msg = str(exc).lower()
    # openai SDK 异常类型优先判断
    try:
        from openai import (
            AuthenticationError,
            RateLimitError,
            APITimeoutError,
            APIConnectionError,
            APIStatusError,
        )
        if isinstance(exc, AuthenticationError):
            return DeepSeekAuthError(f'DeepSeek 认证失败（检查 DEEPSEEK_API_KEY）：{exc}')
        if isinstance(exc, RateLimitError):
            return DeepSeekRateLimitError(f'DeepSeek 触发限流：{exc}')
        if isinstance(exc, (APITimeoutError, APIConnectionError)):
            return DeepSeekTransientError(f'DeepSeek 网络/超时错误：{exc}')
        if isinstance(exc, APIStatusError):
            status = getattr(exc, 'status_code', None)
            if status == 429:
                return DeepSeekRateLimitError(f'DeepSeek 限流(429)：{exc}')
            if status is not None and 500 <= status < 600:
                return DeepSeekTransientError(f'DeepSeek 服务端错误({status})：{exc}')
            return DeepSeekAPIError(f'DeepSeek API 错误({status})：{exc}')
    except Exception:
        pass  # openai 未安装或异常类型不匹配，走通用判断

    if '401' in msg or 'unauthorized' in msg or 'authentication' in msg:
        return DeepSeekAuthError(f'DeepSeek 认证失败：{exc}')
    if '429' in msg or 'rate limit' in msg:
        return DeepSeekRateLimitError(f'DeepSeek 限流：{exc}')
    if 'timeout' in msg or 'connection' in msg or 'timed out' in msg:
        return DeepSeekTransientError(f'DeepSeek 网络/超时错误：{exc}')
    return DeepSeekAPIError(f'DeepSeek 调用失败：{exc}')


class DeepSeekClient:
    """DeepSeek API 客户端封装（Phase 8 强化：重试 / 错误分类 / 可注入）。

    - 支持 env 配置：DEEPSEEK_API_KEY / DEEPSEEK_API_BASE / DEEPSEEK_MODEL /
      DEEPSEEK_TIMEOUT / DEEPSEEK_MAX_RETRIES。
    - 对瞬时错误（超时 / 429 / 5xx）做指数退避重试；认证错误不重试。
    - 可通过构造参数注入 client（测试用），无需真实网络。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        client: Any = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv('DEEPSEEK_API_KEY', '')
        self.api_base = api_base or os.getenv('DEEPSEEK_API_BASE', 'https://api.deepseek.com')
        self.model = model or os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.timeout = timeout if timeout is not None else int(os.getenv('DEEPSEEK_TIMEOUT', '60'))
        self.max_retries = max_retries if max_retries is not None else int(os.getenv('DEEPSEEK_MAX_RETRIES', '3'))
        self._client = client  # 注入用（测试）
        self._sleep = time.sleep  # 可注入以加速测试

        if not self.api_key:
            logger.warning('DEEPSEEK_API_KEY 未设置，AI 功能将不可用')

    def _get_client(self):
        """延迟创建 OpenAI 客户端（仅在实际调用时加载 openai）。"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=self.timeout,
            )
        return self._client

    def _create(self, messages, temperature, max_tokens, response_format):
        client = self._get_client()
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format is not None:
            kwargs['response_format'] = response_format
        return client.chat.completions.create(**kwargs)

    def chat(self, messages, temperature=0.7, max_tokens=2048, response_format=None) -> str:
        """调用 DeepSeek 对话 API，返回助手消息文本。

        对可重试错误做指数退避（上限 30s），认证错误立即抛出。
        """
        if not self.api_key:
            raise DeepSeekAPIError('DeepSeek API Key 未配置')

        last_exc: Optional[DeepSeekError] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._create(messages, temperature, max_tokens, response_format)
                return resp.choices[0].message.content
            except DeepSeekAuthError:
                raise
            except DeepSeekError as e:
                last_exc = e
                if isinstance(e, (DeepSeekRateLimitError, DeepSeekTransientError)) and attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
                raise
            except Exception as e:
                err = _classify(e)
                last_exc = err
                if isinstance(err, (DeepSeekRateLimitError, DeepSeekTransientError)) and attempt < self.max_retries:
                    self._backoff(attempt)
                    continue
                raise err

        raise last_exc or DeepSeekAPIError('DeepSeek 调用失败（未知错误）')

    def chat_completion(self, messages, temperature=0.7, max_tokens=2048, response_format=None):
        """返回原始响应对象（需要 usage / 流式等高级用法时使用）。"""
        if not self.api_key:
            raise DeepSeekAPIError('DeepSeek API Key 未配置')
        return self._create(messages, temperature, max_tokens, response_format)

    def _backoff(self, attempt: int):
        wait = min(2 ** attempt, 30)
        logger.warning(f'DeepSeek 第 {attempt} 次调用失败，{wait}s 后重试')
        self._sleep(wait)

    def is_available(self) -> bool:
        """检查 API 是否可用（已配置 Key）。"""
        return bool(self.api_key)
