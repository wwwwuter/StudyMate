from flask import Blueprint, request, jsonify
from models.analysis import AIAnalysis
from models.task import StudyTask
from models.record import StudyRecord
from app.extensions import db
from utils.jwt_utils import login_required
from ai.service import AIService

ai_bp = Blueprint('ai', __name__)
ai_service = AIService()


@ai_bp.route('/daily-summary', methods=['POST'])
@login_required
def daily_summary(current_user):
    """每日学习总结"""
    data = request.get_json()
    date_str = data.get('date')

    from datetime import datetime, date
    if date_str:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        query_date = date.today()

    # 获取当天任务
    tasks = StudyTask.query.filter_by(user_id=current_user.id, date=query_date).all()
    # 获取当天记录
    records = StudyRecord.query.filter(
        StudyRecord.user_id == current_user.id,
        StudyRecord.start_time >= datetime.combine(query_date, datetime.min.time()),
        StudyRecord.start_time < datetime.combine(query_date, datetime.max.time()),
    ).all()

    total_seconds = sum(r.duration for r in records if r.duration)
    task_summary = "\n".join([
        f"- [{t.status}] {t.subject}: {t.content} ({t.start_time}-{t.end_time})"
        for t in tasks
    ])

    input_text = f"日期：{query_date}\n学习任务：\n{task_summary}\n学习时长：{round(total_seconds/3600, 1)}小时"

    try:
        output = ai_service.daily_summary(input_text)
    except Exception as e:
        return jsonify({'code': 500, 'message': f'AI 服务调用失败: {str(e)}'}), 500

    analysis = AIAnalysis(
        user_id=current_user.id,
        analysis_type='daily_summary',
        input_data=input_text,
        output_data=output,
    )
    db.session.add(analysis)
    db.session.commit()

    return jsonify({'code': 200, 'data': analysis.to_dict()})


@ai_bp.route('/plan-optimize', methods=['POST'])
@login_required
def plan_optimize(current_user):
    """学习计划优化"""
    from datetime import date, timedelta, datetime

    today = date.today()
    week_ago = today - timedelta(days=7)

    tasks = StudyTask.query.filter(
        StudyTask.user_id == current_user.id,
        StudyTask.date >= week_ago,
        StudyTask.date <= today,
    ).all()

    records = StudyRecord.query.filter(
        StudyRecord.user_id == current_user.id,
        StudyRecord.start_time >= datetime.combine(week_ago, datetime.min.time()),
    ).all()

    # 统计各科数据
    subject_stats = {}
    for t in tasks:
        if t.subject not in subject_stats:
            subject_stats[t.subject] = {'total': 0, 'done': 0, 'seconds': 0}
        subject_stats[t.subject]['total'] += 1
        if t.status == 'done':
            subject_stats[t.subject]['done'] += 1

    for r in records:
        if r.task_id:
            task = StudyTask.query.get(r.task_id)
            if task and task.subject in subject_stats:
                subject_stats[task.subject]['seconds'] += r.duration or 0

    stats_text = ""
    for subj, s in subject_stats.items():
        rate = round(s['done'] / s['total'] * 100, 1) if s['total'] > 0 else 0
        hours = round(s['seconds'] / 3600, 1)
        stats_text += f"{subj}: 完成率{rate}%, 学习时长{hours}小时\n"

    input_text = f"近7天学习统计：\n{stats_text}"

    try:
        output = ai_service.plan_optimize(input_text)
    except Exception as e:
        return jsonify({'code': 500, 'message': f'AI 服务调用失败: {str(e)}'}), 500

    analysis = AIAnalysis(
        user_id=current_user.id,
        analysis_type='plan_optimization',
        input_data=input_text,
        output_data=output,
    )
    db.session.add(analysis)
    db.session.commit()

    return jsonify({'code': 200, 'data': analysis.to_dict()})


@ai_bp.route('/chat', methods=['POST'])
@login_required
def chat(current_user):
    """AI 学习助手对话"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'code': 400, 'message': '缺少消息内容'}), 400

    try:
        output = ai_service.chat(data['message'])
    except Exception as e:
        return jsonify({'code': 500, 'message': f'AI 服务调用失败: {str(e)}'}), 500

    analysis = AIAnalysis(
        user_id=current_user.id,
        analysis_type='qa',
        input_data=data['message'],
        output_data=output,
    )
    db.session.add(analysis)
    db.session.commit()

    return jsonify({'code': 200, 'data': {'answer': output}})