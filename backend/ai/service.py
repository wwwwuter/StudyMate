"""AI 服务层：学习计划智能解析。

设计约束（唯一 Key 来源）：
    整个系统**只使用学生在「设置」页配置的 API Key**（存于 user_ai_settings，本地存储）。
    不读取任何环境变量 Key，不存在系统级/全局 Key，不存在正则或模板降级。
    未配置 / 已禁用 / Key 无效 → 直接抛 ValueError，由路由返回明确错误，引导用户去设置页。
"""
import logging
import json
import re

from ai.deepseek_client import DeepSeekClient
from ai.prompt_manager import PromptManager

try:
    from models.ai_setting import DEFAULT_API_BASE, DEFAULT_MODEL
except Exception:  # 配置尚未就绪时兜底
    DEFAULT_API_BASE = 'https://api.deepseek.com'
    DEFAULT_MODEL = 'deepseek-chat'

logger = logging.getLogger(__name__)

# 未配置 Key 时的统一提示语
NO_KEY_MESSAGE = (
    '未配置 AI API Key，无法进行智能解析。'
    '请到「设置」页填入你自己的 API Key（OpenAI 兼容接口均可）后重试。'
)

NO_VISION_KEY_MESSAGE = (
    '未配置可用的 AI API Key，无法识别图片计划。'
    '请到「设置」页填入支持视觉的模型 Key（如 qwen-vl / glm-4v / gpt-4o）后重试。'
)


class AIService:
    """AI 服务层。所有能力均需要用户自己配置的 Key，无任何降级路径。

    prompts 可注入，便于测试。
    """

    def __init__(self, prompts=None):
        self.prompts = prompts or PromptManager()

    # --------------------------- 用户级客户端 ---------------------------
    def client_for_user(self, user_id):
        """构建该学生的 AI 客户端（只使用其在设置页保存的 Key / Base / Model）。

        返回 None 表示未配置或已禁用。
        """
        try:
            from models.ai_setting import UserAISetting
            s = UserAISetting.get_for_user(user_id)
        except Exception as e:
            logger.warning(f'读取用户 AI 设置失败（user_id={user_id}）：{e}')
            return None
        if s is None or not s.enabled:
            return None
        if not s.decrypted_key:
            return None
        return DeepSeekClient(
            api_key=s.decrypted_key,
            api_base=s.api_base or DEFAULT_API_BASE,
            model=s.model or DEFAULT_MODEL,
        )

    def client_for_user_vision(self, user_id):
        """图片计划识别客户端：优先用独立的视觉模型设置，否则回退该用户的聊天 Key。

        注意：这里的「回退」仍然只在**同一个用户自己配置的 Key** 之间发生，
        不涉及任何系统级 Key。
        """
        try:
            from models.vision_setting import UserVisionSetting
            vs = UserVisionSetting.get_for_user(user_id)
        except Exception:
            vs = None
        if vs is not None and vs.decrypted_key:
            return DeepSeekClient(
                api_key=vs.decrypted_key,
                api_base=vs.api_base or DEFAULT_API_BASE,
                model=vs.model or 'gpt-4o-mini',
            )
        return self.client_for_user(user_id)

    def require_client(self, user_id):
        """取该用户的 AI 客户端，未配置则抛 ValueError（不降级）。"""
        client = self.client_for_user(user_id)
        if client is None or not client.is_available():
            raise ValueError(NO_KEY_MESSAGE)
        return client

    def require_vision_client(self, user_id):
        """取该用户的视觉客户端，未配置则抛 ValueError（不降级）。"""
        client = self.client_for_user_vision(user_id)
        if client is None or not client.is_available():
            raise ValueError(NO_VISION_KEY_MESSAGE)
        return client

    # --------------------------- 文本 / PDF 任务提取 ---------------------------
    def extract_tasks(self, plan_text: str, user_id: int) -> dict:
        """从纯文本（含 PDF 提取文本）中识别学习计划，返回三段结构 dict。

        无 Key 直接抛 ValueError。
        """
        from datetime import date as _date

        client = self.require_client(user_id)
        prompt = self.prompts.render(
            'pdf_task_extract',
            TEXT=plan_text,
            TODAY=_date.today().isoformat(),
        )
        messages = [
            {'role': 'system', 'content': '你是考研学习计划排期助手，只输出 JSON。'},
            {'role': 'user', 'content': prompt},
        ]
        # 长计划表输出很大，4096 会被截断成半个 JSON
        raw = client.chat(messages, temperature=0.2, max_tokens=8192)
        return _parse_tasks_json(raw)

    # --------------------------- Word 文档任务提取 ---------------------------
    def extract_tasks_from_docx(self, file_storage, user_id: int) -> dict:
        """从 Word（.docx）学习计划文档中识别任务，返回三段结构 dict。

        返回：{
            'daily_tasks': [...],       # 每日任务
            'schedule_template': [...], # 作息安排（如有）
            'weekly_goals': [...],      # 周目标（如有）
        }
        无 Key 直接抛 ValueError。
        """
        from datetime import date as _date
        from parser.doc_parser import extract_docx_text

        client = self.require_client(user_id)
        text = extract_docx_text(file_storage)
        prompt = self.prompts.render(
            'docx_task_extract',
            TEXT=text,
            TODAY=_date.today().isoformat(),
        )
        messages = [
            {'role': 'system', 'content': '你是考研学习计划排期助手，只输出 JSON。'},
            {'role': 'user', 'content': prompt},
        ]
        # 长计划表（数十天 × 每天多条）输出很大，4096 会被截断成半个 JSON
        raw = client.chat(messages, temperature=0.2, max_tokens=8192)
        return _parse_tasks_json(raw)

    # --------------------------- 图片/截图 计划视觉解析 ---------------------------
    def vision_parse_plan(self, image_b64: str, user_id: int) -> list[dict]:
        """识别学习计划图片/截图，返回结构化计划列表。

        :param image_b64: base64 编码的图片（不含 data: 前缀）。
        无 Key 直接抛 ValueError。
        """
        client = self.require_vision_client(user_id)

        prompt = self.prompts.render('plan_vision')
        messages = [
            {'role': 'system', 'content': '你是学习计划解析助手，只输出 JSON 数组。'},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{image_b64}'}},
                ],
            },
        ]
        try:
            raw = client.chat_completion(
                messages, temperature=0.2, max_tokens=4096
            ).choices[0].message.content
        except Exception as e:
            logger.warning(f'视觉解析失败：{e}')
            raise ValueError(f'图片识别失败（视觉模型调用错误）：{e}')
        return _parse_tasks_json(raw).get('daily_tasks', [])


# --------------------------- JSON 解析辅助 ---------------------------
def _repair_truncated_tasks(snippet: str):
    """尽力修复被 max_tokens 截断的 {"tasks":[...]} JSON。

    策略：定位最后一个完整的任务对象边界 '},'（或数组内的 '}'），截掉末尾不完整的
    条目后重新组合为合法 JSON。无法修复返回 None。
    """
    try:
        head = snippet[:snippet.find('[') + 1] if '[' in snippet else ''
        arr_body = snippet[snippet.find('[') + 1:]
        # 找最后一个 '},'（完整条目结束）或 '}'（单条目结束）
        last_sep = arr_body.rfind('},')
        if last_sep == -1:
            last_sep = arr_body.rfind('}')
        if last_sep == -1:
            return None
        fixed = head + arr_body[:last_sep + 1] + ']}'
        return json.loads(fixed)
    except Exception:
        return None


def _parse_tasks_json(raw: str) -> dict:
    """从 LLM 输出中稳健解析出任务列表（支持新旧两种结构）。

    新结构（通用版）：{"schedule_template": [...], "weekly_goals": [...], "daily_tasks": [...]}
    旧结构（PDF/打卡表）：{"tasks": [...]} 或直接 [...]

    返回：{"daily_tasks": [...], "schedule_template": [...], "weekly_goals": [...]}
    兼容：带 ```json 围栏、前后有说明文字、对象或数组形态；
    并对「max_tokens 截断导致 JSON 不完整」做尽力修复（丢弃最后一个不完整条目）。
    """
    empty = {'daily_tasks': [], 'schedule_template': [], 'weekly_goals': []}
    if not raw:
        return empty
    s = raw.strip()
    if s.startswith('```'):
        s = re.sub(r'^```[a-zA-Z]*\n?', '', s)
        s = re.sub(r'\n?```$', '', s).strip()
    start = s.find('{')
    end = s.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return empty
    try:
        data = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        # 尝试修复截断：截到最后一个完整的 "}," 任务边界
        data = _repair_truncated_tasks(s[start:end + 1])
        if data is None:
            return empty

    # 提取三段结构（新格式）或单段（旧格式）
    plan_name = None
    if isinstance(data, dict):
        plan_name = data.get('plan_name')
        daily_tasks = data.get('daily_tasks') or data.get('tasks') or data.get('data') or []
        schedule_template = data.get('schedule_template') or []
        weekly_goals = data.get('weekly_goals') or []
    elif isinstance(data, list):
        daily_tasks = data
        schedule_template = []
        weekly_goals = []
    else:
        return empty

    # 规范化 daily_tasks
    result_tasks = []
    for t in daily_tasks:
        if not isinstance(t, dict):
            continue
        item = {
            'date': t.get('date'),
            'subject': t.get('subject'),
            'content': t.get('content'),
            'start_time': t.get('start_time'),
            'end_time': t.get('end_time'),
            'status': t.get('status', 'pending'),
            'priority': t.get('priority'),
            'is_schedule': bool(t.get('is_schedule', False)),
        }
        if not item['content']:
            continue
        result_tasks.append(item)
    return {
        'plan_name': plan_name,
        'daily_tasks': result_tasks,
        'schedule_template': schedule_template,
        'weekly_goals': weekly_goals,
    }
