"""Phase 8 提示词管理测试。"""
from ai.prompt_manager import PromptManager


def test_render_replaces_sentinel():
    pm = PromptManager()
    out = pm.render('daily_summary', INPUT_DATA='数据X')
    assert '数据X' in out
    assert '<<<' not in out


def test_render_missing_var_keeps_sentinel():
    pm = PromptManager()
    out = pm.render('daily_summary')  # 未提供 INPUT_DATA
    assert '<<<INPUT_DATA>>>' in out


def test_list_prompts_includes_all_keys():
    pm = PromptManager()
    keys = {p['key'] for p in pm.list_prompts()}
    assert {
        'daily_summary', 'plan_optimize', 'chat',
        'rag_chat', 'learning_report', 'pdf_task_extract',
    } <= keys


def test_pdf_extract_sentinel():
    pm = PromptManager()
    out = pm.render('pdf_task_extract', TEXT='文本Y')
    assert '文本Y' in out and '<<<TEXT>>>' not in out


def test_rag_chat_sentinels():
    pm = PromptManager()
    out = pm.render('rag_chat', CONTEXT='上下文', QUESTION='问题')
    assert '上下文' in out and '问题' in out
    assert '<<<CONTEXT>>>' not in out and '<<<QUESTION>>>' not in out
