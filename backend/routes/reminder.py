"""提醒相关路由：待送达列表、回执、用户偏好设置、手动触发扫描。"""
from flask import request, jsonify

from utils.jwt_utils import login_required
from app.extensions import db
from models.reminder import Reminder, ReminderSetting
from services.reminder_service import get_setting, sweep_due_reminders


@login_required
def pending(current_user):
    """当前用户尚未送达的提醒，按开始时间升序。"""
    rows = (
        Reminder.query
        .filter_by(user_id=current_user.id, delivered=False)
        .order_by(Reminder.fire_at.asc())
        .all()
    )
    return jsonify({'code': 200, 'data': [r.to_dict() for r in rows]})


@login_required
def ack(current_user):
    """标记提醒已送达（前端弹过通知后回执）。body: { ids: [int, ...] }"""
    ids = (request.get_json(silent=True) or {}).get('ids') or []
    if not isinstance(ids, list):
        return jsonify({'code': 400, 'message': 'ids 必须是数组'}), 400
    from utils.time_utils import utcnow
    updated = (
        Reminder.query
        .filter(Reminder.user_id == current_user.id, Reminder.id.in_(ids), Reminder.delivered == False)  # noqa: E712
        .update({Reminder.delivered: True, Reminder.delivered_at: utcnow()}, synchronize_session=False)
    )
    db.session.commit()
    return jsonify({'code': 200, 'message': f'已确认 {updated} 条', 'data': {'count': updated}})


@login_required
def get_settings(current_user):
    s = get_setting(current_user.id)
    return jsonify({
        'code': 200,
        'data': {'enabled': s.enabled, 'lead_minutes': s.lead_minutes},
    })


@login_required
def save_settings(current_user):
    data = request.get_json(silent=True) or {}
    s = db.session.get(ReminderSetting, current_user.id)
    if s is None:
        s = ReminderSetting(user_id=current_user.id)
        db.session.add(s)
    if 'enabled' in data:
        s.enabled = bool(data['enabled'])
    if 'lead_minutes' in data:
        try:
            lm = int(data['lead_minutes'])
        except (TypeError, ValueError):
            return jsonify({'code': 400, 'message': 'lead_minutes 必须是整数'}), 400
        if lm < 0 or lm > 600:
            return jsonify({'code': 400, 'message': 'lead_minutes 需在 0~600 之间'}), 400
        s.lead_minutes = lm
    db.session.commit()
    return jsonify({'code': 200, 'message': '设置已保存', 'data': {'enabled': s.enabled, 'lead_minutes': s.lead_minutes}})


@login_required
def sweep(current_user):
    """手动触发一次扫描（便于联调，无需等待调度周期）。"""
    created = sweep_due_reminders()
    return jsonify({'code': 200, 'data': {'created': created}})
