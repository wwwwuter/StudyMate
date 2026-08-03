"""系统级接口：应用启动时的一次性状态聚合（Phase 6-2）。

GET /api/system/bootstrap 在 App 启动时一次返回「用户 + 计时 + 提醒」全部运行状态，
替代前端依次调用 /auth/status + /timer/current + /reminder/settings 的多次请求，
供启动水合（hydrate）后直接渲染，避免页面闪跳。
"""
from flask import Blueprint, jsonify

from models.timer_session import TimerSession
from utils.local_auth import _extract_token, get_user_by_token

system_bp = Blueprint('system', __name__)


@system_bp.route('/bootstrap', methods=['GET'])
def bootstrap():
    """返回应用启动所需的全部运行状态。

    未登录（无有效令牌）时仍返回 setup_done，供前端决定进 /auth 还是主界面；
    已登录则附带计时会话与提醒设置。不强制鉴权——这是登录前的探路接口。
    """
    user = get_user_by_token(_extract_token())
    if user is not None:
        session = (
            TimerSession.query
            .filter_by(user_id=user.id, status=TimerSession.STATUS_RUNNING)
            .first()
        )
        timer = _session_dict(session) if session else None
        reminder_enabled = _reminder_enabled(user.id)
    else:
        timer = None
        reminder_enabled = True

    data = {
        'user': {
            'setup_done': _setup_done(),
            'authenticated': user is not None,
            'id': user.id if user else None,
            'username': user.username if user else None,
        },
        'timer': timer,
        'reminder': {'enabled': reminder_enabled},
    }
    return jsonify({'code': 200, 'data': data})


def _setup_done() -> bool:
    from models.user import User
    return User.query.first() is not None


def _reminder_enabled(user_id: int) -> bool:
    try:
        from services.reminder_service import get_setting
        return bool(get_setting(user_id).enabled)
    except Exception:
        return True


def _session_dict(session: TimerSession) -> dict:
    """计时会话序列化（含关联任务），与 /plans/timer/current 口径一致。"""
    d = session.to_dict()
    if session.task_id:
        from models.task import StudyTask
        task = StudyTask.query.get(session.task_id)
        d['task'] = task.to_dict() if task else None
    else:
        d['task'] = None
    return d
