import os
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 内置兜底提示词（与 prompts/ 目录文件内容一致；文件优先，缺文件时回退这里）
from ai.prompt import (
    PDF_TASK_EXTRACT_PROMPT,
    DOCX_TASK_EXTRACT_PROMPT,
    PLAN_VISION_PROMPT,
)

_BUILTIN: Dict[str, str] = {
    'pdf_task_extract': PDF_TASK_EXTRACT_PROMPT,
    'docx_task_extract': DOCX_TASK_EXTRACT_PROMPT,
    'plan_vision': PLAN_VISION_PROMPT,
}

_SENTINEL_RE = re.compile(r'<<<\s*([A-Z0-9_]+)\s*>>>')


class PromptManager:
    """集中管理提示词模板。

    - 优先从 prompts/ 目录加载 .txt（可版本化、非开发者也可改，无需改代码）。
    - 文件缺失时回退到 ai/prompt.py 中的内置常量。
    - 渲染统一用 <<<VAR>>> 哨兵替换，避免 JSON 大括号触发 .format 的 KeyError。
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = prompts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts'
        )
        self._cache: Dict[str, str] = {}
        self._descriptions: Dict[str, str] = {}
        self._load_all()

    def _load_all(self):
        # 先装载内置常量，文件存在则覆盖
        for key, text in _BUILTIN.items():
            self._cache[key] = text
            self._descriptions[key] = ''
        if not os.path.isdir(self.prompts_dir):
            logger.warning(f'prompts 目录不存在：{self.prompts_dir}，仅使用内置常量')
            return
        for fn in os.listdir(self.prompts_dir):
            if not fn.endswith('.txt'):
                continue
            key = fn[:-4]
            path = os.path.join(self.prompts_dir, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                desc = ''
                lines = text.splitlines()
                if lines and lines[0].startswith('# desc:'):
                    desc = lines[0][len('# desc:'):].strip()
                    text = '\n'.join(lines[1:]).lstrip('\n')
                self._cache[key] = text
                self._descriptions[key] = desc
            except Exception as e:
                logger.warning(f'加载提示词文件失败 {path}：{e}')

    def reload(self):
        """重新从磁盘加载（修改 .txt 后无需重启）。"""
        self._cache.clear()
        self._descriptions.clear()
        self._load_all()

    def get(self, key: str) -> str:
        if key not in self._cache:
            raise KeyError(f'未知提示词：{key}')
        return self._cache[key]

    def has(self, key: str) -> bool:
        return key in self._cache

    def render(self, key: str, variables: Optional[Dict[str, str]] = None, **kwargs) -> str:
        """用 <<<VAR>>> 哨兵替换变量；未提供的变量保留原哨兵。"""
        tpl = self.get(key)
        vars_ = dict(variables or {})
        vars_.update(kwargs)

        def repl(m):
            name = m.group(1)
            return str(vars_[name]) if name in vars_ else m.group(0)

        return _SENTINEL_RE.sub(repl, tpl)

    def list_prompts(self) -> List[Dict[str, str]]:
        return [
            {
                'key': k,
                'description': self._descriptions.get(k, ''),
                'preview': self._cache[k][:200],
            }
            for k in self._cache
        ]
