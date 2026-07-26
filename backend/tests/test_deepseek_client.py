"""Phase 8 DeepSeek 客户端测试（注入假 client，不联网）。"""
import pytest

from ai.deepseek_client import (
    DeepSeekClient,
    DeepSeekAPIError,
    DeepSeekAuthError,
    DeepSeekRateLimitError,
    DeepSeekTransientError,
)


def _resp(text):
    class M:
        content = text
    class Ch:
        message = M()
    class R:
        choices = [Ch()]
    return R()


def _fake_client(behaviors):
    """behaviors: 每次 create 调用的行为（异常对象或返回文本）。"""
    class Comp:
        def __init__(self, behaviors):
            self._b = list(behaviors)
        def create(self, **kw):
            b = self._b.pop(0)
            if isinstance(b, Exception):
                raise b
            return _resp(b)
    class Cli:
        def __init__(self):
            self.chat = type('T', (), {'completions': Comp(behaviors)})()
    return Cli()


def test_no_key_raises():
    c = DeepSeekClient(api_key='')
    with pytest.raises(DeepSeekAPIError):
        c.chat([{'role': 'user', 'content': 'hi'}])


def test_retry_then_success():
    c = DeepSeekClient(
        api_key='x', max_retries=3,
        client=_fake_client([RuntimeError('429 rate limit'), RuntimeError('timeout'), 'ok']),
    )
    c._sleep = lambda s: None
    assert c.chat([{'role': 'user', 'content': 'hi'}]) == 'ok'


def test_auth_error_no_retry():
    c = DeepSeekClient(
        api_key='x', max_retries=3,
        client=_fake_client([RuntimeError('401 unauthorized')]),
    )
    c._sleep = lambda s: None
    with pytest.raises(DeepSeekAuthError):
        c.chat([{'role': 'user', 'content': 'hi'}])


def test_transient_retry_then_fail():
    c = DeepSeekClient(
        api_key='x', max_retries=2,
        client=_fake_client([RuntimeError('timeout'), RuntimeError('timeout')]),
    )
    c._sleep = lambda s: None
    with pytest.raises((DeepSeekTransientError, DeepSeekRateLimitError, DeepSeekAPIError)):
        c.chat([{'role': 'user', 'content': 'hi'}])


def test_is_available():
    assert DeepSeekClient(api_key='').is_available() is False
    assert DeepSeekClient(api_key='x').is_available() is True
