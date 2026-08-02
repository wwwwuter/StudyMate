"""提示词管理测试（仅保留计划解析所需的三个模板）。"""
import pytest

from ai.prompt_manager import PromptManager


def test_render_replaces_sentinel():
    pm = PromptManager()
    out = pm.render('pdf_task_extract', TEXT='数据X')
    assert '数据X' in out
    assert '<<<TEXT>>>' not in out


def test_render_missing_var_keeps_sentinel():
    pm = PromptManager()
    out = pm.render('pdf_task_extract')  # 未提供 TEXT
    assert '<<<TEXT>>>' in out


def test_list_prompts_only_plan_templates():
    pm = PromptManager()
    keys = {p['key'] for p in pm.list_prompts()}
    assert keys == {'pdf_task_extract', 'docx_task_extract', 'plan_vision'}


def test_docx_extract_sentinel():
    pm = PromptManager()
    out = pm.render('docx_task_extract', TEXT='文本Y')
    assert '文本Y' in out and '<<<TEXT>>>' not in out


def test_unknown_prompt_raises():
    pm = PromptManager()
    with pytest.raises(KeyError):
        pm.get('rag_chat')
